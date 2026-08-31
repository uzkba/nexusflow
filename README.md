# Painel Executivo — Portfólio de Geração

Plataforma para extração (ETL), tratamento e visualização de dados de outorgas de geração de energia elétrica no Brasil (solar e eólica), com base em dados públicos da ANEEL.

A arquitetura desacopla ingestão de dados, curadoria de dados (com aprovação humana) e interface de visualização, priorizando confiabilidade do dado apresentado ao cliente sobre velocidade de entrega.

A consolidação de clientes duplicados na base (mesma empresa aparecendo com nomes ligeiramente diferentes) não é automática: o sistema sugere agrupamentos e o **admin** (o próprio cliente final, único tipo de conta do sistema — ver seção `usuarios`) aprova ou rejeita cada sugestão antes que ela vire dado oficial no dashboard.

## Equipe

3 desenvolvedores, com fases pensadas para permitir trabalho em paralelo a partir da Fase 2.

- **Dev A** — Dados e ETL
- **Dev B** — Backend e API
- **Dev C** — Frontend

## Stack tecnológica

| Camada | Tecnologia | Papel |
|---|---|---|
| Frontend | React (Vite) + Tailwind CSS + Shadcn/UI + Apache ECharts | Interface, gráficos e mapa geográfico |
| Backend / API | Python + FastAPI (assíncrono) | Endpoints analíticos e autenticação |
| Motor ETL | Pandas + APScheduler | Extração, normalização e agendamento |
| Matching de nomes | RapidFuzz | Score de similaridade para sugestão de consolidação |
| Banco de dados | PostgreSQL + SQLAlchemy + Alembic | Persistência e migrations versionadas |
| Hospedagem | Railway | API, worker do scheduler, banco e ambientes de staging/produção |

## Fonte de dados

Fonte oficial: **SIGA — Sistema de Informações de Geração da ANEEL** (dataset `siga-empreendimentos-geracao-diario.csv`, Portal de Dados Abertos, atualização diária). O dataset da ANEEL cobre **todas as fontes de geração com concessão/autorização** (Solar, Eólica, Térmica, Hídrica, Biomassa etc.) e as fases "Construção não iniciada", "Construção" e "Operação" — mas apenas um subconjunto é persistido em `projetos_geracao`, por decisão de negócio confirmada com o cliente:

- **Fase:** só "Construção não iniciada" segue adiante.
- **Origem:** só Solar e Eólica seguem adiante.

Os dois filtros são aplicados explicitamente no Transform (ver Fase 2 do pipeline) — o CSV bruto continua sendo baixado e preservado por completo, o filtro só decide o que é persistido em `projetos_geracao`.

> O dataset "Atos de Outorgas de Geração" foi descartado como fonte principal: registra documentos administrativos emitidos, não o status contínuo de obra do empreendimento.

Colunas do CSV e mapeamento de valores de fase documentados em `Mapeamento_SIGA_Fase_e_Colunas.docx`.

## Pipeline de dados (ETL com aprovação humana)

Princípio central: dado bruto nunca é sobrescrito, e nenhum dado vira "oficial" sem passar por uma decisão registrada.

