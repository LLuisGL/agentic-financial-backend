from __future__ import annotations

import datetime

from pydantic import BaseModel, Field

class DatoReutilizable(BaseModel):
    campo: str
    valor: str | float | None
    fuente: str
    fecha: datetime.datetime | None = Field(default=None)
    estado: str