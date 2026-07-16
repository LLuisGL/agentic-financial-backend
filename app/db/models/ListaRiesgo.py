from __future__ import annotations
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

class ListaRiesgo(Base):
    """Lista simulada de sanciones / PEP para cruce de coincidencias de riesgo."""

    __tablename__ = "lista_riesgo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruc_cedula: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    motivo: Mapped[str] = mapped_column(String(50))  # PEP | SANCIONADO | LISTA_OFAC_SIMULADA
    nivel: Mapped[str] = mapped_column(String(10), default="ALTO")  # ALTO | MEDIO | BAJO