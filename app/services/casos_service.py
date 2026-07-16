from __future__ import annotations

import datetime
import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

import app.validations as validations
from app import mensajes, models
from app.dto.caso_crear_dto import CasoCrearRequest
from app.dto.cierre_dto import CierreRequest
from app.dto.diligencia_dto import DiligenciaRequest
from app.dto.propuesta_dto import PropuestaRequest
from app.dto.recomendacion_dto import RecomendacionRequest
import app.negociacion as negociacion_service
from app.serializers import caso_a_dict, negociacion_a_dict

ACCIONES_CIERRE_VALIDAS = {"LIQUIDACION", "TRANSFERENCIA", "ENDOSO"}


def _registrar_evento(db: Session, caso: models.Caso, tipo: str, descripcion: str, data: dict | None = None) -> None:
    db.add(
        models.EventoCaso(
            caso_id=caso.id,
            tipo=tipo,
            descripcion=descripcion,
            data_json=json.dumps(data, default=str) if data is not None else None,
        )
    )


def _obtener_caso_o_404(db: Session, caso_id: int) -> models.Caso:
    caso = db.get(models.Caso, caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="Caso no encontrado.")
    return caso


def _accion_legible(siguiente_accion: str) -> str:
    return {
        "SOLICITAR_DOCUMENTO": "Solicitar documento faltante al cliente",
        "ACTUALIZAR_DATO": "Actualizar dato con el operador",
        "ENVIAR_A_CUMPLIMIENTO": "Enviar a cumplimiento para revisión",
        "PREPARAR_ORDEN": "Preparar orden de negociación",
        "CONTINUAR": "Continuar con la propuesta económica de negociación",
    }[siguiente_accion]


def crear_caso(db: Session, payload: CasoCrearRequest):
    """HU1: crea el expediente solo con los campos que el operador confirmó o editó."""
    acciones = {c.campo: c.accion for c in payload.campos} if payload.campos else {}

    def permitido(campo: str) -> bool:
        return acciones.get(campo, "confirmar") in ("confirmar", "editar")

    cliente = db.query(models.Cliente).filter(models.Cliente.ruc_cedula == payload.ruc_cedula).first()
    if cliente is None:
        cliente = models.Cliente(
            ruc_cedula=payload.ruc_cedula,
            razon_social=payload.razon_social,
            tipo_persona=payload.tipo_persona,
            representante_legal=payload.representante_legal if permitido("representante_legal") else None,
        )
        db.add(cliente)
        db.flush()
    else:
        if payload.razon_social and permitido("razon_social"):
            cliente.razon_social = payload.razon_social
        if payload.representante_legal and permitido("representante_legal"):
            cliente.representante_legal = payload.representante_legal

    titulo = None
    if payload.numero_titulo and permitido("numero_titulo"):
        titulo = db.query(models.Titulo).filter(models.Titulo.numero_titulo == payload.numero_titulo).first()
        if titulo is None:
            titulo = models.Titulo(
                cliente_id=cliente.id,
                numero_titulo=payload.numero_titulo,
                tipo_nota=payload.tipo_nota or "NCD",
                valor_nominal=payload.valor_nominal or 0.0,
                saldo_disponible=payload.saldo_disponible if payload.saldo_disponible is not None else (payload.valor_nominal or 0.0),
                fecha_emision=payload.fecha_emision,
                url_documento=payload.url_documento,
            )
            db.add(titulo)
            db.flush()
        else:
            if payload.fecha_emision and permitido("fecha_emision"):
                titulo.fecha_emision = payload.fecha_emision
            if payload.tipo_nota and permitido("tipo_nota"):
                titulo.tipo_nota = payload.tipo_nota
            if payload.valor_nominal is not None and permitido("valor_nominal"):
                titulo.valor_nominal = payload.valor_nominal
            if payload.saldo_disponible is not None and permitido("saldo_disponible"):
                titulo.saldo_disponible = payload.saldo_disponible

    caso = models.Caso(
        cliente_id=cliente.id,
        titulo_id=titulo.id if titulo else None,
        operador=payload.operador,
        estado="RECIBIDO",
        proxima_accion="Ejecutar validaciones del expediente",
    )
    db.add(caso)
    db.flush()

    _registrar_evento(
        db,
        caso,
        "DATO_CONFIRMADO",
        "Expediente creado a partir de datos confirmados/editados por el operador.",
        {"campos_recibidos": [c.model_dump() for c in payload.campos]},
    )

    db.commit()
    db.refresh(caso)
    return caso_a_dict(caso)


