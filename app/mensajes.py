"""Mensajes WhatsApp para el operador (reglas de flujo y estética).

Reglas:
1) Extracción: empieza con "Los datos extraídos del PDF son:" y cierra con confirmación.
2) Parcialmente negociada: informar saldo remanente y pasar a negociación (no es error).
3) Sin endpoints crudos; saldo 0 → texto natural de nota consumida.
4) Propuesta como ticket "Propuesta Inteligente de Negociación".
5) Guardrail de seguridad con texto exacto.
"""

from __future__ import annotations

from typing import Any

GUARDRAIL_CIERRE = (
    "🔒 Guardia de Seguridad: Esta propuesta es preparatoria. "
    "El sistema no ejecuta liquidaciones ni endosos automáticamente. "
    "¿Aprueba esta propuesta para registrar el cierre de la operación?"
)

PREGUNTA_CONFIRMACION_EXTRACCION = "¿Confirma que la información leída es correcta para continuar?"

PREGUNTA_MONTO_PARCIAL = (
    "¿Cuánto de este saldo disponible desea retirar/negociar? "
    "(Puede indicar el monto total o una cantidad específica)"
)

PREGUNTA_PORCENTAJE = "¿A qué porcentaje de precio referencial se realizará la negociación?"

NOTA_TIPO_VACIO = (
    "⚠️ Nota: El 'Tipo' de documento no se pudo identificar. "
    "Verifique si es legible en el PDF o si el backend omitió el registro."
)


def _fmt_money(valor: Any) -> str:
    try:
        if valor is None or valor == "":
            return "No detectado"
        return f"${float(valor):,.2f}"
    except (TypeError, ValueError):
        return str(valor)


def _fmt_pct(valor: Any) -> str:
    try:
        if valor is None or valor == "":
            return "—"
        return f"{float(valor):.2f}%"
    except (TypeError, ValueError):
        return str(valor)


def _saldo_legible(saldo: Any, valor_nominal: Any = None) -> str:
    try:
        s = float(saldo) if saldo is not None and saldo != "" else None
    except (TypeError, ValueError):
        s = None
    if s is None:
        return "No detectado"
    if s <= 0:
        return "Saldo remanente: $0.00 (Nota consumida en su totalidad)"
    return f"Saldo remanente: {_fmt_money(s)}"


def mensaje_extraccion(datos: dict) -> str:
    """REGLA 1: primer mensaje tras extracción del PDF."""
    ruc = datos.get("ruc") or "No detectado"
    titular = datos.get("titular") or "No detectado"
    numero = datos.get("numero_titulo") or datos.get("codigo_nota") or "No detectado"
    tipo = datos.get("tipo_nota") or datos.get("tipo")
    valor = datos.get("valor_nominal")
    saldo = datos.get("saldo_disponible")
    if saldo is None:
        saldo = valor
    fecha = datos.get("fecha_emision") or "No detectada"
    estado = datos.get("estado") or "No detectado"

    lineas = [
        "Los datos extraídos del PDF son:",
        "",
        f"• RUC / Identificación: {ruc}",
        f"• Titular: {titular}",
        f"• Número / código de la nota: {numero}",
        f"• Tipo: {tipo or 'No identificado'}",
        f"• Valor nominal: {_fmt_money(valor)}",
        f"• {_saldo_legible(saldo, valor)}",
        f"• Fecha de emisión: {fecha}",
        f"• Estado del documento: {estado}",
    ]
    if not tipo:
        lineas.extend(["", NOTA_TIPO_VACIO])
    lineas.extend(["", PREGUNTA_CONFIRMACION_EXTRACCION])
    return "\n".join(lineas)


