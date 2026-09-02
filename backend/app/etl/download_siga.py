

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

SIGA_CSV_URL = (
    "https://dadosabertos.aneel.gov.br/dataset/"
    "6d90b77c-c5f5-4d81-bdec-7bc619494bb9/resource/"
    "2f65a1b0-19b8-4360-8238-b34ab4693d55/download/"
    "siga-empreendimentos-geracao-diario.csv"
)

DEFAULT_TIMEOUT_SECONDS = 120.0 


class SigaDownloadError(Exception):
    """Erro ao baixar o CSV da ANEEL — timeout, endpoint fora do ar, resposta não-2xx."""


@dataclass
class DownloadResult:
    raw_path: Path
    downloaded_at: datetime
    size_bytes: int
    sha256: str
    http_status: int


async def download_siga_csv(
    raw_dir: Path,
    url: str = SIGA_CSV_URL,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> DownloadResult:
    raw_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
   
    filename = f"siga-empreendimentos-geracao-diario_{now.strftime('%Y%m%dT%H%M%SZ')}.csv"
    raw_path = raw_dir / filename

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url)
    except httpx.TimeoutException as exc:
        raise SigaDownloadError(f"Timeout ao baixar CSV da ANEEL após {timeout_seconds}s") from exc
    except httpx.ConnectError as exc:
        raise SigaDownloadError("Não foi possível conectar ao endpoint da ANEEL (endpoint fora do ar?)") from exc
    except httpx.HTTPError as exc:
        raise SigaDownloadError(f"Erro de rede ao baixar CSV da ANEEL: {exc}") from exc

    if response.status_code != 200:
        raise SigaDownloadError(
            f"ANEEL retornou status {response.status_code} para {url} "
            f"(esperado 200). Corpo (primeiros 300 chars): {response.text[:300]!r}"
        )

    content = response.content
    if not content:
        raise SigaDownloadError("ANEEL retornou resposta vazia (0 bytes) — provável CSV malformado/indisponível")

    raw_path.write_bytes(content)

    return DownloadResult(
        raw_path=raw_path,
        downloaded_at=now,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        http_status=response.status_code,
    )