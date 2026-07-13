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
    fecha_emision: datetime.date | None = None
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
    # Obligatorio en la práctica: nunca se asume 96% ni otro default.
    # Si falta, el endpoint responde pidiendo el % al operador.
    precio_negociacion_pct: float | None = None
    otros_costos: float = 0.0
    vigencia_autorizacion: str | None = None
    instrucciones_especiales: str | None = None
    cuenta_destino: str | None = None
    precio_minimo_cliente: float | None = None
    # Si se envía, se usa como base del VE en lugar del valor_nominal del título.
    monto_negociar: float | None = None
    # Opcional: adjunta mediana/IA solo como referencia en el ticket (no sustituye el %).
    incluir_recomendacion: bool = False


class RecomendacionRequest(BaseModel):
    monto_negociar: float | None = None
    tipo_nota: str | None = None
    precio_minimo_cliente: float | None = None
    otros_costos: float = 0.0


class CierreRequest(BaseModel):
    accion: str = Field(description="LIQUIDACION | TRANSFERENCIA | ENDOSO")
    observaciones: str | None = None
