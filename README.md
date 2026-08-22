# Painel Executivo — Portfólio de Geração

Plataforma para extração (ETL), tratamento e visualização de dados de outorgas de geração de energia elétrica no Brasil (solar e eólica), com base em dados públicos da ANEEL.

A arquitetura desacopla ingestão de dados, curadoria de dados (com aprovação humana) e interface de visualização, priorizando confiabilidade do dado apresentado ao cliente sobre velocidade de entrega.

A consolidação de clientes duplicados na base (mesma empresa aparecendo com nomes ligeiramente diferentes) não é automática: o sistema sugere agrupamentos e o cliente final aprova ou rejeita cada sugestão antes que ela vire dado oficial no dashboard.

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

Fonte oficial: **SIGA — Sistema de Informações de Geração da ANEEL** (dataset `siga-empreendimentos-geracao-diario.csv`, Portal de Dados Abertos, atualização diária). Cobre empreendimentos nas fases "Construção não iniciada", "Construção" e "Operação".

> O dataset "Atos de Outorgas de Geração" foi descartado como fonte principal: registra documentos administrativos emitidos, não o status contínuo de obra do empreendimento.

**Ponto em aberto:** confirmar nome exato de todas as colunas do CSV do SIGA e o mapeamento de valores de fase, antes de fechar o schema definitivo.

## Pipeline de dados (ETL com aprovação humana)

Princípio central: dado bruto nunca é sobrescrito, e nenhum dado vira "oficial" sem passar por uma decisão registrada.

1. **Extract** — download diário do CSV do SIGA via endpoint público da ANEEL, carregado em memória via Pandas. O CSV bruto de cada rodada é preservado.
2. **Transform** — limpeza de texto (remoção de CNPJ, sufixos societários, numerações finais) e cálculo de score de similaridade (RapidFuzz) entre nomes de agentes já vistos, gerando sugestões de agrupamento — não aplica a fusão diretamente.
3. **Staging** — sugestões de consolidação gravadas em tabela de espera, com os CEGs relacionados anexados para dar contexto à decisão.
4. **Aprovação do cliente** — tela dedicada do painel onde o cliente vê cada sugestão, o score e os projetos envolvidos, e aprova ou rejeita. Decisão registrada com autor e data/hora.
5. **Load** — apenas sugestões aprovadas atualizam a tabela de clientes canônica. Projetos são gravados/atualizados via upsert (`ON CONFLICT DO UPDATE`) usando o CEG como chave.
6. **Observabilidade** — cada execução do ETL grava início, fim, status e contagem de linhas processadas/erros em tabela própria.

## Modelagem de dados

O esquema separa entidades canônicas de dado bruto e de sugestões pendentes, para que aprovação/rejeição de uma consolidação nunca exija reprocessar ou apagar histórico.

### `clientes`
Entidade canônica — quem a ANEEL/empresa realmente é, após consolidação aprovada.

| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID / serial (PK) | Identificador interno |
| nome_oficial | text | Nome final exibido no dashboard |
| criado_em | timestamp | |
| atualizado_em | timestamp | |

### `nomes_brutos`
Toda variação de nome de agente já vista no CSV da ANEEL.

| Coluna | Tipo | Notas |
|---|---|---|
| id | serial (PK) | |
| nome_bruto | text | Como aparece originalmente no CSV |
| cliente_id | FK → clientes.id | Nulo até aprovação de vínculo |
| primeira_ocorrencia | timestamp | Quando apareceu pela 1ª vez no ETL |

### `consolidacoes_pendentes`
Staging das sugestões de agrupamento aguardando decisão do cliente.

| Coluna | Tipo | Notas |
|---|---|---|
| id | serial (PK) | |
| nome_bruto_id | FK → nomes_brutos.id | |
| cliente_sugerido_id | FK → clientes.id | Cliente candidato à fusão |
| score_similaridade | float (0–100) | Calculado via RapidFuzz |
| cegs_relacionados | array / jsonb | Contexto para o cliente decidir |
| status | enum | pendente / aprovado / rejeitado |
| decidido_por | FK → usuarios.id | Nulo até haver decisão |
| decidido_em | timestamp | Nulo até haver decisão |

### `projetos_geracao`
Tabela principal consumida pelo dashboard.

| Coluna | Tipo | Notas |
|---|---|---|
| ceg | text (PK) | Código Único de Empreendimentos de Geração — chave oficial ANEEL |
| nome_projeto | text | |
| cliente_id | FK → clientes.id | Substitui o antigo campo de texto livre |
| uf | char(2) | Indexado |
| municipio | text | Indexado |
| origem | enum | Solar / Eólica — indexado |
| fase | enum | Mapeada a partir do SIGA — indexado |
| potencia_outorgada | float | MW |
| inicio_vigencia | int (ano) | Indexado |
| atualizado_em | timestamp | Última rodada de ETL que tocou este registro |

### `usuarios`
Autenticação do painel — inclui contas do cliente, que agora executa ações (aprovar/rejeitar), não só leitura.

| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| email | text (unique) | |
| senha_hash | text | bcrypt |
| papel | enum | admin / cliente (evoluir se necessário) |
| criado_em | timestamp | |

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

**Índices obrigatórios:** `cliente_id`, `uf`, `origem`, `fase` e `inicio_vigencia` em `projetos_geracao` — garantem resposta rápida aos filtros do painel sem múltiplos JOINs pesados.

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

## Estrutura de telas

- **Login** — obrigatório para qualquer acesso ao painel.
- **Visão Geral** — KPIs, rosca de origem, evolução anual, ranking de clientes.
- **Geolocalização** — mapa do Brasil (ECharts + GeoJSON oficial do IBGE) e top municípios.
- **Base de Dados** — tabela paginada no servidor com os projetos.
- **Aprovação de Consolidação** — lista de sugestões de fusão de clientes, com score de similaridade e CEGs relacionados, para o cliente aprovar ou rejeitar. Voltada ao cliente final, com a mesma qualidade visual (Shadcn/UI) das demais abas.

## Roteiro de desenvolvimento

Prazo flexível — priorizando estrutura robusta sobre velocidade.

### Fase 0 — Decisões e fundação
- Confirmar colunas exatas do CSV do SIGA e mapeamento de valores de fase
- Fechar o schema definitivo (6 tabelas) com Alembic para migrations versionadas
- Configurar ambientes staging e produção no Railway
- Modelar tabela de usuários e estratégia de autenticação (JWT + refresh token)

### Fase 1 — Fundação de dados
- Criar schema no PostgreSQL via migration
- Implementar Extract puro (download do CSV do SIGA, preservando o bruto)
- Popular `nomes_brutos` a partir da primeira carga

### Fase 2 — Transform e matching
- Implementar normalização de texto (regex: CNPJ, sufixos, numeração)
- Implementar cálculo de score de similaridade (RapidFuzz) entre nomes
- Gravar sugestões em `consolidacoes_pendentes` com CEGs relacionados

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
- Implementar Transform: normalização por regex
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
- Confiança do cliente na tela de aprovação depende da qualidade do score e do contexto mostrado (CEGs relacionados) — sem isso, a aprovação vira clique automático sem valor real.
- Schema do SIGA não foi validado campo a campo — primeira tarefa técnica do projeto antes de fechar migrations.
- Fusões rejeitadas precisam de um caminho claro de nova triagem, para não acumular pendências sem solução.
