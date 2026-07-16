from pydantic import BaseModel, Field

class CierreRequest(BaseModel):
    accion: str = Field(description="LIQUIDACION | TRANSFERENCIA | ENDOSO")
    observaciones: str | None = None