from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

import datetime
from app.db.database import Base
from app.utils.now import _now

if TYPE_CHECKING:
    from app.db.models.Caso import Caso
    from app.db.models.Cliente import Cliente


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
    fecha_emision: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    tiene_restriccion: Mapped[bool] = mapped_column(Boolean, default=False)  # retención / embargo
    url_documento: Mapped[str] = mapped_column(String(500), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    cliente: Mapped[Cliente] = relationship(back_populates="titulos")
    casos: Mapped[list[Caso]] = relationship(back_populates="titulo")
