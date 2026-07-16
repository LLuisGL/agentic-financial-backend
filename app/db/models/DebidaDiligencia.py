from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

import datetime
from app.db.database import Base
from app.utils.now import _now

if TYPE_CHECKING:
    from app.db.models.Caso import Caso

class DebidaDiligencia(Base):
    """Checklist de debida diligencia / KYC del cliente para un caso."""

    __tablename__ = "debida_diligencia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id"), unique=True)
    identidad_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    capacidad_legal_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    representacion_legal_ok: Mapped[bool] = mapped_column(Boolean, nullable=True)
    beneficiario_final: Mapped[str] = mapped_column(String(255), nullable=True)
    kyc_formulario_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    origen_fondos_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    riesgo_match: Mapped[bool] = mapped_column(Boolean, default=False)
    riesgo_detalle: Mapped[str] = mapped_column(String(500), nullable=True)
    resultado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")  # APROBADO | PENDIENTE | RECHAZADO
    pendientes_json: Mapped[str] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    caso: Mapped[Caso] = relationship(back_populates="diligencia")
