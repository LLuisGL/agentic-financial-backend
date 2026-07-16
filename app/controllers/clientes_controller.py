from __future__ import annotations

from sqlalchemy.orm import Session

from app.dto.cliente_buscar_dto import ClienteBuscarRequest
from app.dto.cliente_buscar_response_dto import ClienteBuscarResponse
from app.services import clientes_service


def buscar_cliente(db: Session, payload: ClienteBuscarRequest) -> ClienteBuscarResponse:
    return clientes_service.buscar_cliente(db, payload)


def obtener_cliente(db: Session, cliente_id: int):
    return clientes_service.obtener_cliente(db, cliente_id)