def clasificar_estado_negociacion(titulo) -> str:
    """Normaliza el estado de negocio para el flujo WhatsApp."""
    if titulo is None:
        return "NO_ENCONTRADA"
    if getattr(titulo, "bloqueado", False) or str(getattr(titulo, "estado", "")).upper() in ("BLOQUEADA", "BLOQUEADO"):
        return "BLOQUEADA"
    estado = str(getattr(titulo, "estado", "") or "").upper()
    if estado in ("CADUCADA", "ANULADA"):
        return "CADUCADA" if estado == "CADUCADA" else "ANULADA"
    try:
        saldo = float(titulo.saldo_disponible)
        nominal = float(titulo.valor_nominal)
    except (TypeError, ValueError):
        return "DISPONIBLE"
    if saldo <= 0 or estado in ("USADA", "TOTALMENTE_NEGOCIADA", "TOTALMENTE NEGOCIADA"):
        return "TOTALMENTE_NEGOCIADA"
    if saldo < nominal or estado in ("PARCIALMENTE_NEGOCIADA", "PARCIALMENTE NEGOCIADA", "PARCIAL"):
        return "PARCIALMENTE_NEGOCIADA"
    return "DISPONIBLE"


def mensaje_validacion(titulo, pendientes: list[dict] | None = None, detalle_riesgo: str | None = None) -> dict:
    """REGLA 2 y 3: mensajes de validación en lenguaje natural."""
    pendientes = pendientes or []
    estado_flujo = clasificar_estado_negociacion(titulo)

    if estado_flujo == "PARCIALMENTE_NEGOCIADA":
        saldo = getattr(titulo, "saldo_disponible", None)
        texto = (
            "La nota ya tiene negociaciones previas (Parcialmente Negociada).\n"
            f"{_saldo_legible(saldo)}\n\n"
            f"{PREGUNTA_MONTO_PARCIAL}"
        )
        return {
            "estado_flujo": estado_flujo,
            "estadoNota": "APROBADO",
            "siguienteAccion": "negociar_parcial",
            "mensaje_operador": texto,
            "saldo_remanente": saldo,
            "pregunta_porcentaje": PREGUNTA_PORCENTAJE,
        }

    if estado_flujo == "TOTALMENTE_NEGOCIADA":
        texto = (
            "Esta nota ya fue negociada al 100%.\n"
            "Saldo remanente: $0.00 (Nota consumida en su totalidad).\n"
            "No hay monto disponible para una nueva negociación."
        )
        return {
            "estado_flujo": estado_flujo,
            "estadoNota": "RECHAZADO",
            "siguienteAccion": "",
            "mensaje_operador": texto,
            "saldo_remanente": 0,
        }

    if estado_flujo == "BLOQUEADA":
        motivo = "La nota está bloqueada y no puede negociarse en este momento."
        texto = f"{motivo}\nPor favor derive el caso a cumplimiento o operaciones."
        return {
            "estado_flujo": estado_flujo,
            "estadoNota": "RECHAZADO",
            "siguienteAccion": "",
            "mensaje_operador": texto,
        }

    if not pendientes:
        saldo = getattr(titulo, "saldo_disponible", None) if titulo else None
        texto = (
            "Validación completada. La nota está disponible para negociar.\n"
            f"{_saldo_legible(saldo)}\n\n"
            f"{PREGUNTA_MONTO_PARCIAL}"
        )
        return {
            "estado_flujo": "DISPONIBLE",
            "estadoNota": "APROBADO",
            "siguienteAccion": "negociar",
            "mensaje_operador": texto,
            "saldo_remanente": saldo,
            "pregunta_porcentaje": PREGUNTA_PORCENTAJE,
        }

    # Pendientes en lenguaje natural (sin endpoints)
    bullets = []
    for p in pendientes:
        bullets.append(f"• {p.get('mensaje', 'Pendiente por revisar')}")
    if detalle_riesgo:
        bullets.append(f"• Coincidencia de riesgo detectada: {detalle_riesgo}")

    texto = (
        "Se detectaron observaciones que requieren su revisión antes de continuar:\n"
        + "\n".join(bullets)
        + "\n\n¿Desea corregir los datos o enviar el caso a cumplimiento?"
    )
    return {
        "estado_flujo": estado_flujo,
        "estadoNota": "PENDIENTE",
        "siguienteAccion": "completar_datos",
        "mensaje_operador": texto,
    }


