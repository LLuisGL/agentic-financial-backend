    
from app.dto.campo_confirmacion_dto import CampoConfirmacion
from datetime import date
from pydantic import BaseModel

class CasoCrearRequest(BaseModel):
    operador: str
    ruc_cedula: str
    razon_social: str
    tipo_persona: str = "NATURAL"
    representante_legal: str | None = None
    numero_titulo: str | None = None
    tipo_nota: str | None = None
    valor_nominal: float | None = None
    saldo_disponible: float | None = None
    fecha_emision: date | None = None
    url_documento: str | None = None
    campos: list[CampoConfirmacion] = []