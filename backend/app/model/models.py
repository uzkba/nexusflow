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

from backend.app.enum import (
    ConsolidationStatus,
    EtlRunStatus,
    ReviewStatus,
    UserRole,
)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(Text, nullable=False)
    papel: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="papel_usuario"), nullable=False, default=UserRole.admin
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="usuario", passive_deletes=True
    )


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
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )

    usuario: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Client(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    nome_oficial: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class RawName(Base):
    __tablename__ = "nomes_brutos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_bruto: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True
    )
    primeira_ocorrencia: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultima_ocorrencia: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    total_ocorrencias: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class PendingConsolidation(Base):
    __tablename__ = "consolidacoes_pendentes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_bruto_id: Mapped[int] = mapped_column(ForeignKey("nomes_brutos.id"), nullable=False)
    cliente_sugerido_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False
    )
    score_similaridade: Mapped[float] = mapped_column(Float)  # 0-100, via RapidFuzz
    status: Mapped[ConsolidationStatus] = mapped_column(
        Enum(ConsolidationStatus, name="status_consolidacao"),
        nullable=False,
        default=ConsolidationStatus.pendente,
    )
    decidido_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    decidido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cegs_relacionados: Mapped[list["ConsolidationCeg"]] = relationship(
        back_populates="consolidacao", cascade="all, delete-orphan"
    )

class ConsolidationCeg(Base):
    __tablename__ = "consolidacao_ceg"

    consolidacao_id: Mapped[int] = mapped_column(
        ForeignKey("consolidacoes_pendentes.id", ondelete="CASCADE"), primary_key=True
    )
    ceg: Mapped[str] = mapped_column(
        ForeignKey("projetos_geracao.ceg", ondelete="CASCADE"), primary_key=True
    )

    consolidacao: Mapped["PendingConsolidation"] = relationship(back_populates="cegs_relacionados")

class GenerationProject(Base):
    __tablename__ = "projetos_geracao"

    ceg: Mapped[str] = mapped_column(Text, primary_key=True)  # Código Único ANEEL — chave natural
    nome_projeto: Mapped[str | None] = mapped_column(Text, nullable=True)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True, index=True
    )
    uf: Mapped[str | None] = mapped_column(String(2), index=True)

    municipios: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    origem: Mapped[str | None] = mapped_column(String, index=True)
    fase: Mapped[str | None] = mapped_column(String, index=True)
    potencia_outorgada_kw: Mapped[float | None] = mapped_column(Float)
    inicio_vigencia_ano: Mapped[int | None] = mapped_column(Integer, index=True)

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    status_revisao: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="status_revisao"), nullable=False, default=ReviewStatus.pendente
    )

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
class EtlRun(Base):
    __tablename__ = "etl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[EtlRunStatus] = mapped_column(
        Enum(EtlRunStatus, name="status_etl_run"), nullable=False, default=EtlRunStatus.em_andamento
    )
    linhas_processadas: Mapped[int | None] = mapped_column(Integer)
    erros: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)  # inclui falhas de enum inválido