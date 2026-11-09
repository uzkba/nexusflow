from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
# ATENÇÃO: Ajuste o import abaixo para o caminho correto do seu modelo de Cliente
from backend.app.model.models import Client

async def obter_clientes_dropdown(db: AsyncSession):
    """Procura o ID e o Nome de todos os clientes, ordenados alfabeticamente."""
    
    # Selecionamos apenas os campos necessários para ficar leve e rápido
    stmt = select(Client.id, Client.nome_oficial).order_by(Client.nome_oficial)
    resultado = await db.execute(stmt)
    
    return [{"id": row.id, "nome_oficial": row.nome_oficial} for row in resultado.all()]