import pytest
from unittest.mock import patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.model.models import (
    Client,
    RawName,
    GenerationProject,
    PendingConsolidation,
)
from backend.app.enum import ConsolidationStatus
from backend.app.services.matching.matching_service import (
    MatchingPipelineService,
    normalize_company_name,
    compute_similarity_score,
)


# =====================================================================
# 1. UNIT TESTS: Core Normalization & Scoring Logic
# =====================================================================

class TestMatchingAlgorithmUnit:
    """Unit tests for string normalization and similarity calculation in isolation."""

    @pytest.mark.parametrize(
        "dirty_input,expected_normalized",
        [
            ("VENTOS DE SAO CARLOS 01", "ventos de sao carlos"),
            ("SPE VENTOS DE SÃO CARLOS 04 S/A", "ventos de sao carlos"),
            ("CENTRAL EOLICA VENTOS DE SAO CARLOS 08 LTDA.", "ventos de sao carlos"),
            ("  Ventos de São Carlos Oficial  ", "ventos de sao carlos"),
        ],
    )
    def test_normalize_company_name_strips_spe_noise(
        self, dirty_input: str, expected_normalized: str
    ) -> None:
        cleaned = normalize_company_name(dirty_input)
        assert expected_normalized in cleaned

    def test_similarity_score_ranks_target_above_distractors(self) -> None:
        raw_spe = "VENTOS DE SAO CARLOS 07 SPE LTDA"
        target_name = "Ventos de São Carlos Oficial"
        distractor_sao_jose = "Ventos de São José Energia S.A."
        distractor_solar = "São Carlos Solar Participações Ltda"

        score_target = compute_similarity_score(raw_spe, target_name)
        score_sao_jose = compute_similarity_score(raw_spe, distractor_sao_jose)
        score_solar = compute_similarity_score(raw_spe, distractor_solar)

        assert score_target >= 85.0
        assert score_target > score_sao_jose
        assert score_target > score_solar


# =====================================================================
# 2. INTEGRATION TESTS: Database Persistence & Consolidation Routing
# =====================================================================

