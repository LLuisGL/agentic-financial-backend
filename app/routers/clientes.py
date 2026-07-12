from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.serializers import caso_a_dict, cliente_a_dict, titulo_a_dict

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post("/buscar", response_model=schemas.ClienteBuscarResponse)
def buscar_cliente(payload: schemas.ClienteBuscarRequest, db: Session = Depends(get_db)):
    """HU1: busca antecedentes por RUC/cédula, razón social o número de título.

    Devuelve cada dato reutilizable con su fecha, fuente y estado para que el
    operador confirme, edite o rechace antes de guardarlo.
    """
    if not any([payload.ruc_cedula, payload.razon_social, payload.numero_titulo]):
        raise HTTPException(status_code=400, detail="Debe indicar ruc_cedula, razon_social o numero_titulo.")

    cliente = None
    if payload.numero_titulo:
        titulo = db.query(models.Titulo).filter(models.Titulo.numero_titulo == payload.numero_titulo).first()
        if titulo:
            cliente = titulo.cliente

    if cliente is None and payload.ruc_cedula:
        cliente = db.query(models.Cliente).filter(models.Cliente.ruc_cedula == payload.ruc_cedula).first()

    if cliente is None and payload.razon_social:
        cliente = (
            db.query(models.Cliente)
            .filter(or_(models.Cliente.razon_social.ilike(f"%{payload.razon_social}%")))
            .first()
        )

    if cliente is None:
        return schemas.ClienteBuscarResponse(encontrado=False)

    datos_reutilizables = [
        schemas.DatoReutilizable(campo="razon_social", valor=cliente.razon_social, fuente="clientes", fecha=cliente.creado_en, estado="CONFIABLE"),
        schemas.DatoReutilizable(campo="tipo_persona", valor=cliente.tipo_persona, fuente="clientes", fecha=cliente.creado_en, estado="CONFIABLE"),
    ]
    if cliente.representante_legal:
        datos_reutilizables.append(
            schemas.DatoReutilizable(campo="representante_legal", valor=cliente.representante_legal, fuente="clientes", fecha=cliente.creado_en, estado="CONFIABLE")
        )
    for titulo in cliente.titulos:
        datos_reutilizables.append(
            schemas.DatoReutilizable(campo=f"titulo:{titulo.numero_titulo}", valor=titulo.saldo_disponible, fuente="titulos", fecha=titulo.creado_en, estado=titulo.estado)
        )

    return schemas.ClienteBuscarResponse(
        encontrado=True,
        cliente=cliente_a_dict(cliente),
        datos_reutilizables=datos_reutilizables,
        titulos_anteriores=[titulo_a_dict(t) for t in cliente.titulos],
        casos_anteriores=[caso_a_dict(c, incluir_relaciones=False) for c in cliente.casos],
    )


@router.get("/{cliente_id}")
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.get(models.Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return {
        **cliente_a_dict(cliente),
        "titulos": [titulo_a_dict(t) for t in cliente.titulos],
        "casos": [caso_a_dict(c, incluir_relaciones=False) for c in cliente.casos],
    }