1. **Extract** — download diário do CSV do SIGA via endpoint público da ANEEL, carregado em memória via Pandas. O CSV bruto de cada rodada é preservado.
2. **Transform** — limpeza de texto (remoção de CNPJ, sufixos societários, numerações finais), filtro de fase (só "Construção não iniciada" segue adiante) e filtro de origem (só Solar/Eólica segue adiante), e cálculo de score de similaridade (RapidFuzz) entre nomes de agentes já vistos, gerando sugestões de agrupamento — não aplica a fusão diretamente.
3. **Staging** — sugestões de consolidação gravadas em `consolidacoes_pendentes`; os CEGs relacionados ficam em tabela associativa própria (`consolidacao_ceg`), não em array solto, para manter integridade referencial com `projetos_geracao`.
4. **Aprovação** — tela dedicada do painel onde o admin (cliente final) vê cada sugestão, o score e os projetos envolvidos, e aprova ou rejeita. Decisão registrada com autor e data/hora.
5. **Load** — projetos são gravados/atualizados via upsert (`ON CONFLICT DO UPDATE`) usando o CEG como chave, sem sobrescrever `criado_em`. Todo `GenerationProject` novo entra com `cliente_id = NULL` até que uma sugestão de consolidação envolvendo o `nome_bruto` dele seja aprovada. **A aprovação de uma `PendingConsolidation` precisa propagar `cliente_id` para todo `GenerationProject` ligado a ela via `consolidacao_ceg` — isso é lógica explícita do endpoint `/api/consolidacoes/{id}/aprovar`, não acontece sozinho no banco.** Sem esse passo, aprovar uma sugestão não muda nada nos gráficos.
6. **Observabilidade** — cada execução do ETL grava início, fim, status e contagem de linhas processadas/erros em tabela própria.

## Modelagem de dados

O esquema separa entidades canônicas de dado bruto e de sugestões pendentes, para que aprovação/rejeição de uma consolidação nunca exija reprocessar ou apagar histórico.

> **Nota de implementação:** os enums do SQLAlchemy vivem em `backend/app/enums/`, um arquivo por domínio. As classes do model (`User`, `Client`, `RawName`, `PendingConsolidation`, `ConsolidationCeg`, `GenerationProject`, `EtlRun`) são nomeadas em inglês; nomes de tabela, coluna e os valores de enum permanecem em português.

### `usuarios`
Autenticação do painel. **Único tipo de conta: `admin`** — é o próprio cliente final quem loga e executa as ações de aprovação/rejeição, não existe uma segunda role de "cliente" separada do admin.

| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| email | text (unique) | |
| senha_hash | text | bcrypt |
| papel | enum | valor único: `admin` |
| ativo | boolean | default true |
| criado_em | timestamp | |
| atualizado_em | timestamp | |

### `refresh_tokens`
Suporte a rotação de token JWT (access + refresh).

| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| usuario_id | FK → usuarios.id | ON DELETE CASCADE |
| token_hash | text (unique) | |
| criado_em | timestamp | |
| expira_em | timestamp | |
| revogado_em | timestamp | Nulo se ainda válido |
| substituido_por_id | FK → refresh_tokens.id | ON DELETE SET NULL — aponta pro token que substituiu este na rotação |

### `clientes`
Entidade canônica — quem a ANEEL/empresa realmente é, após consolidação aprovada.

| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | Identificador interno |
| nome_oficial | text | Nome final exibido no dashboard |
| criado_em | timestamp | |
| atualizado_em | timestamp | |

### `nomes_brutos`
Toda variação de nome de agente já vista no CSV da ANEEL. **Único por `nome_bruto`** — a mesma variação vista de novo em uma rodada posterior do ETL atualiza a linha (upsert), não cria duplicata.

| Coluna | Tipo | Notas |
|---|---|---|
| id | serial (PK) | |
| nome_bruto | text (unique) | Como aparece originalmente no CSV |
| cliente_id | FK → clientes.id | Nulo até aprovação de vínculo |
| primeira_ocorrencia | timestamp | Quando apareceu pela 1ª vez no ETL |
| ultima_ocorrencia | timestamp | Atualizado a cada rodada em que o nome reaparece |
| total_ocorrencias | int | Contador — sinal de confiança extra para o matching |

### `consolidacoes_pendentes`
Staging das sugestões de agrupamento aguardando decisão.

| Coluna | Tipo | Notas |
|---|---|---|
| id | serial (PK) | |
| nome_bruto_id | FK → nomes_brutos.id | |
| cliente_sugerido_id | FK → clientes.id | Cliente candidato à fusão |
| score_similaridade | float (0–100) | Calculado via RapidFuzz |
| status | enum | pendente / aprovado / rejeitado |
| decidido_por | FK → usuarios.id | Nulo até haver decisão |
| decidido_em | timestamp | Nulo até haver decisão |