def listar_casos(db: Session, estado: str | None = None, ruc_cedula: str | None = None):
    query = db.query(models.Caso)
    if estado:
        query = query.filter(models.Caso.estado == estado)
    if ruc_cedula:
        query = query.join(models.Cliente).filter(models.Cliente.ruc_cedula == ruc_cedula)
    return [caso_a_dict(c, incluir_relaciones=False) for c in query.order_by(models.Caso.creado_en.desc()).all()]


def obtener_caso(db: Session, caso_id: int):
    data = caso_a_dict(_obtener_caso_o_404(db, caso_id))
    data["mensaje_auditoria"] = mensajes.mensaje_expediente(data)
    return data


def validar_caso(db: Session, caso_id: int):
    """HU2: valida existencia/saldo/estado/bloqueos, duplicados y riesgo; sugiere el siguiente paso."""
    caso = _obtener_caso_o_404(db, caso_id)
    resultado = validations.validar_caso(db, caso)

    if resultado.get("estadoNota") == "APROBADO":
        caso.estado = "VALIDADO"
    else:
        caso.estado = "EN_VALIDACION" if resultado["pendientes"] else "VALIDADO"

    caso.proxima_accion = _accion_legible(resultado["siguiente_accion_sugerida"])
    _registrar_evento(db, caso, "VALIDACION", f"Validación ejecutada: {len(resultado['pendientes'])} pendiente(s).", resultado)
    db.commit()

    return {"caso_id": caso.id, "estado": caso.estado, **resultado}


def registrar_diligencia(db: Session, caso_id: int, payload: DiligenciaRequest):
    """HU2 (debida diligencia): registra el checklist KYC y cruza contra la lista de riesgo."""
    caso = _obtener_caso_o_404(db, caso_id)
    hay_riesgo, detalle_riesgo, _ = validations.validar_riesgo(db, caso.cliente)

    pendientes = []
    if not payload.identidad_ok:
        pendientes.append("identidad_no_verificada")
    if not payload.capacidad_legal_ok:
        pendientes.append("capacidad_legal_no_verificada")
    if caso.cliente.tipo_persona == "JURIDICA" and not payload.representacion_legal_ok:
        pendientes.append("representacion_legal_no_verificada")
    if not payload.kyc_formulario_ok:
        pendientes.append("formulario_kyc_incompleto")
    if not payload.origen_fondos_ok:
        pendientes.append("origen_fondos_no_justificado")
    if hay_riesgo:
        pendientes.append("coincidencia_lista_riesgo")

    resultado = "RECHAZADO" if (not payload.identidad_ok or not payload.capacidad_legal_ok) else ("PENDIENTE" if pendientes else "APROBADO")

    diligencia = caso.diligencia or models.DebidaDiligencia(caso_id=caso.id)
    diligencia.identidad_ok = payload.identidad_ok
    diligencia.capacidad_legal_ok = payload.capacidad_legal_ok
    diligencia.representacion_legal_ok = payload.representacion_legal_ok
    diligencia.beneficiario_final = payload.beneficiario_final
    diligencia.kyc_formulario_ok = payload.kyc_formulario_ok
    diligencia.origen_fondos_ok = payload.origen_fondos_ok
    diligencia.riesgo_match = hay_riesgo
    diligencia.riesgo_detalle = detalle_riesgo
    diligencia.resultado = resultado
    diligencia.pendientes_json = json.dumps(pendientes)
    db.add(diligencia)

    caso.estado = {"APROBADO": "DILIGENCIA_APROBADA", "PENDIENTE": "PENDIENTE_DOCUMENTO", "RECHAZADO": "RECHAZADO"}[resultado]
    caso.proxima_accion = {
        "APROBADO": "Continuar con la validación de la nota",
        "PENDIENTE": "Completar documentación KYC pendiente",
        "RECHAZADO": "Caso rechazado en debida diligencia; requiere revisión de cumplimiento",
    }[resultado]

    _registrar_evento(db, caso, "DILIGENCIA", f"Debida diligencia: resultado {resultado}.", {"pendientes": pendientes, "riesgo": detalle_riesgo})
    db.commit()

    return {"caso_id": caso.id, "resultado": resultado, "pendientes": pendientes, "riesgo_detalle": detalle_riesgo}


