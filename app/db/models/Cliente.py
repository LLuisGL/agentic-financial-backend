from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

import datetime
from app.db.database import Base
from app.utils.now import _now

if TYPE_CHECKING:
    from app.db.models.Caso import Caso
    from app.db.models.Titulo import Titulo

class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruc_cedula: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(255))
    tipo_persona: Mapped[str] = mapped_column(String(20), default="NATURAL")  # NATURAL | JURIDICA
    representante_legal: Mapped[str] = mapped_column(String(255), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    titulos: Mapped[list[Titulo]] = relationship(back_populates="cliente")
    casos: Mapped[list[Caso]] = relationship(back_populates="cliente")