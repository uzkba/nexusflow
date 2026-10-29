import re
import unicodedata
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.model.models import (
    Client,
    GenerationProject,
    PendingConsolidation,
    RawName,
)
from backend.app.enum import ConsolidationStatus
from backend.app.enum.consolidacao import MotivoPendenciaEnum

# Regex para remover sufixos societários e numeração romana/arábica de SPEs
STOPWORDS_REGEX = re.compile(
    r"\b(spe|s\.?a\.?|s/a|ltda\.?|oficial|central|geradora|eolica|energia|empreendimentos)\b",
    flags=re.IGNORECASE,
)
SPE_NUMBER_REGEX = re.compile(
    r"\b(0?[1-9]|1[0-9]|2[0-9]|i{1,3}|iv|v|vi{0,3}|ix|x{1,3})\b", 
    flags=re.IGNORECASE
)


def normalize_company_name(name: str) -> str:
    """Removes accents, corporate suffixes, and SPE numbering to isolate the core brand."""
    # Remove acentos (NFD)
    text = unicodedata.normalize("NFD", name)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower()

    # Remove pontuação (mantendo espaços)
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove ruídos societários e sequenciais numéricos
    text = STOPWORDS_REGEX.sub(" ", text)
    text = SPE_NUMBER_REGEX.sub(" ", text)

    # Remove espaços duplos e trailing spaces
    return re.sub(r"\s+", " ", text).strip()


def compute_similarity_score(raw_name: str, official_name: str) -> float:
    """Computes similarity (0.0 to 100.0) between normalized company strings."""
    clean_raw = normalize_company_name(raw_name)
    clean_official = normalize_company_name(official_name)
    
    if not clean_raw or not clean_official:
        return 0.0
        
    return float(fuzz.token_set_ratio(clean_raw, clean_official))


class MatchingPipelineService:
    def __init__(
        self,
        db_session: AsyncSession,
        auto_match_threshold: float = 85.0,
        review_threshold: float = 70.0,
    ):
        self.db_session = db_session
        self.auto_match_threshold = auto_match_threshold
        self.review_threshold = review_threshold

    async def process_unmatched_raw_names(self) -> None:
        """
        Itera sobre todos os RawNames não mapeados e tenta vinculá-los aos Clientes oficiais.
        - Score >= auto_match_threshold: Vincula diretamente RawName e GenerationProject.
        - Score >= review_threshold: Envia para a tabela de PendingConsolidation.
        - Score < review_threshold: Ignora.
        """
        raw_names_stmt = select(RawName).where(RawName.cliente_id.is_(None))
        unmatched_raws = (await self.db_session.execute(raw_names_stmt)).scalars().all()

        if not unmatched_raws:
            return

        clients_stmt = select(Client)
        official_clients = (await self.db_session.execute(clients_stmt)).scalars().all()

        for raw in unmatched_raws:
            best_match: Client | None = None
            highest_score: float = 0.0

            for client in official_clients:
                score = compute_similarity_score(raw.nome_bruto, client.nome_oficial)
                if score > highest_score:
                    highest_score = score
                    best_match = client

            if not best_match:
                continue

            if highest_score >= self.auto_match_threshold:
                # 3a. Correspondência de Alta Confiança (Auto-Match)
                raw.cliente_id = best_match.id

                projects_stmt = select(GenerationProject).where(
                    GenerationProject.nome_bruto_principal_id == raw.id
                )
                projects = (await self.db_session.execute(projects_stmt)).scalars().all()
                for project in projects:
                    project.cliente_id = best_match.id

            elif highest_score >= self.review_threshold:
                # 3b. Correspondência Ambígua (Auditoria Manual)
                pending_stmt = select(PendingConsolidation).where(
                    PendingConsolidation.nome_bruto_id == raw.id
                )
                existing_pending = (
                    await self.db_session.execute(pending_stmt)
                ).scalar_one_or_none()

                if not existing_pending:
                    new_pending = PendingConsolidation(
                        nome_bruto_id=raw.id,
                        cliente_sugerido_id=best_match.id,
                        score_similaridade=highest_score,
                        status=ConsolidationStatus.pendente,
                        # Ajuste a linha abaixo caso o nome do seu Enum seja diferente
                        motivo_pendencia=MotivoPendenciaEnum.consolidacao_nome 
                    )
                    self.db_session.add(new_pending)

        await self.db_session.commit()