def recomendar_precio(db: Session, caso_id: int, payload: RecomendacionRequest):
    """HU3: mediana de la tabla referencial BVQ + % recomendado por IA (sin persistir negociación)."""
    caso = _obtener_caso_o_404(db, caso_id)
    valor_base = payload.monto_negociar
    if valor_base is None and caso.titulo is not None:
        valor_base = caso.titulo.saldo_disponible if caso.titulo.saldo_disponible is not None else caso.titulo.valor_nominal
    tipo_nota = payload.tipo_nota or (caso.titulo.tipo_nota if caso.titulo else None)

    recomendacion = negociacion_service.construir_recomendacion_propuesta(
        valor_base=valor_base,
        tipo_nota=tipo_nota,
        precio_minimo_cliente=payload.precio_minimo_cliente,
        otros_costos=payload.otros_costos,
    )
    _registrar_evento(db, caso, "RECOMENDACION_PRECIO", "Se generó recomendación de precio (HITL).", recomendacion)
    db.commit()
    return {"caso_id": caso.id, **recomendacion}


def crear_propuesta(db: Session, caso_id: int, payload: PropuestaRequest):
    """HU3: calcula VE/Vneto y genera borrador. Exige % del operador (nunca asume 96% ni otro default)."""
    caso = _obtener_caso_o_404(db, caso_id)
    if caso.titulo is None:
        raise HTTPException(status_code=409, detail="El caso no tiene un título/nota de crédito asociado.")

    valor_base = payload.monto_negociar
    if valor_base is None:
        valor_base = caso.titulo.saldo_disponible if caso.titulo.saldo_disponible is not None else caso.titulo.valor_nominal

    precio = payload.precio_negociacion_pct
    if precio is None:
        raise HTTPException(
            status_code=400,
            detail={
                "mensaje": mensajes.PREGUNTA_PORCENTAJE,
                "pregunta_porcentaje": mensajes.PREGUNTA_PORCENTAJE,
                "hint": (
                    "Indique precio_negociacion_pct con el porcentaje confirmado por el operador. "
                    "No se asume 96% ni ningún otro valor por defecto. "
                    "Puede consultar /negociacion/recomendacion solo como referencia."
                ),
            },
        )

    recomendacion = None
    if payload.incluir_recomendacion:
        recomendacion = negociacion_service.construir_recomendacion_propuesta(
            valor_base=valor_base,
            tipo_nota=caso.titulo.tipo_nota,
            precio_minimo_cliente=payload.precio_minimo_cliente,
            otros_costos=payload.otros_costos,
        )

    calculo = negociacion_service.calcular_propuesta(valor_base, float(precio), payload.otros_costos)

    negociacion = models.Negociacion(
        caso_id=caso.id,
        vigencia_autorizacion=payload.vigencia_autorizacion,
        instrucciones_especiales=payload.instrucciones_especiales,
        cuenta_destino=payload.cuenta_destino,
        estado="BORRADOR",
        **calculo,
    )
    db.add(negociacion)
    db.flush()

    try:
        saldo_actual = float(caso.titulo.saldo_disponible)
        saldo_post = max(0.0, round(saldo_actual - float(valor_base), 2))
    except (TypeError, ValueError):
        saldo_post = None

    ticket_payload = {**calculo, "saldo_remanente_post": saldo_post}
    negociacion.borrador_texto = mensajes.mensaje_propuesta_ticket(
        negociacion=ticket_payload,
        titular=caso.cliente.razon_social if caso.cliente else None,
        ruc=caso.cliente.ruc_cedula if caso.cliente else None,
        codigo_nota=caso.titulo.numero_titulo if caso.titulo else None,
        recomendacion=recomendacion,
    )

    caso.estado = "EN_NEGOCIACION"
    caso.proxima_accion = "Revisar y aprobar el borrador de negociación con el operador"

    evento_data = {"calculo": calculo, "recomendacion": recomendacion, "saldo_remanente_post": saldo_post}
    _registrar_evento(db, caso, "PROPUESTA", "Propuesta económica generada.", evento_data)
    db.commit()
    db.refresh(negociacion)

    body = negociacion_a_dict(negociacion)
    body["saldo_remanente_post"] = saldo_post
    body["mensaje_propuesta"] = negociacion.borrador_texto
    body["vneto"] = negociacion.valor_neto
    body["comision"] = round((negociacion.comision_bolsa or 0) + (negociacion.comision_casa or 0), 2)
    body["pregunta_porcentaje"] = mensajes.PREGUNTA_PORCENTAJE
    body["guardrail"] = mensajes.GUARDRAIL_CIERRE
    if recomendacion is not None:
        body["recomendacion"] = {
            "mediana": recomendacion["mediana"],
            "porcentaje_recomendado": recomendacion["porcentaje_recomendado"],
            "justificacion": recomendacion["justificacion"],
            "fuente": recomendacion["fuente"],
        }
    return body


