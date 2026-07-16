from pydantic import BaseModel

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