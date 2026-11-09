from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.cliente_schema import ClienteDropdownOut
from backend.app.services import cliente_service
# from backend.app.core.auth_dependencies import get_current_user # Descomente se usar proteção

router = APIRouter(
    prefix="/api/clientes", 
    tags=["Clientes"],
    # dependencies=[Depends(get_current_user)] # Descomente se usar proteção
)

@router.get(
    "", 
    response_model=List[ClienteDropdownOut], 
    summary="Lista simplificada de clientes para dropdowns"
)
async def listar_clientes(db: AsyncSession = Depends(get_db)):
    return await cliente_service.obter_clientes_dropdown(db)