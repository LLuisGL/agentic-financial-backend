"""Endpoints planos compatibles con las skills Jelou v1 (/extraer, /validar, /calcular, /auditoria)."""

from __future__ import annotations

import datetime
import json
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import mensajes, models, negociacion as negociacion_service, validations
from app.database import get_db
from app.serializers import caso_a_dict

router = APIRouter(tags=["legacy-v1"])


def _parse_fecha(value):
    if not value:
        return None
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _upsert_cliente_titulo(db: Session, data: dict) -> tuple[models.Cliente, models.Titulo | None]:
    ruc = str(data.get("ruc") or data.get("ruc_cedula") or "").strip()
    titular = str(data.get("titular") or data.get("razon_social") or "").strip() or "Sin titular"
    numero = str(data.get("numero_titulo") or "").strip() or None
    tipo = str(data.get("tipo_nota") or "NCD").strip() or "NCD"
    valor = data.get("valor_nominal")
    saldo = data.get("saldo_disponible")
    if valor is None:
        valor = 0.0
    valor = float(valor)
    if saldo is None:
        saldo = valor
    saldo = float(saldo)
    fecha = _parse_fecha(data.get("fecha_emision"))
    url_doc = data.get("url_pdf") or data.get("url_documento")

    cliente = db.query(models.Cliente).filter(models.Cliente.ruc_cedula == ruc).first() if ruc else None
    if cliente is None:
        cliente = models.Cliente(
            ruc_cedula=ruc or f"TEMP-{uuid.uuid4().hex[:8]}",
            razon_social=titular,
            tipo_persona="NATURAL",
        )
        db.add(cliente)
        db.flush()
    else:
        if titular:
            cliente.razon_social = titular

    titulo = None
    if numero:
        titulo = db.query(models.Titulo).filter(models.Titulo.numero_titulo == numero).first()
        if titulo is None:
            titulo = models.Titulo(
                cliente_id=cliente.id,
                numero_titulo=numero,
                tipo_nota=tipo,
                valor_nominal=valor,
                saldo_disponible=saldo,
                fecha_emision=fecha,
                url_documento=url_doc,
            )
            db.add(titulo)
            db.flush()
        else:
            titulo.cliente_id = cliente.id
            titulo.tipo_nota = tipo or titulo.tipo_nota
            titulo.valor_nominal = valor
            titulo.saldo_disponible = saldo
            if fecha:
                titulo.fecha_emision = fecha
            if url_doc:
                titulo.url_documento = url_doc
    return cliente, titulo


def _caso_abierto_para_titulo(db: Session, titulo: models.Titulo | None) -> models.Caso | None:
    if titulo is None:
        return None
    return (
        db.query(models.Caso)
        .filter(
            models.Caso.titulo_id == titulo.id,
            models.Caso.estado.notin_(["CERRADO", "RECHAZADO"]),
        )
        .order_by(models.Caso.creado_en.desc())
        .first()
    )


def _cerrar_duplicados_viejos(db: Session, titulo: models.Titulo | None, caso_actual: models.Caso) -> None:
    if titulo is None:
        return
    otros = (
        db.query(models.Caso)
        .filter(
            models.Caso.titulo_id == titulo.id,
            models.Caso.id != caso_actual.id,
            models.Caso.estado.notin_(["CERRADO", "RECHAZADO"]),
        )
        .all()
    )
    for c in otros:
        c.estado = "CERRADO"
        c.proxima_accion = "Cerrado automáticamente al reabrir el mismo título"
        db.add(
            models.EventoCaso(
                caso_id=c.id,
                tipo="CIERRE_AUTO",
                descripcion=f"Cerrado al reutilizar el título en caso #{caso_actual.id}.",
                data_json=json.dumps({"reemplazado_por": caso_actual.id}),
            )
        )


