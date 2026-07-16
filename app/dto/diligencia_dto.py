from pydantic import BaseModel

class DiligenciaRequest(BaseModel):
    identidad_ok: bool
    capacidad_legal_ok: bool
    representacion_legal_ok: bool | None = None
    beneficiario_final: str | None = None
    kyc_formulario_ok: bool
    origen_fondos_ok: bool