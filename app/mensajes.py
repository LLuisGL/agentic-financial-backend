"""Mensajes WhatsApp para el operador (reglas de flujo y estética).

Reglas:
1) Extracción: "Los datos extraídos del PDF son:" + confirmación obligatoria.
2) Corrección en vivo: reimprimir lista completa tras actualizar memoria.
3) Parcialmente negociada: VN + saldo remanente + pregunta de monto (no es error).
4) Nunca asumir % (ni 96% ni otro); preguntar el precio referencial.
5) Propuesta como ticket + saldo 0 en lenguaje natural (sin endpoints).
6) Guardrail de seguridad con texto exacto (DECEVALE).
7) Continuidad: nunca cerrar el chat tras registrar el expediente.
"""

from __future__ import annotations

from typing import Any

from app.negociacion import COMISION_BOLSA_PCT, COMISION_CASA_PCT

GUARDRAIL_CIERRE = (
    "🔒 Guardia de Seguridad: Esta propuesta es preparatoria. "
    "El sistema no ejecuta liquidaciones, transferencias ni endosos automáticamente en DECEVALE. "
    "¿Aprueba esta propuesta para registrar el cierre de la operación en el expediente?"
)

PREGUNTA_CONFIRMACION_EXTRACCION = "¿Confirma que la información leída es correcta para continuar?"

PREGUNTA_MONTO_PARCIAL = (
    "¿Cuánto de este saldo disponible desea retirar/negociar hoy? "
    "(Indique el monto total o una cantidad específica)"
)

PREGUNTA_PORCENTAJE = "¿A qué porcentaje de precio referencial se realizará la negociación?"

NOTA_TIPO_VACIO = (
    "⚠️ Nota: El 'Tipo' de documento no se pudo identificar. "
    "Verifique si es legible en el PDF original."
)