@router.post("/validar")
async def validar_plano(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    cliente, titulo = _upsert_cliente_titulo(db, data)
    operador = str(data.get("operador") or data.get("usuario") or "operador-whatsapp")

    caso = _caso_abierto_para_titulo(db, titulo)
    if caso is None:
        caso = models.Caso(
            cliente_id=cliente.id,
            titulo_id=titulo.id if titulo else None,
            operador=operador,
            estado="RECIBIDO",
            proxima_accion="Ejecutar validaciones del expediente",
        )
        db.add(caso)
        db.flush()
    else:
        caso.cliente_id = cliente.id
        caso.operador = operador
        if titulo:
            caso.titulo_id = titulo.id

    _cerrar_duplicados_viejos(db, titulo, caso)
    resultado = validations.validar_caso(db, caso)

    if resultado.get("estadoNota") == "APROBADO":
        caso.estado = "VALIDADO"
        caso.proxima_accion = "Continuar con la propuesta económica de negociación"
    else:
        caso.estado = "EN_VALIDACION" if resultado.get("pendientes") else "VALIDADO"
        caso.proxima_accion = str(resultado.get("siguiente_accion_sugerida") or "Revisión")

    db.add(
        models.EventoCaso(
            caso_id=caso.id,
            tipo="VALIDACION",
            descripcion=f"Validación plana: {len(resultado.get('pendientes') or [])} pendiente(s).",
            data_json=json.dumps(resultado, default=str),
        )
    )
    db.commit()
    db.refresh(caso)

    return {
        "status": "success",
        "caso_id": caso.id,
        "analisis_id": str(data.get("analisis_id") or caso.id),
        "es_valido": resultado.get("estadoNota") == "APROBADO",
        "estado_riesgo": resultado.get("estadoNota"),
        "estadoNota": resultado.get("estadoNota"),
        "siguiente_accion": resultado.get("siguienteAccion") or resultado.get("siguiente_accion_sugerida"),
        "siguienteAccion": resultado.get("siguienteAccion") or "",
        "siguiente_accion_sugerida": resultado.get("siguiente_accion_sugerida"),
        "mensaje_operador": resultado.get("mensaje_operador"),
        "pendientes": resultado.get("pendientes") or [],
        "saldo_remanente": resultado.get("saldo_remanente"),
        "estado_flujo": resultado.get("estado_flujo"),
        "caso": caso_a_dict(caso, incluir_relaciones=False),
    }


@router.post("/calcular")
async def calcular_plano(request: Request):
    data = await request.json()
    try:
        valor = float(data.get("valor_nominal") or data.get("monto_negociar") or 0)
        pct = float(data.get("porcentaje_propuesta") or data.get("precio_negociacion_pct") or 0)
    except (TypeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "mensaje": "valor_nominal y porcentaje_propuesta son obligatorios."},
        )
    if valor <= 0 or pct <= 0 or pct > 100:
        return JSONResponse(status_code=400, content={"status": "error", "mensaje": "Monto o porcentaje inválido."})

    calc = negociacion_service.calcular_propuesta(valor, pct, float(data.get("otros_costos") or 0))
    ticket = mensajes.mensaje_propuesta_ticket(
        negociacion=calc,
        titular=data.get("titular"),
        ruc=data.get("ruc"),
        codigo_nota=data.get("numero_titulo"),
    )
    return {
        "status": "success",
        "analisis_id": data.get("analisis_id"),
        "vneto": calc["valor_neto"],
        "valor_neto": calc["valor_neto"],
        "comision": round(calc["comision_bolsa"] + calc["comision_casa"], 2),
        "comision_bolsa": calc["comision_bolsa"],
        "comision_casa": calc["comision_casa"],
        "valor_efectivo": calc["valor_efectivo"],
        "mensaje_propuesta": ticket,
        "borrador_texto": ticket,
        **calc,
    }


@router.post("/auditoria")
async def auditoria_plana(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    analisis = data.get("analisis_id") or data.get("caso_id")
    guardar = bool(data.get("guardar", True))
    caso = None
    if analisis is not None and str(analisis).isdigit():
        caso = db.get(models.Caso, int(analisis))
    if caso is None and data.get("numero_titulo"):
        titulo = db.query(models.Titulo).filter(models.Titulo.numero_titulo == str(data["numero_titulo"])).first()
        caso = _caso_abierto_para_titulo(db, titulo) if titulo else None

    if caso is not None and guardar:
        if caso.estado not in ("CERRADO", "RECHAZADO"):
            caso.estado = "CERRADO"
        caso.proxima_accion = "Expediente registrado en auditoría"
        db.add(
            models.EventoCaso(
                caso_id=caso.id,
                tipo="AUDITORIA",
                descripcion="Expediente confirmado por el operador (skill auditoría).",
                data_json=json.dumps({"guardar": True}),
            )
        )
        db.commit()
        db.refresh(caso)
        mensaje = mensajes.mensaje_expediente(caso_a_dict(caso))
    else:
        mensaje = (
            "✅ Operación registrada con éxito y expediente guardado. "
            "¿Desea ingresar y procesar una nueva nota de crédito?"
        )
    return {"status": "success", "mensaje": mensaje, "mensaje_auditoria": mensaje, "analisis_id": analisis}
