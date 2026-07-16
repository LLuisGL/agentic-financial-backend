"""Motor de validaciones (Historia de Usuario 2).

Valida existencia, saldo, estado y bloqueos de la nota contra la fuente
simulada, marca campos faltantes, duplicados y coincidencias de riesgo, y
sugiere el siguiente paso. Nunca ejecuta nada por sí mismo.

Parcialmente Negociada NO es error: se informa el saldo remanente y se continúa.
"""

import datetime

from sqlalchemy.orm import Session

from app import mensajes, models

VIGENCIA_ISD_ANIOS = 4

SIGUIENTE_ACCION_PRIORIDAD = [
    "SOLICITAR_DOCUMENTO",
    "ACTUALIZAR_DATO",
    "ENVIAR_A_CUMPLIMIENTO",
    "PREPARAR_ORDEN",
    "CONTINUAR",
]

ESTADOS_OK = {
    "VIGENTE",
    "DISPONIBLE",
    "PARCIALMENTE_NEGOCIADA",
    "PARCIALMENTE NEGOCIADA",
    "PARCIAL",
}


def _pendiente(tipo: str, campo: str, mensaje: str, evidencia: str, siguiente_accion: str) -> dict:
    return {
        "tipo": tipo,
        "campo": campo,
        "mensaje": mensaje,
        "evidencia_a_revisar": evidencia,
        "siguiente_accion_sugerida": siguiente_accion,
    }


def validar_cliente(cliente: models.Cliente) -> list[dict]:
    pendientes = []
    if not cliente.razon_social:
        pendientes.append(_pendiente("CAMPO_FALTANTE", "razon_social", "Falta razón social o nombre del titular.", "Cédula/RUC o constitución de la empresa", "SOLICITAR_DOCUMENTO"))
    if cliente.tipo_persona == "JURIDICA" and not cliente.representante_legal:
        pendientes.append(_pendiente("CAMPO_FALTANTE", "representante_legal", "Falta representante legal para persona jurídica.", "Nombramiento del representante legal", "SOLICITAR_DOCUMENTO"))
    return pendientes


def validar_titulo(titulo: models.Titulo | None, valor_solicitado: float | None) -> list[dict]:
    pendientes = []

    if titulo is None:
        pendientes.append(_pendiente("EXISTENCIA", "titulo", "La nota no fue encontrada en la fuente autorizada simulada.", "Estado de cuenta de la nota de crédito", "SOLICITAR_DOCUMENTO"))
        return pendientes

    estado_flujo = mensajes.clasificar_estado_negociacion(titulo)

    if estado_flujo == "TOTALMENTE_NEGOCIADA":
        pendientes.append(
            _pendiente(
                "SALDO",
                "saldo_disponible",
                "Saldo remanente: $0.00 (Nota consumida en su totalidad).",
                "Historial de negociaciones",
                "ENVIAR_A_CUMPLIMIENTO",
            )
        )
        return pendientes

    if estado_flujo == "BLOQUEADA":
        pendientes.append(_pendiente("BLOQUEO", "bloqueado", "El título está bloqueado y no puede negociarse.", "Detalle del bloqueo en el sistema interno", "ENVIAR_A_CUMPLIMIENTO"))
        return pendientes

    if estado_flujo == "CADUCADA":
        pendientes.append(_pendiente("VIGENCIA", "estado", "La nota figura como caducada.", "Fecha de emisión y tipo de nota", "ENVIAR_A_CUMPLIMIENTO"))
        return pendientes

    if titulo.estado and titulo.estado.upper() not in ESTADOS_OK and estado_flujo not in ("DISPONIBLE", "PARCIALMENTE_NEGOCIADA"):
        if titulo.estado.upper() not in ("USADA",):
            pendientes.append(_pendiente("ESTADO", "estado", f"El título tiene un estado que requiere revisión: {titulo.estado}.", "Consulta de estado en SRI/DECEVALE", "ACTUALIZAR_DATO"))

    if titulo.bloqueado:
        pendientes.append(_pendiente("BLOQUEO", "bloqueado", "El título está bloqueado.", "Detalle del bloqueo en el sistema interno", "ENVIAR_A_CUMPLIMIENTO"))

    if titulo.tiene_restriccion:
        pendientes.append(_pendiente("RESTRICCION", "tiene_restriccion", "El título tiene retención, embargo o restricción.", "Documento de retención/embargo", "ENVIAR_A_CUMPLIMIENTO"))

    if valor_solicitado is not None and valor_solicitado > titulo.saldo_disponible:
        pendientes.append(
            _pendiente(
                "SALDO",
                "valor_solicitado",
                f"El valor solicitado ({valor_solicitado:,.2f}) supera el saldo remanente disponible ({titulo.saldo_disponible:,.2f}).",
                "Estado de cuenta actualizado",
                "ACTUALIZAR_DATO",
            )
        )

    if titulo.tipo_nota == "ISD" and titulo.fecha_emision:
        vencimiento = titulo.fecha_emision.replace(year=titulo.fecha_emision.year + VIGENCIA_ISD_ANIOS)
        if datetime.date.today() > vencimiento:
            pendientes.append(_pendiente("VIGENCIA", "fecha_emision", f"Nota ISD caducada: vigente hasta {vencimiento.isoformat()} (4 años desde emisión).", "Fecha de emisión en el documento original", "ENVIAR_A_CUMPLIMIENTO"))

    return pendientes


