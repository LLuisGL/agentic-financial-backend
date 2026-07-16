from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.controllers import casos_controller
from app.db.database import get_db
from app.dto.caso_crear_dto import CasoCrearRequest
from app.dto.cierre_dto import CierreRequest
from app.dto.diligencia_dto import DiligenciaRequest
from app.dto.propuesta_dto import PropuestaRequest
from app.dto.recomendacion_dto import RecomendacionRequest

router = APIRouter(prefix="/casos", tags=["casos"])


@router.post("")
def crear_caso(payload: CasoCrearRequest, db: Session = Depends(get_db)):
    return casos_controller.crear_caso(db, payload)


@router.get("")
def listar_casos(estado: str | None = None, ruc_cedula: str | None = None, db: Session = Depends(get_db)):
    return casos_controller.listar_casos(db, estado=estado, ruc_cedula=ruc_cedula)


@router.get("/{caso_id}")
def obtener_caso(caso_id: int, db: Session = Depends(get_db)):
    return casos_controller.obtener_caso(db, caso_id)


@router.post("/{caso_id}/validar")
def validar_caso(caso_id: int, db: Session = Depends(get_db)):
    return casos_controller.validar_caso(db, caso_id)


@router.post("/{caso_id}/diligencia")
def registrar_diligencia(caso_id: int, payload: DiligenciaRequest, db: Session = Depends(get_db)):
    return casos_controller.registrar_diligencia(db, caso_id, payload)


@router.post("/{caso_id}/negociacion/recomendacion")
def recomendar_precio(
    caso_id: int,
    payload: RecomendacionRequest = Body(default_factory=RecomendacionRequest),
    db: Session = Depends(get_db),
):
    return casos_controller.recomendar_precio(db, caso_id, payload)


@router.post("/{caso_id}/negociacion/propuesta")
def crear_propuesta(caso_id: int, payload: PropuestaRequest, db: Session = Depends(get_db)):
    return casos_controller.crear_propuesta(db, caso_id, payload)


@router.post("/{caso_id}/negociacion/{negociacion_id}/aprobar")
def aprobar_negociacion(caso_id: int, negociacion_id: int, db: Session = Depends(get_db)):
    return casos_controller.aprobar_negociacion(db, caso_id, negociacion_id)


@router.post("/{caso_id}/cierre")
def solicitar_cierre(caso_id: int, payload: CierreRequest, db: Session = Depends(get_db)):
    return casos_controller.solicitar_cierre(db, caso_id, payload)
