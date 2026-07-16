from pydantic import BaseModel, Field
from app.dto.dato_reutilizable_dto import DatoReutilizable

class ClienteBuscarResponse(BaseModel):
    encontrado: bool
    cliente: dict | None = None
    datos_reutilizables: list[DatoReutilizable] = Field(default_factory=list)
    titulos_anteriores: list[dict] = Field(default_factory=list)
    casos_anteriores: list[dict] = Field(default_factory=list)