Os CEGs relacionados a cada sugestão **não** ficam mais num array/JSONB dentro desta tabela — ver `consolidacao_ceg` abaixo.

### `consolidacao_ceg`
Tabela associativa: quais CEGs cada sugestão de consolidação envolve. Existe para garantir integridade referencial real com `projetos_geracao` (o formato anterior, array solto, não garantia que os CEGs citados existissem de fato).

| Coluna | Tipo | Notas |
|---|---|---|
| consolidacao_id | FK → consolidacoes_pendentes.id (PK composta) | ON DELETE CASCADE |
| ceg | FK → projetos_geracao.ceg (PK composta) | ON DELETE CASCADE |

### `projetos_geracao`
Tabela principal consumida pelo dashboard.

| Coluna | Tipo | Notas |
|---|---|---|
| ceg | text (PK) | Código Único de Empreendimentos de Geração — chave oficial ANEEL |
| nome_projeto | text | |
| cliente_id | FK → clientes.id | Substitui o antigo campo de texto livre |
| uf | char(2) | Indexado |
| municipios | array / jsonb | Um parque pode abranger mais de um município — todos listados aqui, todos plotados no mapa |
| origem | string (validado em Python/Pydantic, não enum de banco) | Solar / Eólica — indexado. Categoria vem da ANEEL; validação fora do tipo da coluna evita migration a cada novo valor |
| fase | string (validado em Python/Pydantic, não enum de banco) | Só "Construção não iniciada" chega até aqui (filtro no Transform) — indexado |
| potencia_outorgada_kw | float | |
| inicio_vigencia_ano | int | Indexado |
| latitude / longitude | float | Usado na aba Geolocalização |
| status_revisao | enum | pendente / aprovado / rejeitado — registro novo do ETL entra "pendente" até revisão manual de nome_projeto/cliente_id |
| criado_em | timestamp | Quando a linha entrou na base pela primeira vez (não muda em updates) — base do histórico de "quem está esperando aprovação há mais tempo" |
| atualizado_em | timestamp | Última rodada de ETL que tocou este registro |

### `etl_runs`
Log de execução do pipeline, para diagnóstico.

| Coluna | Tipo | Notas |
|---|---|---|
| id | serial (PK) | |
| iniciado_em | timestamp | |
| finalizado_em | timestamp | Nulo se ainda em execução ou se falhou sem finalizar |
| status | enum | sucesso / erro / em_andamento |
| linhas_processadas | int | |
| erros | jsonb | Detalhes de falhas, se houver |

**Índices obrigatórios:** `cliente_id`, `uf`, `origem`, `fase`, `inicio_vigencia_ano` e `criado_em` em `projetos_geracao` — garantem resposta rápida aos filtros do painel sem múltiplos JOINs pesados.

## Contrato da API

| Rota | Método | Descrição |
|---|---|---|
| `/api/auth/login` | POST | Autenticação, retorna access + refresh token |
| `/api/kpis` | GET | Totais agregados (projetos, clientes, potência) por filtro |
| `/api/graficos/potencia-uf` | GET | Potência outorgada agrupada por UF |
| `/api/graficos/evolucao-anual` | GET | Série anual de potência outorgada |
| `/api/projetos` | GET | Listagem paginada da Base de Dados, com filtros via query string |
| `/api/geolocalizacao` | GET | Pontos georreferenciados + ranking de municípios |
| `/api/consolidacoes/pendentes` | GET | Lista sugestões de fusão aguardando decisão |
| `/api/consolidacoes/{id}/aprovar` | POST | Aprova uma sugestão de consolidação |
| `/api/consolidacoes/{id}/rejeitar` | POST | Rejeita e devolve para nova triagem |

