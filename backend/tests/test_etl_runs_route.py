import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.models import EtlRun, EtlRunStatus

@pytest.mark.asyncio
async def test_get_etl_runs_pagination(
    async_client: AsyncClient, 
    db_session: AsyncSession
):
    # Setup
    runs_to_insert = [
        EtlRun(
            status=EtlRunStatus.sucesso,
            linhas_processadas=100 + i
        ) for i in range(15)
    ]
    db_session.add_all(runs_to_insert)
    await db_session.commit()

    # Act
    # Ajuste a URL base dependendo de como você registrou o router no main.py
    response = await async_client.get("/api/etl-runs?page=2&size=10")

    # Assert
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 15
    assert data["page"] == 2
    assert data["size"] == 10
    assert data["total_pages"] == 2
    assert len(data["items"]) == 5
    
    first_item = data["items"][0]
    assert "id" in first_item
    assert "iniciado_em" in first_item
    assert first_item["status"] == EtlRunStatus.sucesso.value