MENSAJE_CONTINUIDAD = (
    "✅ Operación registrada con éxito y expediente guardado. "
    "¿Desea ingresar y procesar una nueva nota de crédito?"
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


def _fmt_fecha(valor: Any) -> str:
    if valor is None or valor == "":
        return "No detectada"
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    texto = str(valor).strip()
    return texto or "No detectada"


def _saldo_legible(saldo: Any, valor_nominal: Any = None) -> str:
    try:
        s = float(saldo) if saldo is not None and saldo != "" else None
    except (TypeError, ValueError):
        s = None
    if s is None:
        return "Saldo remanente: No detectado"
    if s <= 0:
        return "Saldo remanente: $0.00 (Nota consumida en su totalidad)"
    return f"Saldo remanente: {_fmt_money(s)}"


def _pct_casa_etiqueta() -> str:
    return f"{COMISION_CASA_PCT * 100:.2f}".rstrip("0").rstrip(".") + "%"


def _pct_bvq_etiqueta() -> str:
    return f"{COMISION_BOLSA_PCT * 100:.2f}".rstrip("0").rstrip(".") + "%"


def lista_datos_extraidos(datos: dict) -> list[str]:
    """Lista canónica de campos del primer mensaje / corrección en vivo."""
    ruc = datos.get("ruc") or "No detectado"
    titular = datos.get("titular") or "No detectado"
    numero = datos.get("numero_titulo") or datos.get("codigo_nota") or "No detectado"
    tipo = datos.get("tipo_nota") or datos.get("tipo")
    valor = datos.get("valor_nominal")
    saldo = datos.get("saldo_disponible")
    if saldo is None:
        saldo = valor
    fecha = _fmt_fecha(datos.get("fecha_emision"))

    lineas = [
        f"• RUC: {ruc}",
        f"• Titular: {titular}",
        f"• Código de nota: {numero}",
        f"• Tipo: {tipo or 'No identificado'}",
        f"• Valor nominal: {_fmt_money(valor)}",
        f"• {_saldo_legible(saldo, valor)}",
        f"• Fecha de emisión: {fecha}",
    ]
    if not tipo:
        lineas.extend(["", NOTA_TIPO_VACIO])
    return lineas


def mensaje_extraccion(datos: dict) -> str:
    """REGLA 2: primer mensaje tras extracción del PDF."""
    lineas = ["Los datos extraídos del PDF son:", ""]
    lineas.extend(lista_datos_extraidos(datos))
    lineas.extend(["", PREGUNTA_CONFIRMACION_EXTRACCION])
    return "\n".join(lineas)


def mensaje_datos_actualizados(datos: dict) -> str:
    """REGLA 3: corrección en vivo — reimprime la lista completa y pide confirmación."""
    lineas = ["He actualizado el registro. Los datos actuales son:", ""]
    lineas.extend(lista_datos_extraidos(datos))
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
    """REGLA 4: validación en lenguaje natural (parcial no es error)."""
    pendientes = pendientes or []
    estado_flujo = clasificar_estado_negociacion(titulo)

    if estado_flujo == "PARCIALMENTE_NEGOCIADA":
        saldo = getattr(titulo, "saldo_disponible", None)
        valor_nominal = getattr(titulo, "valor_nominal", None)
        texto = (
            "La nota ya tiene negociaciones previas (Parcialmente Negociada).\n"
            f"Valor nominal original: {_fmt_money(valor_nominal)}\n"
            f"{_saldo_legible(saldo)}\n\n"
            f"{PREGUNTA_MONTO_PARCIAL}"
        )
        return {
            "estado_flujo": estado_flujo,
            "estadoNota": "APROBADO",
            "siguienteAccion": "negociar_parcial",
            "mensaje_operador": texto,
            "saldo_remanente": saldo,
            "valor_nominal": valor_nominal,
            "pregunta_monto": PREGUNTA_MONTO_PARCIAL,
            "pregunta_porcentaje": PREGUNTA_PORCENTAJE,
        }

    if estado_flujo == "TOTALMENTE_NEGOCIADA":
        texto = (
            "Esta nota ya fue negociada al 100%.\n"
            "Saldo remanente: $0.00 (Nota consumida en su totalidad).\n"
            "No hay monto disponible para una nueva negociación.\n\n"
            f"{MENSAJE_CONTINUIDAD}"
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
        valor_nominal = getattr(titulo, "valor_nominal", None) if titulo else None
        texto = (
            "Validación completada. La nota está disponible para negociar.\n"
            f"Valor nominal: {_fmt_money(valor_nominal)}\n"
            f"{_saldo_legible(saldo)}\n\n"
            f"{PREGUNTA_MONTO_PARCIAL}"
        )
        return {
            "estado_flujo": "DISPONIBLE",
            "estadoNota": "APROBADO",
            "siguienteAccion": "negociar",
            "mensaje_operador": texto,
            "saldo_remanente": saldo,
            "valor_nominal": valor_nominal,
            "pregunta_monto": PREGUNTA_MONTO_PARCIAL,
            "pregunta_porcentaje": PREGUNTA_PORCENTAJE,
        }

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
    """REGLA 6 + 7: ticket de propuesta + guardrail exacto."""
    get = negociacion.get if isinstance(negociacion, dict) else lambda k, d=None: getattr(negociacion, k, d)

    lineas = [
        "📊 PROPUESTA INTELIGENTE DE NEGOCIACIÓN",
        "────────────────────────────",
        f"Titular: {titular or '—'}",
        f"RUC: {ruc or '—'}",
        f"Nota: {codigo_nota or '—'}",
        "",
        f"Monto a negociar: {_fmt_money(get('valor_nominal'))}",
        f"Precio referencial: {_fmt_pct(get('precio_negociacion_pct'))}",
        f"Valor Efectivo: {_fmt_money(get('valor_efectivo'))}",
        f"Comisión BVQ ({_pct_bvq_etiqueta()}): {_fmt_money(get('comision_bolsa'))}",
        f"Comisión Casa de Valores ({_pct_casa_etiqueta()}): {_fmt_money(get('comision_casa'))}",
        f"Valor Neto al Vendedor: {_fmt_money(get('valor_neto'))}",
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

    if get("saldo_remanente_post") is not None:
        lineas.append(_saldo_legible(get("saldo_remanente_post"), get("valor_nominal")))

    lineas.extend(["", GUARDRAIL_CIERRE])
    return "\n".join(lineas)


def mensaje_expediente(caso: dict) -> str:
    """Expediente en lenguaje natural, sin rutas/endpoints."""
    cliente = caso.get("cliente") or {}
    titulo = caso.get("titulo") or {}
    negs = caso.get("negociaciones") or []
    last = negs[-1] if negs else None

    saldo = titulo.get("saldo_disponible")
    estado = caso.get("estado") or "—"
    proxima = caso.get("proxima_accion") or "Sin acción pendiente"
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
            "La liquidación, transferencia y el endoso requieren aprobación humana explícita.",
        ]
    )
    return "\n".join(lineas)


def mensaje_cierre_registrado() -> str:
    """REGLA 8: nunca cerrar el chat; ofrecer nueva nota."""
    return MENSAJE_CONTINUIDAD