def mensaje_propuesta_ticket(
    *,
    negociacion: dict | Any,
    titular: str | None = None,
    ruc: str | None = None,
    codigo_nota: str | None = None,
    recomendacion: dict | None = None,
) -> str:
    """REGLA 4 + 5: ticket de propuesta + guardrail exacto."""
    get = negociacion.get if isinstance(negociacion, dict) else lambda k, d=None: getattr(negociacion, k, d)

    saldo_txt = _saldo_legible(get("saldo_remanente_post"), get("valor_nominal"))
    # Si no hay saldo post, no inventamos; solo mostramos monto negociado.
    lineas = [
        "📊 Propuesta Inteligente de Negociación",
        "────────────────────────────",
        f"Titular: {titular or '—'}",
        f"RUC: {ruc or '—'}",
        f"Nota: {codigo_nota or '—'}",
        "",
        f"Monto a negociar: {_fmt_money(get('valor_nominal'))}",
        f"Precio referencial: {_fmt_pct(get('precio_negociacion_pct'))}",
        f"Valor efectivo (VE): {_fmt_money(get('valor_efectivo'))}",
        f"Descuento: {_fmt_money(get('descuento'))}",
        f"Comisión bolsa (0.09%): {_fmt_money(get('comision_bolsa'))}",
        f"Comisión casa (0.5%): {_fmt_money(get('comision_casa'))}",
        f"Otros costos: {_fmt_money(get('otros_costos'))}",
        "",
        f"💵 VALOR NETO ESTIMADO: {_fmt_money(get('valor_neto'))}",
        "────────────────────────────",
    ]
    if recomendacion:
        lineas.insert(
            5,
            f"Mediana de mercado: {_fmt_pct(recomendacion.get('mediana'))} | "
            f"Sugerido IA: {_fmt_pct(recomendacion.get('porcentaje_recomendado'))}",
        )
        if recomendacion.get("justificacion"):
            lineas.insert(6, f"Criterio: {recomendacion['justificacion']}")

    # Remanente solo si viene informado
    if get("saldo_remanente_post") is not None:
        lineas.append(saldo_txt)

    lineas.extend(["", GUARDRAIL_CIERRE])
    return "\n".join(lineas)


def mensaje_expediente(caso: dict) -> str:
    """REGLA 3: expediente en lenguaje natural, sin rutas/endpoints."""
    cliente = caso.get("cliente") or {}
    titulo = caso.get("titulo") or {}
    negs = caso.get("negociaciones") or []
    last = negs[-1] if negs else None

    saldo = titulo.get("saldo_disponible")
    estado = caso.get("estado") or "—"
    proxima = caso.get("proxima_accion") or "Sin acción pendiente"
    # Sanitizar posibles restos técnicos
    for token in ("POST /", "GET /", "/casos", "/negociacion", "/cierre", "/validar", "/webhook"):
        if token.lower() in str(proxima).lower():
            proxima = "Revisión y aprobación humana pendiente"
            break

    lineas = [
        "📁 Expediente del trámite",
        "────────────────────────────",
        f"Expediente N.º: {caso.get('id')}",
        f"Estado: {estado}",
        f"Próximo paso: {proxima}",
        f"Responsable: {caso.get('operador') or '—'}",
        "",
        f"Titular: {cliente.get('razon_social') or '—'}",
        f"RUC: {cliente.get('ruc_cedula') or '—'}",
        f"Nota: {titulo.get('numero_titulo') or '—'}",
        f"{_saldo_legible(saldo, titulo.get('valor_nominal'))}",
    ]
    if last:
        lineas.extend(
            [
                "",
                f"Última propuesta: {_fmt_money(last.get('valor_neto'))} neto "
                f"a {_fmt_pct(last.get('precio_negociacion_pct'))} "
                f"(estado: {last.get('estado')})",
            ]
        )
    lineas.extend(
        [
            "",
            "La liquidación y el endoso requieren aprobación humana explícita.",
        ]
    )
    return "\n".join(lineas)
