from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Integer, String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

import datetime
from app.db.database import Base
from app.utils.now import _now

if TYPE_CHECKING:
    from app.db.models.Cliente import Cliente
    from app.db.models.DebidaDiligencia import DebidaDiligencia
    from app.db.models.EventoCaso import EventoCaso
    from app.db.models.Negociacion import Negociacion
    from app.db.models.Titulo import Titulo

class Caso(Base):
    """Expediente único del caso: estado, próxima acción, responsable, documentos."""

    __tablename__ = "casos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    titulo_id: Mapped[int] = mapped_column(ForeignKey("titulos.id"), nullable=True)
    operador: Mapped[str] = mapped_column(String(255))
    estado: Mapped[str] = mapped_column(String(30), default="RECIBIDO")
    proxima_accion: Mapped[str] = mapped_column(String(255), nullable=True)
    observaciones: Mapped[str] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)
    actualizado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    cliente: Mapped[Cliente] = relationship(back_populates="casos")
    titulo: Mapped[Titulo] = relationship(back_populates="casos")
    eventos: Mapped[list[EventoCaso]] = relationship(back_populates="caso", order_by="EventoCaso.creado_en")
    diligencia: Mapped[DebidaDiligencia | None] = relationship(back_populates="caso", uselist=False)
    negociaciones: Mapped[list[Negociacion]] = relationship(back_populates="caso", order_by="Negociacion.creado_en")

