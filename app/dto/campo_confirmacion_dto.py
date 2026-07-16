from pydantic import BaseModel, Field

class CampoConfirmacion(BaseModel):
    campo: str
    valor: str | float | None = None
    accion: str = Field(description="confirmar | editar | rechazar")