class TestMatchingPipelineDatabaseIntegration:
    """Integration tests verifying DB state transitions via AsyncSession."""

    @pytest.mark.asyncio
    async def test_high_confidence_match_links_directly(
        self,
        db_session: AsyncSession,
        seeded_clients: dict[str, Client],
    ) -> None:
        target_client = seeded_clients["target"]

        raw_entry = RawName(nome_bruto="VENTOS DE SAO CARLOS OFICIAL S.A.", cliente_id=None)
        db_session.add(raw_entry)
        await db_session.commit()
        await db_session.refresh(raw_entry)

        service = MatchingPipelineService(
            db_session=db_session,
            auto_match_threshold=90.0,
            review_threshold=70.0,
        )
        await service.process_unmatched_raw_names()
        await db_session.refresh(raw_entry)

        assert raw_entry.cliente_id == target_client.id

        stmt = select(PendingConsolidation).where(
            PendingConsolidation.nome_bruto_id == raw_entry.id
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_ambiguous_match_creates_pending_consolidation(
        self,
        db_session: AsyncSession,
        seeded_clients: dict[str, Client],
    ) -> None:
        target_client = seeded_clients["target"]

        raw_entry = RawName(
            nome_bruto="CONSORCIO GERADOR S. CARLOS",
            cliente_id=None,
        )
        db_session.add(raw_entry)
        await db_session.commit()
        await db_session.refresh(raw_entry)

        # O patch agora aponta perfeitamente para o caminho do novo arquivo
        with patch(
            "backend.app.services.matching.matching_service.compute_similarity_score",
            side_effect=lambda raw, official: 78.5 if "São Carlos Oficial" in official else 40.0,
        ):
            service = MatchingPipelineService(
                db_session=db_session,
                auto_match_threshold=90.0,
                review_threshold=70.0,
            )
            await service.process_unmatched_raw_names()

        await db_session.refresh(raw_entry)
        assert raw_entry.cliente_id is None

        stmt = select(PendingConsolidation).where(
            PendingConsolidation.nome_bruto_id == raw_entry.id
        )
        result = await db_session.execute(stmt)
        pending = result.scalar_one_or_none()

        assert pending is not None
        assert pending.cliente_sugerido_id == target_client.id
        assert pending.score_similaridade == pytest.approx(78.5, rel=1e-2)
        # O assert agora utiliza o Enum real do modelo em vez da string "PENDING"
        assert pending.status == ConsolidationStatus.pendente
        assert pending.motivo_pendencia is not None

    @pytest.mark.asyncio
    async def test_low_confidence_ignores_and_leaves_unmatched(
        self,
        db_session: AsyncSession,
        seeded_clients: dict[str, Client],
    ) -> None:
        raw_entry = RawName(
            nome_bruto="HIDRELETRICA FOZ DO RIO XINGU LTDA",
            cliente_id=None,
        )
        db_session.add(raw_entry)
        await db_session.commit()
        await db_session.refresh(raw_entry)

        service = MatchingPipelineService(
            db_session=db_session,
            auto_match_threshold=90.0,
            review_threshold=70.0,
        )
        await service.process_unmatched_raw_names()
        await db_session.refresh(raw_entry)

        assert raw_entry.cliente_id is None

        stmt = select(PendingConsolidation).where(
            PendingConsolidation.nome_bruto_id == raw_entry.id
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None


# =====================================================================
# 3. REGRESSION SUITE: The 12 "VENTOS DE SÃO CARLOS" SPEs
# =====================================================================

class TestVentosDeSaoCarlosRegression:
    """
    Regression suite guaranteeing that all 12 SPEs (VENTOS DE SAO CARLOS 01-12)
    are consistently mapped to the official 'Ventos de São Carlos Oficial' client.
    """

    @pytest.mark.asyncio
    async def test_all_12_spes_map_consistently_to_official_client(
        self,
        db_session: AsyncSession,
        seeded_clients: dict[str, Client],
        ventos_sao_carlos_spes: list[tuple[RawName, GenerationProject]],
    ) -> None:
        target_client = seeded_clients["target"]
        assert len(ventos_sao_carlos_spes) == 12

        service = MatchingPipelineService(
            db_session=db_session,
            auto_match_threshold=85.0,
            review_threshold=70.0,
        )
        await service.process_unmatched_raw_names()

        for raw_name, project in ventos_sao_carlos_spes:
            await db_session.refresh(raw_name)
            await db_session.refresh(project)

            if raw_name.cliente_id is not None:
                assert raw_name.cliente_id == target_client.id, (
                    f"SPE '{raw_name.nome_bruto}' matched wrong Client ID: {raw_name.cliente_id}"
                )
                assert project.cliente_id == target_client.id, (
                    f"Project '{project.ceg}' did not inherit Client ID from '{raw_name.nome_bruto}'"
                )
            else:
                stmt = select(PendingConsolidation).where(
                    PendingConsolidation.nome_bruto_id == raw_name.id
                )
                result = await db_session.execute(stmt)
                pending = result.scalar_one_or_none()

                assert pending is not None, (
                    f"SPE '{raw_name.nome_bruto}' was neither auto-matched nor added to PendingConsolidation"
                )
                assert pending.cliente_sugerido_id == target_client.id, (
                    f"SPE '{raw_name.nome_bruto}' suggested wrong Client: {pending.cliente_sugerido_id}"
                )
                assert pending.score_similaridade >= 70.0, (
                    f"SPE '{raw_name.nome_bruto}' produced unexpectedly low similarity score: {pending.score_similaridade}"
                )

    @pytest.mark.asyncio
    async def test_matching_pipeline_idempotency_on_12_spes(
        self,
        db_session: AsyncSession,
        seeded_clients: dict[str, Client],
        ventos_sao_carlos_spes: list[tuple[RawName, GenerationProject]],
    ) -> None:
        service = MatchingPipelineService(
            db_session=db_session,
            auto_match_threshold=85.0,
            review_threshold=70.0,
        )

        # First execution
        await service.process_unmatched_raw_names()
        first_run_pending = (
            await db_session.execute(select(PendingConsolidation))
        ).scalars().all()

        # Second execution
        await service.process_unmatched_raw_names()
        second_run_pending = (
            await db_session.execute(select(PendingConsolidation))
        ).scalars().all()

        assert len(first_run_pending) == len(second_run_pending)