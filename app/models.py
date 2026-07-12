import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruc_cedula: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(255))
    tipo_persona: Mapped[str] = mapped_column(String(20), default="NATURAL")  # NATURAL | JURIDICA
    representante_legal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    titulos: Mapped[list["Titulo"]] = relationship(back_populates="cliente")
    casos: Mapped[list["Caso"]] = relationship(back_populates="cliente")


class Titulo(Base):
    """Nota de crédito tributaria (NCD, ISD o NCE)."""

    __tablename__ = "titulos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    numero_titulo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    tipo_nota: Mapped[str] = mapped_column(String(10))  # NCD | ISD | NCE
    valor_nominal: Mapped[float] = mapped_column(Float)
    saldo_disponible: Mapped[float] = mapped_column(Float)
    estado: Mapped[str] = mapped_column(String(20), default="VIGENTE")  # VIGENTE|USADA|BLOQUEADA|ANULADA|CADUCADA
    fecha_emision: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    tiene_restriccion: Mapped[bool] = mapped_column(Boolean, default=False)  # retención / embargo
    url_documento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    cliente: Mapped["Cliente"] = relationship(back_populates="titulos")
    casos: Mapped[list["Caso"]] = relationship(back_populates="titulo")


class Caso(Base):
    """Expediente único del caso: estado, próxima acción, responsable, documentos."""

    __tablename__ = "casos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    titulo_id: Mapped[int | None] = mapped_column(ForeignKey("titulos.id"), nullable=True)
    operador: Mapped[str] = mapped_column(String(255))
    estado: Mapped[str] = mapped_column(String(30), default="RECIBIDO")
    proxima_accion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)
    actualizado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    cliente: Mapped["Cliente"] = relationship(back_populates="casos")
    titulo: Mapped["Titulo | None"] = relationship(back_populates="casos")
    eventos: Mapped[list["EventoCaso"]] = relationship(back_populates="caso", order_by="EventoCaso.creado_en")
    diligencia: Mapped["DebidaDiligencia | None"] = relationship(back_populates="caso", uselist=False)
    negociaciones: Mapped[list["Negociacion"]] = relationship(back_populates="caso", order_by="Negociacion.creado_en")


class EventoCaso(Base):
    """Bitácora del expediente: qué pasó, cuándo y con qué datos."""

    __tablename__ = "eventos_caso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id"))
    tipo: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(Text)
    data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    caso: Mapped["Caso"] = relationship(back_populates="eventos")


class DebidaDiligencia(Base):
    """Checklist de debida diligencia / KYC del cliente para un caso."""

    __tablename__ = "debida_diligencia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id"), unique=True)
    identidad_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    capacidad_legal_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    representacion_legal_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    beneficiario_final: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kyc_formulario_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    origen_fondos_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    riesgo_match: Mapped[bool] = mapped_column(Boolean, default=False)
    riesgo_detalle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resultado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")  # APROBADO | PENDIENTE | RECHAZADO
    pendientes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    caso: Mapped["Caso"] = relationship(back_populates="diligencia")


class ListaRiesgo(Base):
    """Lista simulada de sanciones / PEP para cruce de coincidencias de riesgo."""

    __tablename__ = "lista_riesgo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruc_cedula: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    motivo: Mapped[str] = mapped_column(String(50))  # PEP | SANCIONADO | LISTA_OFAC_SIMULADA
    nivel: Mapped[str] = mapped_column(String(10), default="ALTO")  # ALTO | MEDIO | BAJO


class Negociacion(Base):
    """Propuesta económica y borrador de negociación (HU3)."""

    __tablename__ = "negociaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id"))
    valor_nominal: Mapped[float] = mapped_column(Float)
    precio_negociacion_pct: Mapped[float] = mapped_column(Float)
    valor_efectivo: Mapped[float] = mapped_column(Float)  # VE
    descuento: Mapped[float] = mapped_column(Float)
    comision_bolsa: Mapped[float] = mapped_column(Float)  # CBVQ
    comision_casa: Mapped[float] = mapped_column(Float)  # Ccv
    otros_costos: Mapped[float] = mapped_column(Float, default=0.0)
    valor_neto: Mapped[float] = mapped_column(Float)  # Vneto
    vigencia_autorizacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instrucciones_especiales: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuenta_destino: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default="BORRADOR")
    borrador_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    caso: Mapped["Caso"] = relationship(back_populates="negociaciones")