Todas as rotas — exceto `/api/auth/login` — exigem token de autenticação válido. Todos os endpoints analíticos recebem parâmetros de filtro (origem, cliente, uf, município, ano) e devolvem agregação já processada no banco, nunca dado bruto para o frontend somar.

**Regra de consumo de `cliente_id = NULL`:** decisão confirmada — `GenerationProject` fica com `cliente_id = NULL` até que uma consolidação seja aprovada (ver Load, passo 5). Pra não poluir os números "oficiais" com obras ainda não identificadas:

- `/api/kpis`, `/api/graficos/potencia-uf`, `/api/graficos/evolucao-anual` filtram `WHERE cliente_id IS NOT NULL` por padrão.
- `/api/projetos` (Base de Dados) continua mostrando tudo, com filtro disponível por `cliente_id IS NULL` / `status_revisao` pra quem quiser ver o que ainda não foi consolidado.
- O `/api/consolidacoes/{id}/aprovar` precisa propagar `cliente_id` pros `GenerationProject` envolvidos (ver nota no pipeline, passo 5 do Load) — sem isso, aprovar não muda o que os gráficos mostram.

> **Ponto em aberto:** "Rejeita e devolve para nova triagem" — o model atual não tem um mecanismo estrutural claro pra isso. Uma sugestão rejeitada fica com `status = rejeitado` na mesma linha, `cliente_id` continua `NULL` nos projetos envolvidos (decisão confirmada: fica visível na Base de Dados, não é escondido nem forçado). Falta decidir só o caminho de correção: o endpoint `/rejeitar` cria uma nova linha em `consolidacoes_pendentes` (mesmo `nome_bruto_id`, outro `cliente_sugerido_id`)? Ou o `nome_bruto` só volta a ser candidato quando a próxima rodada do ETL rodar o matching de novo?

## Estrutura de telas

- **Login** — obrigatório para qualquer acesso ao painel.
- **Visão Geral** — KPIs, rosca de origem, evolução anual, ranking de clientes.
- **Geolocalização** — mapa do Brasil (ECharts + GeoJSON oficial do IBGE) e top municípios.
- **Base de Dados** — tabela paginada no servidor com os projetos.
- **Aprovação de Consolidação** — lista de sugestões de fusão de clientes, com score de similaridade e CEGs relacionados, para o admin (cliente final) aprovar ou rejeitar. Mesma qualidade visual (Shadcn/UI) das demais abas.

## Roteiro de desenvolvimento

Prazo flexível — priorizando estrutura robusta sobre velocidade.

### Fase 0 — Decisões e fundação
- ~~Confirmar colunas exatas do CSV do SIGA e mapeamento de valores de fase~~ — concluído, ver `Mapeamento_SIGA_Fase_e_Colunas.docx`
- ~~Fechar o schema definitivo com Alembic para migrations versionadas~~ — concluído: migration inicial gerada via `--autogenerate`, aplicada com `upgrade head` e `downgrade` testados
- Configurar ambientes staging e produção no Railway
- Modelar tabela de usuários e estratégia de autenticação (JWT + refresh token)

### Fase 1 — Fundação de dados
- Criar schema no PostgreSQL via migration
- Implementar Extract puro (download do CSV do SIGA, preservando o bruto)
- Popular `nomes_brutos` a partir da primeira carga

### Fase 2 — Transform e matching
- Implementar normalização de texto (regex: CNPJ, sufixos, numeração)
- Implementar filtro de fase e de origem (ver nota em "Fonte de dados")
- Implementar cálculo de score de similaridade (RapidFuzz) entre nomes
- Gravar sugestões em `consolidacoes_pendentes` + `consolidacao_ceg`

### Fase 3 — Autenticação e API base
- Implementar `/api/auth/login` com JWT + refresh token
- Middleware de autenticação em todas as rotas protegidas
- Implementar `/api/consolidacoes/pendentes`, `/aprovar`, `/rejeitar`
- Implementar upsert em `projetos_geracao` usando CEG como chave

