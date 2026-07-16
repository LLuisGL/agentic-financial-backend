from pydantic import BaseModel

class RecomendacionRequest(BaseModel):
    monto_negociar: float | None = None
    tipo_nota: str | None = None
    precio_minimo_cliente: float | None = None
    otros_costos: float = 0.0