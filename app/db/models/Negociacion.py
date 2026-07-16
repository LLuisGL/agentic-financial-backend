from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime

from app.db.database import Base
from app.utils.now import _now

if TYPE_CHECKING:
    from app.db.models.Caso import Caso

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
    vigencia_autorizacion: Mapped[str] = mapped_column(String(100), nullable=True)
    instrucciones_especiales: Mapped[str] = mapped_column(Text, nullable=True)
    cuenta_destino: Mapped[str] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default="BORRADOR")
    borrador_texto: Mapped[str] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    caso: Mapped[Caso] = relationship(back_populates="negociaciones")