### Fase 4 — Endpoints analíticos
- `/api/kpis`, `/api/graficos/potencia-uf`, `/api/graficos/evolucao-anual`
- `/api/projetos` com paginação de servidor e filtros via query string
- `/api/geolocalizacao` com agregação por município/UF

### Fase 5 — Frontend: telas principais
- Tela de login
- Shell com sidebar de filtros retrátil (Shadcn/UI)
- Aba Visão Geral (KPIs, rosca, gráficos) com React Query para cache
- Aba Base de Dados (tabela paginada)

### Fase 6 — Frontend: Geolocalização e Aprovação
- Registrar GeoJSON do IBGE como mapa customizado no ECharts
- Aba Geolocalização com pontos por projeto e ranking de municípios
- Aba de Aprovação de Consolidação com score, CEGs relacionados e ações aprovar/rejeitar
- Integração do estado global de filtros entre as abas

### Fase 7 — Testes, observabilidade e deploy
- Testes automatizados no algoritmo de matching/score (parte mais sensível a erro silencioso)
- Implementar `etl_runs` para log de cada execução
- Configurar backup automático do Postgres no Railway
- Deploy em produção e validação ponta a ponta com dado real

## Divisão de tarefas por desenvolvedor

Dev A carrega o caminho crítico (dados) — os outros dois entram assim que o schema estiver fechado, trabalhando com dado seed/mock enquanto o ETL real não está 100%.

### Dev A — Dados e ETL
- Levantar e documentar colunas do CSV do SIGA
- Modelar e versionar schema completo via Alembic
- Implementar Extract (download diário, preserva bruto)
- Implementar Transform: normalização por regex + filtros de fase/origem
- Implementar matching com RapidFuzz e geração de sugestões
- Implementar upsert com CEG como chave em `projetos_geracao`
- Implementar `etl_runs` (log de execução)
- Configurar job do APScheduler
- Escrever testes automatizados do algoritmo de matching

### Dev B — Backend e API
- Implementar autenticação (JWT + refresh token) e tabela `usuarios`
- Implementar middleware de proteção de rotas
- Implementar `/api/consolidacoes` (listar, aprovar, rejeitar)
- Implementar `/api/kpis`, `/api/graficos/potencia-uf`, `/api/graficos/evolucao-anual`
- Implementar `/api/projetos` com paginação e filtros
- Implementar `/api/geolocalizacao`
- Configurar ambientes staging/produção no Railway
- Configurar backup automático do Postgres

### Dev C — Frontend
- Tela de login
- Shell da aplicação + sidebar de filtros retrátil (Shadcn/UI)
- Configurar React Query para cache das chamadas à API
- Aba Visão Geral (KPIs, rosca de origem, gráficos)
- Aba Base de Dados (tabela paginada no servidor)
- Aba Geolocalização com ECharts + GeoJSON do IBGE
- Aba de Aprovação de Consolidação (score, CEGs relacionados, ações)
- Integração do estado de filtros entre as três abas analíticas

## Riscos e pontos de atenção

- Consolidação de nomes é o maior risco técnico — regex e matching de texto sobre dado público brasileiro é inerentemente sujo (acentuação, abreviações, erros de digitação da própria fonte).
- Confiança da equipe na tela de aprovação depende da qualidade do score e do contexto mostrado (CEGs relacionados) — sem isso, a aprovação vira clique automático sem valor real.
- Schema do SIGA não foi validado campo a campo — primeira tarefa técnica do projeto antes de fechar migrations.
- Fusões rejeitadas precisam de um caminho claro de nova triagem, para não acumular pendências sem solução — ver ponto em aberto na seção "Contrato da API".
- A propagação de `cliente_id` do `PendingConsolidation` aprovado para os `GenerationProject` associados é lógica de aplicação, não automática no banco — se o endpoint `/aprovar` não implementar isso explicitamente, a aprovação não reflete nos gráficos (ver "Contrato da API").