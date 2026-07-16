from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers import clientes_controller
from app.db.database import get_db
from app.dto.cliente_buscar_dto import ClienteBuscarRequest
from app.dto.cliente_buscar_response_dto import ClienteBuscarResponse

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post("/buscar", response_model=ClienteBuscarResponse)
def buscar_cliente(payload: ClienteBuscarRequest, db: Session = Depends(get_db)):
    return clientes_controller.buscar_cliente(db, payload)


@router.get("/{cliente_id}")
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    return clientes_controller.obtener_cliente(db, cliente_id)