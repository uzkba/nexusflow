import enum
import uuid
from datetime import datetime
 
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
 
 
class Base(DeclarativeBase):
    pass
 
# --------------------------------------------------------------------------
# 1. usuarios
# --------------------------------------------------------------------------
class PapelUsuario(str, enum.Enum):
    admin = "admin"  # único valor — confirmado, sem conta de cliente
 
 
class Usuario(Base):
    __tablename__ = "usuarios"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(Text, nullable=False)
    papel: Mapped[PapelUsuario] = mapped_column(
        Enum(PapelUsuario, name="papel_usuario"), nullable=False, default=PapelUsuario.admin
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # ASSUMIDO — ver docstring
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
 
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="usuario")
 
 
# --------------------------------------------------------------------------
# 2. refresh_tokens — mantida por decisão confirmada (não estava na imagem)
# --------------------------------------------------------------------------
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    substituido_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id"), nullable=True
    )
 
    usuario: Mapped["Usuario"] = relationship(back_populates="refresh_tokens")
 
 
# --------------------------------------------------------------------------
# 3. clientes — entidade canônica (imagem, seção 5.1)
# --------------------------------------------------------------------------
class Cliente(Base):
    __tablename__ = "clientes"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    nome_oficial: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
 
 
# --------------------------------------------------------------------------
# 4. nomes_brutos — toda variação de nome de agente já vista no CSV
# --------------------------------------------------------------------------
class NomeBruto(Base):
    __tablename__ = "nomes_brutos"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_bruto: Mapped[str] = mapped_column(Text, nullable=False)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True
    )
    primeira_ocorrencia: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
 
# --------------------------------------------------------------------------
# 5. consolidacoes_pendentes — staging das sugestões de agrupamento de cliente
# --------------------------------------------------------------------------
class StatusConsolidacao(str, enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
    rejeitado = "rejeitado"
 
 
class ConsolidacaoPendente(Base):
    __tablename__ = "consolidacoes_pendentes"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_bruto_id: Mapped[int] = mapped_column(ForeignKey("nomes_brutos.id"), nullable=False)
    cliente_sugerido_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False
    )
    score_similaridade: Mapped[float] = mapped_column(Float)  # 0-100, via RapidFuzz
    cegs_relacionados: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[StatusConsolidacao] = mapped_column(
        Enum(StatusConsolidacao, name="status_consolidacao"), nullable=False, default=StatusConsolidacao.pendente
    )
    decidido_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    decidido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
 
 
# --------------------------------------------------------------------------
# 6. projetos_geracao — tabela principal consumida pelo dashboard
# --------------------------------------------------------------------------
class OrigemGeracao(str, enum.Enum):
    solar = "Solar"
    eolica = "Eólica"
    # fechado por decisão de negócio confirmada — ver risco anotado acima
 
 
class FaseUsina(str, enum.Enum):
    construcao_nao_iniciada = "Construção não iniciada"
    # fechado por decisão de negócio confirmada — ver risco anotado acima
 
 
class StatusRevisao(str, enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
 
 
class ProjetoGeracao(Base):
    __tablename__ = "projetos_geracao"
 
    ceg: Mapped[str] = mapped_column(Text, primary_key=True)  # Código Único ANEEL — chave natural
    nome_projeto: Mapped[str | None] = mapped_column(Text, nullable=True)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True, index=True
    )
    uf: Mapped[str | None] = mapped_column(String(2), index=True)
 
    # ASSUMIDO: array em vez de texto único, por causa do fan-out decidido
    # na seção 7.3 (532 registros com múltiplos municípios). Se a intenção
    # real for reverter essa decisão, isso vira String(2) simples de novo.
    municipios: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
 
    origem: Mapped[OrigemGeracao | None] = mapped_column(
        Enum(OrigemGeracao, name="origem_geracao"), index=True
    )
    fase: Mapped[FaseUsina | None] = mapped_column(Enum(FaseUsina, name="fase_usina"), index=True)
    potencia_outorgada_kw: Mapped[float | None] = mapped_column(Float)
    inicio_vigencia_ano: Mapped[int | None] = mapped_column(Integer, index=True)
 
    # ASSUMIDO: mapeado no doc SIGA como "Geolocalização no mapa" — não
    # apareceu na imagem, mas sem isso não há o que plotar.
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
 
    # ASSUMIDO: decisão 7.4 — registro novo do ETL entra "pendente" até
    # revisão manual de nome_projeto/cliente_id.
    status_revisao: Mapped[StatusRevisao] = mapped_column(
        Enum(StatusRevisao, name="status_revisao"), nullable=False, default=StatusRevisao.pendente
    )
 
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
 
 
# --------------------------------------------------------------------------
# 7. etl_runs — log de execução do pipeline
# --------------------------------------------------------------------------
class StatusEtlRun(str, enum.Enum):
    sucesso = "sucesso"
    erro = "erro"
    em_andamento = "em_andamento"
 
 
class EtlRun(Base):
    __tablename__ = "etl_runs"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[StatusEtlRun] = mapped_column(
        Enum(StatusEtlRun, name="status_etl_run"), nullable=False, default=StatusEtlRun.em_andamento
    )
    linhas_processadas: Mapped[int | None] = mapped_column(Integer)
    erros: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)  # inclui falhas de enum inválido
 
