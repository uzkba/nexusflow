from pydantic import BaseModel
from uuid import UUID

class ClienteDropdownOut(BaseModel):
    """Schema para popular caixas de seleção (dropdowns) no frontend."""
    id: UUID
    nome_oficial: str