from datetime import date, datetime
from typing import Any

from db.database import buscar_cliente_por_ruc


def _parse_fecha(fecha: str | None) -> date | None:
    if not fecha:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(fecha).strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def _norm(texto: str | None) -> str:
    if not texto:
        return ""
    return " ".join(texto.upper().strip().split())


def _titular(payload: dict[str, Any]) -> str | None:
    return payload.get("titular") or payload.get("nombre_titular")


def _estado(payload: dict[str, Any]) -> str | None:
    raw = payload.get("estado") or payload.get("estado_documento")
    return (raw or "").upper().strip() or None


def validar_cumplimiento(payload: dict[str, Any]) -> dict[str, Any]:
    """Aplica reglas de negocio. Gemini no decide el riesgo final."""
    observaciones: list[dict[str, str]] = []
    tipo_nota = (payload.get("tipo_nota") or "").upper().strip() or None
    estado_doc = _estado(payload)
    titular = _titular(payload)
    nombre_confirmado = bool(payload.get("nombre_confirmado", False))

    campos_criticos = {
        "ruc": payload.get("ruc"),
        "valor_nominal": payload.get("valor_nominal"),
        "fecha_emision": payload.get("fecha_emision"),
        "titular": titular,
    }
    faltantes = [k for k, v in campos_criticos.items() if v is None or v == ""]
    if faltantes:
        observaciones.append(
            {
                "codigo": "DATOS_INCOMPLETOS",
                "severidad": "media",
                "texto": f"Faltan o son ilegibles: {', '.join(faltantes)}",
            }
        )

    if estado_doc in {"EMBARGADO", "BLOQUEADO", "ANULADO"}:
        observaciones.append(
            {
                "codigo": "DOCUMENTO_BLOQUEADO",
                "severidad": "alta",
                "texto": f"El documento aparece como {estado_doc}",
            }
        )

    fecha_emision = _parse_fecha(payload.get("fecha_emision"))
    if tipo_nota == "ISD":
        if fecha_emision is None:
            observaciones.append(
                {
                    "codigo": "ISD_SIN_FECHA",
                    "severidad": "media",
                    "texto": (
                        "Nota ISD sin fecha de emisión legible; "
                        "no se pudo verificar vigencia de 4 años"
                    ),
                }
            )
        else:
            hoy = date.today()
            try:
                limite = fecha_emision.replace(year=fecha_emision.year + 4)
            except ValueError:
                limite = fecha_emision.replace(year=fecha_emision.year + 4, day=28)
            if hoy > limite:
                observaciones.append(
                    {
                        "codigo": "ISD_CADUCADO",
                        "severidad": "alta",
                        "texto": "La nota excede el plazo de vigencia de 4 años para ISD",
                    }
                )
            else:
                observaciones.append(
                    {
                        "codigo": "ISD_VIGENCIA_OK",
                        "severidad": "info",
                        "texto": (
                            "Esta nota es de tipo ISD; vigila la caducidad "
                            "(plazo máximo 4 años)"
                        ),
                    }
                )

    cliente = buscar_cliente_por_ruc(payload.get("ruc"))
    titular_pdf = _norm(titular)
    requiere_confirmacion_titular = False
    if cliente:
        titular_db = _norm(cliente.get("nombre"))
        if titular_pdf and titular_db and titular_pdf != titular_db and not nombre_confirmado:
            requiere_confirmacion_titular = True
            observaciones.append(
                {
                    "codigo": "TITULARIDAD_DIFIERE",
                    "severidad": "media",
                    "texto": (
                        f"He detectado el nombre {titular} en la nota, "
                        f"pero en base interna el RUC corresponde a {cliente.get('nombre')}. "
                        "¿Confirmas que es el cliente correcto para este trámite?"
                    ),
                }
            )
    elif payload.get("ruc"):
        observaciones.append(
            {
                "codigo": "RUC_NO_REGISTRADO",
                "severidad": "media",
                "texto": f"El RUC {payload.get('ruc')} no está en la base interna de clientes",
            }
        )
        if not nombre_confirmado:
            requiere_confirmacion_titular = True

    altas = [o for o in observaciones if o["severidad"] == "alta"]
    medias = [o for o in observaciones if o["severidad"] == "media"]

    if altas:
        estado_riesgo = "RECHAZADO"
        es_valido = False
        siguiente_accion = "rechazar"
        motivos = "; ".join(o["texto"] for o in altas)
        mensaje_operador = (
            f"No se puede continuar el trámite por: {motivos}. "
            "Recomienda al área revisar con el emisor o legal "
            "si el bloqueo/embargo fue levantado o si hay una nota vigente."
        )
    elif requiere_confirmacion_titular:
        estado_riesgo = "PENDIENTE"
        es_valido = False
        siguiente_accion = "confirmar_titular"
        mensaje_operador = next(
            (o["texto"] for o in observaciones if o["codigo"] == "TITULARIDAD_DIFIERE"),
            f"He detectado el nombre {titular} en la nota. "
            "¿Confirmas la titularidad para este trámite?",
        )
    elif faltantes or medias:
        estado_riesgo = "PENDIENTE"
        es_valido = False
        siguiente_accion = "completar_datos"
        mensaje_operador = (
            "La nota requiere revisión adicional antes de continuar: "
            + "; ".join(o["texto"] for o in medias)
        )
    else:
        estado_riesgo = "APROBADO"
        es_valido = True
        siguiente_accion = "continuar"
        mensaje_operador = (
            "Cumplimiento OK. Datos completos y sin bloqueos detectados. "
            "Puedes continuar con el cálculo de la propuesta."
        )

    return {
        "status": "success",
        "es_valido": es_valido,
        "estado_riesgo": estado_riesgo,
        "observaciones": observaciones,
        "mensaje_operador": mensaje_operador,
        "siguiente_accion": siguiente_accion,
        "requiere_confirmacion_titular": requiere_confirmacion_titular,
        "cliente_interno": cliente,
        "tipo_nota": tipo_nota,
    }
