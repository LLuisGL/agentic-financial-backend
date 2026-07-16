from __future__ import annotations

from sqlalchemy.orm import Session

from app.dto.caso_crear_dto import CasoCrearRequest
from app.dto.cierre_dto import CierreRequest
from app.dto.diligencia_dto import DiligenciaRequest
from app.dto.propuesta_dto import PropuestaRequest
from app.dto.recomendacion_dto import RecomendacionRequest
from app.services import casos_service


def crear_caso(db: Session, payload: CasoCrearRequest):
    return casos_service.crear_caso(db, payload)


def listar_casos(db: Session, estado: str | None = None, ruc_cedula: str | None = None):
    return casos_service.listar_casos(db, estado=estado, ruc_cedula=ruc_cedula)


def obtener_caso(db: Session, caso_id: int):
    return casos_service.obtener_caso(db, caso_id)


def validar_caso(db: Session, caso_id: int):
    return casos_service.validar_caso(db, caso_id)


def registrar_diligencia(db: Session, caso_id: int, payload: DiligenciaRequest):
    return casos_service.registrar_diligencia(db, caso_id, payload)


def recomendar_precio(db: Session, caso_id: int, payload: RecomendacionRequest):
    return casos_service.recomendar_precio(db, caso_id, payload)


def crear_propuesta(db: Session, caso_id: int, payload: PropuestaRequest):
    return casos_service.crear_propuesta(db, caso_id, payload)


def aprobar_negociacion(db: Session, caso_id: int, negociacion_id: int):
    return casos_service.aprobar_negociacion(db, caso_id, negociacion_id)


def solicitar_cierre(db: Session, caso_id: int, payload: CierreRequest):
    return casos_service.solicitar_cierre(db, caso_id, payload)