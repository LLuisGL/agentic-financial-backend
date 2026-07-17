import datetime

from pydantic import BaseModel, Field


class ClienteBuscarRequest(BaseModel):
    ruc_cedula: str | None = None
    razon_social: str | None = None
    numero_titulo: str | None = None


class DatoReutilizable(BaseModel):
    campo: str
    valor: str | float | None
    fuente: str
    fecha: datetime.datetime | None
    estado: str


class ClienteBuscarResponse(BaseModel):
    encontrado: bool
    cliente: dict | None = None
    datos_reutilizables: list[DatoReutilizable] = []
    titulos_anteriores: list[dict] = []
    casos_anteriores: list[dict] = []


class CampoConfirmacion(BaseModel):
    campo: str
    valor: str | float | None = None
    accion: str = Field(description="confirmar | editar | rechazar")


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
    url_documento: str | None = None
    campos: list[CampoConfirmacion] = []


class DiligenciaRequest(BaseModel):
    identidad_ok: bool
    capacidad_legal_ok: bool
    representacion_legal_ok: bool | None = None
    beneficiario_final: str | None = None
    kyc_formulario_ok: bool
    origen_fondos_ok: bool


class PropuestaRequest(BaseModel):
    precio_negociacion_pct: float | None = None
    monto_a_retirar: float | None = None
    otros_costos: float = 0.0
    vigencia_autorizacion: str | None = None
    instrucciones_especiales: str | None = None
    cuenta_destino: str | None = None


class CierreRequest(BaseModel):
    accion: str = Field(description="LIQUIDACION | TRANSFERENCIA | ENDOSO")
    observaciones: str | None = None