def validar_duplicados(db: Session, titulo: models.Titulo | None, caso_actual_id: int | None) -> list[dict]:
    if titulo is None:
        return []
    query = db.query(models.Caso).filter(
        models.Caso.titulo_id == titulo.id,
        models.Caso.estado.notin_(["CERRADO", "RECHAZADO"]),
    )
    if caso_actual_id is not None:
        query = query.filter(models.Caso.id != caso_actual_id)
    otros_casos = query.all()
    if not otros_casos:
        return []
    ids = ", ".join(f"#{c.id}" for c in otros_casos)
    return [
        _pendiente(
            "DUPLICADO",
            "numero_titulo",
            f"Ya existe(n) trámite(s) abierto(s) para la misma nota: {ids}.",
            "Expediente(s) de los casos previos",
            "ENVIAR_A_CUMPLIMIENTO",
        )
    ]


def validar_riesgo(db: Session, cliente: models.Cliente) -> tuple[bool, str | None, list[dict]]:
    coincidencias = (
        db.query(models.ListaRiesgo)
        .filter(
            (models.ListaRiesgo.ruc_cedula == cliente.ruc_cedula)
            | (models.ListaRiesgo.nombre.ilike(f"%{cliente.razon_social}%"))
        )
        .all()
    )
    if not coincidencias:
        return False, None, []

    detalle = "; ".join(f"{c.nombre} ({c.motivo}, riesgo {c.nivel})" for c in coincidencias)
    pendientes = [
        _pendiente(
            "RIESGO",
            "lista_riesgo",
            f"Coincidencia en lista de riesgo/sanciones/PEP: {detalle}.",
            "Formulario de conocimiento del cliente y justificación del origen de fondos",
            "ENVIAR_A_CUMPLIMIENTO",
        )
    ]
    return True, detalle, pendientes


def priorizar(pendientes: list[dict]) -> list[dict]:
    return sorted(pendientes, key=lambda p: SIGUIENTE_ACCION_PRIORIDAD.index(p["siguiente_accion_sugerida"]))


def determinar_siguiente_accion(pendientes: list[dict]) -> str:
    if not pendientes:
        return "CONTINUAR"
    return priorizar(pendientes)[0]["siguiente_accion_sugerida"]


def validar_caso(db: Session, caso: models.Caso) -> dict:
    pendientes: list[dict] = []
    pendientes += validar_cliente(caso.cliente)
    pendientes += validar_titulo(caso.titulo, None)
    pendientes += validar_duplicados(db, caso.titulo, caso.id)

    hay_riesgo, detalle_riesgo, pendientes_riesgo = validar_riesgo(db, caso.cliente)
    pendientes += pendientes_riesgo

    pendientes = priorizar(pendientes)
    siguiente_accion = determinar_siguiente_accion(pendientes)

    ui = mensajes.mensaje_validacion(caso.titulo, pendientes, detalle_riesgo)

    if ui["estado_flujo"] == "PARCIALMENTE_NEGOCIADA" and ui["estadoNota"] == "APROBADO":
        siguiente_accion = "CONTINUAR"
        pendientes = [p for p in pendientes if p.get("tipo") != "ESTADO"]

    return {
        "pendientes": pendientes,
        "siguiente_accion_sugerida": siguiente_accion,
        "hay_coincidencia_riesgo": hay_riesgo,
        "detalle_riesgo": detalle_riesgo,
        "requiere_aprobacion_humana": True,
        "estado_flujo": ui["estado_flujo"],
        "estadoNota": ui["estadoNota"],
        "siguienteAccion": ui.get("siguienteAccion") or "",
        "mensaje_operador": ui["mensaje_operador"],
        "saldo_remanente": ui.get("saldo_remanente"),
        "valor_nominal": ui.get("valor_nominal"),
        "pregunta_monto": ui.get("pregunta_monto"),
        "pregunta_porcentaje": ui.get("pregunta_porcentaje"),
    }