def aprobar_negociacion(db: Session, caso_id: int, negociacion_id: int):
    caso = _obtener_caso_o_404(db, caso_id)
    negociacion = db.get(models.Negociacion, negociacion_id)
    if negociacion is None or negociacion.caso_id != caso.id:
        raise HTTPException(status_code=404, detail="Negociación no encontrada para este caso.")

    negociacion.estado = "APROBADA_OPERADOR"
    caso.estado = "NEGOCIACION_APROBADA"
    caso.proxima_accion = "Registrar el cierre de la operación con aprobación humana (sin liquidación automática)"

    _registrar_evento(db, caso, "APROBACION", f"Operador aprobó la negociación #{negociacion.id}.")
    db.commit()

    return {
        "caso_id": caso.id,
        "negociacion_id": negociacion.id,
        "estado": negociacion.estado,
        "mensaje": (
            "Propuesta aprobada por el operador. "
            "Pendiente registrar el cierre humano (sin liquidación automática en DECEVALE)."
        ),
        "mensaje_operador": (
            "Propuesta aprobada. Cuando registre el cierre del expediente, "
            "el sistema le preguntará si desea procesar una nueva nota."
        ),
        "guardrail": mensajes.GUARDRAIL_CIERRE,
    }


def solicitar_cierre(db: Session, caso_id: int, payload: CierreRequest):
    """HU3: deja liquidación/transferencia/endoso como propuesta o alerta; no ejecuta nada regulado."""
    caso = _obtener_caso_o_404(db, caso_id)
    if payload.accion not in ACCIONES_CIERRE_VALIDAS:
        raise HTTPException(status_code=400, detail=f"accion debe ser una de: {sorted(ACCIONES_CIERRE_VALIDAS)}")

    caso.estado = "PENDIENTE_APROBACION_CIERRE"
    caso.proxima_accion = "Pendiente de aprobación humana para cierre. No se ejecuta liquidación ni endoso automáticamente."
    if payload.observaciones:
        caso.observaciones = payload.observaciones

    _registrar_evento(
        db,
        caso,
        "SOLICITUD_APROBACION",
        f"Se solicita aprobación humana para {payload.accion}. Ninguna acción regulada fue ejecutada.",
        {"accion": payload.accion},
    )
    db.commit()

    return {
        "caso_id": caso.id,
        "estado": caso.estado,
        "accion_solicitada": payload.accion,
        "mensaje": mensajes.GUARDRAIL_CIERRE,
        "mensaje_operador": mensajes.mensaje_cierre_registrado(),
        "continuar": True,
    }