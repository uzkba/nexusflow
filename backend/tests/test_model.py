"""
Testes do model SQLAlchemy.

Escopo deliberadamente restrito: só o que o Postgres de fato enforce.
Não testa "a classe tem tal coluna" — isso é reflexão trivial que não
pega bug nenhum. Testa constraint, cascade/ondelete, enum de banco e
default que só se manifesta depois de um round-trip real.

Async de ponta a ponta (AsyncSession + asyncpg), pra bater com o driver
que a aplicação usa de verdade — não SQLAlchemy síncrono.

Lógica de aplicação (matching RapidFuzz, upsert do ETL, propagação de
cliente_id na aprovação de consolidação) NÃO é testada aqui — tem
arquivo próprio quando essa lógica existir.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend.app.enum import ReviewStatus, UserRole
from backend.app.model.models import (
    Client,
    ConsolidationCeg,
    GenerationProject,
    PendingConsolidation,
    RawName,
    RefreshToken,
    User,
)


# --------------------------------------------------------------------------
# Constraints únicas — protege a dedup que motivou essa suíte de testes
# --------------------------------------------------------------------------
class TestUniqueConstraints:
    async def test_raw_name_nome_bruto_is_unique(self, db_session):
        db_session.add(RawName(nome_bruto="EMPRESA X LTDA"))
        await db_session.flush()

        db_session.add(RawName(nome_bruto="EMPRESA X LTDA"))
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_user_email_is_unique(self, db_session):
        db_session.add(User(email="admin@exemplo.com", senha_hash="hash1"))
        await db_session.flush()

        db_session.add(User(email="admin@exemplo.com", senha_hash="hash2"))
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_generation_project_ceg_is_primary_key(self, db_session):
        db_session.add(GenerationProject(ceg="CEG-0001"))
        await db_session.flush()

        db_session.add(GenerationProject(ceg="CEG-0001"))
        with pytest.raises(IntegrityError):
            await db_session.flush()


# --------------------------------------------------------------------------
# ondelete — cada um foi uma decisão deliberada, não default acidental
# --------------------------------------------------------------------------
class TestOnDeleteBehavior:
    async def test_deleting_user_cascades_refresh_tokens(self, db_session):
        user = User(email="a@exemplo.com", senha_hash="hash")
        db_session.add(user)
        await db_session.flush()

        token = RefreshToken(
            usuario_id=user.id,
            token_hash="abc123",
            expira_em=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(token)
        await db_session.flush()
        token_id = token.id

        await db_session.delete(user)
        await db_session.flush()

        # session.get() checaria o identity map primeiro e devolveria o
        # token "vivo" em memória — quem apagou a linha foi o CASCADE do
        # banco, não uma chamada explícita de session.delete(token), então
        # o ORM não sabe que ela sumiu. SQL cru confirma direto no banco.
        result = await db_session.execute(
            text("SELECT 1 FROM refresh_tokens WHERE id = :id"), {"id": token_id}
        )
        assert result.first() is None

    async def test_deleting_newer_refresh_token_sets_null_not_cascade(self, db_session):
        """
        substituido_por_id usa SET NULL: apagar o token novo (B) não pode
        arrastar o token antigo (A) junto — A é histórico de auditoria.
        """
        user = User(email="b@exemplo.com", senha_hash="hash")
        db_session.add(user)
        await db_session.flush()

        expira = datetime.now(timezone.utc) + timedelta(days=7)
        token_b = RefreshToken(usuario_id=user.id, token_hash="token-b", expira_em=expira)
        db_session.add(token_b)
        await db_session.flush()

        token_a = RefreshToken(
            usuario_id=user.id,
            token_hash="token-a",
            expira_em=expira,
            substituido_por_id=token_b.id,
        )
        db_session.add(token_a)
        await db_session.flush()

        await db_session.delete(token_b)
        await db_session.flush()

        # session.get() olha primeiro o identity map — como token_a já
        # estava carregado nesta sessão, ele voltaria com o valor antigo
        # em memória sem isso. refresh() força reconsultar o banco de
        # verdade, que é o que o SET NULL efetivamente mudou.
        await db_session.refresh(token_a)
        assert token_a.substituido_por_id is None

    async def test_deleting_pending_consolidation_cascades_consolidation_ceg(self, db_session):
        client = Client(nome_oficial="Empresa Y")
        raw_name = RawName(nome_bruto="EMPRESA Y S.A.")
        project = GenerationProject(ceg="CEG-0002")
        db_session.add_all([client, raw_name, project])
        await db_session.flush()

        consolidation = PendingConsolidation(
            nome_bruto_id=raw_name.id,
            cliente_sugerido_id=client.id,
            score_similaridade=92.5,
        )
        db_session.add(consolidation)
        await db_session.flush()

        link = ConsolidationCeg(consolidacao_id=consolidation.id, ceg=project.ceg)
        db_session.add(link)
        await db_session.flush()

        await db_session.delete(consolidation)
        await db_session.flush()

        remaining = await db_session.get(
            ConsolidationCeg, {"consolidacao_id": consolidation.id, "ceg": project.ceg}
        )
        assert remaining is None


# --------------------------------------------------------------------------
# Enum nativo do Postgres — confirma que só os enums que a gente decidiu
# manter como Enum de banco (não string) de fato rejeitam valor inválido
# --------------------------------------------------------------------------
class TestDatabaseEnumEnforcement:
    async def test_papel_usuario_rejects_value_outside_enum(self, db_session):
        # DBAPIError, não DataError: o dialect asyncpg embrulha o erro
        # de enum inválido (InvalidTextRepresentationError, SQLSTATE
        # 22P02) na classe genérica DBAPIError, não na subclasse mais
        # específica DataError que o dialect psycopg2 usaria. Confirmado
        # rodando contra Postgres real — DataError não capturava.
        with pytest.raises(DBAPIError):
            await db_session.execute(
                text(
                    "INSERT INTO usuarios (id, email, senha_hash, papel) "
                    "VALUES (:id, :email, :senha_hash, 'superadmin')"
                ),
                {"id": uuid.uuid4(), "email": "x@exemplo.com", "senha_hash": "hash"},
            )
            await db_session.flush()

    async def test_status_revisao_rejects_value_outside_enum(self, db_session):
        db_session.add(GenerationProject(ceg="CEG-0003"))
        await db_session.flush()

        with pytest.raises(DBAPIError):
            await db_session.execute(
                text("UPDATE projetos_geracao SET status_revisao = 'em_analise' WHERE ceg = :ceg"),
                {"ceg": "CEG-0003"},
            )
            await db_session.flush()

    async def test_origem_and_fase_accept_any_string(self, db_session):
        """
        Contraste deliberado com os testes acima: origem/fase NÃO são
        Enum de banco (decisão registrada no README) — validação é
        responsabilidade do Transform/Pydantic, não da coluna. Isso
        confirma que a coluna aceita qualquer string sem erro do banco.
        """
        project = GenerationProject(ceg="CEG-0004", origem="Térmica", fase="Operação")
        db_session.add(project)
        await db_session.flush()  # não deve levantar erro


# --------------------------------------------------------------------------
# Defaults que só se confirmam depois de um round-trip no banco
# --------------------------------------------------------------------------
class TestDefaults:
    async def test_user_ativo_defaults_true(self, db_session):
        user = User(email="c@exemplo.com", senha_hash="hash")
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        assert user.ativo is True
        assert user.papel == UserRole.admin

    async def test_raw_name_total_ocorrencias_defaults_one(self, db_session):
        raw_name = RawName(nome_bruto="EMPRESA Z")
        db_session.add(raw_name)
        await db_session.flush()
        await db_session.refresh(raw_name)

        assert raw_name.total_ocorrencias == 1
        assert raw_name.primeira_ocorrencia is not None
        assert raw_name.ultima_ocorrencia is not None

    async def test_generation_project_status_revisao_defaults_pendente(self, db_session):
        project = GenerationProject(ceg="CEG-0005")
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        assert project.status_revisao == ReviewStatus.pendente
        assert project.criado_em is not None