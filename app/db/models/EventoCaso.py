from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

import datetime
from app.db.database import Base
from app.utils.now import _now

if TYPE_CHECKING:
    from app.db.models.Caso import Caso

class EventoCaso(Base):
    """Bitácora del expediente: qué pasó, cuándo y con qué datos."""

    __tablename__ = "eventos_caso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id"))
    tipo: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(Text)
    data_json: Mapped[str] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    caso: Mapped[Caso] = relationship(back_populates="eventos")