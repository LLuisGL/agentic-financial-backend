from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from db.database import (
    actualizar_analisis,
    crear_analisis,
    init_db,
    obtener_analisis,
)
from services.compliance import validar_cumplimiento
from services.gemini_extract import (
    configurar_gemini,
    descargar_pdf,
    extraer_datos_pdf,
)
from services.pricing import calcular_vneto

app = FastAPI(title="Agentic Scale - Notas de Crédito")
model = configurar_gemini()
init_db()


def _mensaje_confirmacion(datos: dict) -> str:
    ruc = datos.get("ruc") or "N/D"
    monto = datos.get("valor_nominal")
    monto_txt = f"${monto:,.2f}" if isinstance(monto, (int, float)) else "N/D"
    titular = datos.get("titular") or "N/D"
    numero = datos.get("numero_titulo") or "N/D"
    return (
        f"Datos extraídos de la nota: "
        f"RUC: {ruc}, Titular: {titular}, Título: {numero}, "
        f"Valor nominal: {monto_txt}. "
        "¿Confirmas estos datos para continuar el cumplimiento?"
    )


def _normalizar_payload_validar(data: dict) -> dict:
    """Unifica aliases del operador/Jelou hacia el contrato del equipo."""
    out = dict(data)
    if out.get("titular") is None and out.get("nombre_titular") is not None:
        out["titular"] = out["nombre_titular"]
    if out.get("estado") is None and out.get("estado_documento") is not None:
        out["estado"] = out["estado_documento"]
    return out


async def _extraer_impl(request: Request) -> JSONResponse:
    data = await request.json()
    print("PAYLOAD /extraer:", data, flush=True)

    file_url = data.get("url_pdf")
    if not file_url or "{{" in str(file_url):
        body = {
            "status": "error",
            "mensaje": "url_pdf vacío o variable $memory.url_pdf no resuelta en Jelou.",
            "payload_recibido": data,
        }
        print("RESPUESTA:", body, flush=True)
        return JSONResponse(content=body)

    try:
        pdf_bytes, content_type = descargar_pdf(file_url)
    except Exception as e:
        body = {
            "status": "error",
            "mensaje": f"No se pudo descargar el PDF: {e}",
            "url_pdf": file_url,
        }
        print("RESPUESTA:", body, flush=True)
        return JSONResponse(content=body)

    print(f"PDF descargado: {len(pdf_bytes)} bytes, content-type={content_type}", flush=True)

    if not pdf_bytes.startswith(b"%PDF"):
        body = {
            "status": "error",
            "mensaje": "La URL no devolvió un PDF válido.",
            "url_pdf": file_url,
            "content_type": content_type,
            "bytes_recibidos": len(pdf_bytes),
        }
        print("RESPUESTA:", body, flush=True)
        return JSONResponse(content=body)

    try:
        print("Enviando PDF inline a Gemini...", flush=True)
        datos, raw = extraer_datos_pdf(pdf_bytes, model)
        print("RESULTADO GEMINI:", raw, flush=True)

        analisis_id = crear_analisis(
            url_pdf=file_url,
            ruc=datos.get("ruc"),
            titular=datos.get("titular"),
            numero_titulo=datos.get("numero_titulo"),
            valor_nominal=datos.get("valor_nominal"),
            saldo_disponible=datos.get("saldo_disponible"),
            fecha_emision=datos.get("fecha_emision"),
            tipo_nota=datos.get("tipo_nota"),
            estado=datos.get("estado"),
        )

        body = {
            "status": "success",
            "mensaje": "Análisis finalizado correctamente.",
            "analisis_id": analisis_id,
            "datos": datos,
            # Contrato del equipo (Jelou / merge futuro)
            "ruc": datos.get("ruc"),
            "titular": datos.get("titular"),
            "numero_titulo": datos.get("numero_titulo"),
            "tipo_nota": datos.get("tipo_nota"),
            "valor_nominal": datos.get("valor_nominal"),
            "saldo_disponible": datos.get("saldo_disponible"),
            "estado": datos.get("estado"),
            # Extra agéntico
            "fecha_emision": datos.get("fecha_emision"),
            "mensaje_confirmacion": _mensaje_confirmacion(datos),
            "url_pdf": file_url,
            "accion_sugerida": (
                "Confirmar datos con el operador, luego POST /validar. "
                "Más adelante: antecedentes (clientes) y crear expediente (casos)."
            ),
        }
        print("RESPUESTA:", body, flush=True)
        return JSONResponse(content=body)
    except Exception as e:
        body = {
            "status": "error",
            "mensaje": f"Error al analizar el PDF con Gemini: {e}",
            "url_pdf": file_url,
        }
        print("RESPUESTA:", body, flush=True)
        return JSONResponse(content=body)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/extraer")
async def extraer(request: Request):
    return await _extraer_impl(request)


@app.post("/webhook")
async def webhook_alias(request: Request):
    """Alias de /extraer para no romper el nodo API actual de Jelou."""
    return await _extraer_impl(request)


@app.post("/validar")
async def validar(request: Request):
    data = _normalizar_payload_validar(await request.json())
    print("PAYLOAD /validar:", data, flush=True)

    analisis_id = data.get("analisis_id")
    campos_editables = (
        "ruc",
        "titular",
        "numero_titulo",
        "valor_nominal",
        "saldo_disponible",
        "fecha_emision",
        "tipo_nota",
        "estado",
    )

    if analisis_id:
        existente = obtener_analisis(analisis_id)
        if existente:
            for campo in campos_editables:
                if data.get(campo) is not None:
                    existente[campo] = data[campo]
            payload = {
                **existente,
                "nombre_confirmado": data.get("nombre_confirmado", False),
            }
        else:
            payload = data
    else:
        payload = data

    resultado = validar_cumplimiento(payload)

    if analisis_id:
        actualizar_analisis(
            analisis_id,
            ruc=payload.get("ruc"),
            titular=payload.get("titular"),
            numero_titulo=payload.get("numero_titulo"),
            valor_nominal=payload.get("valor_nominal"),
            saldo_disponible=payload.get("saldo_disponible"),
            fecha_emision=payload.get("fecha_emision"),
            tipo_nota=payload.get("tipo_nota"),
            estado=payload.get("estado"),
            estado_riesgo=resultado["estado_riesgo"],
            observaciones_json=resultado["observaciones"],
        )
        resultado["analisis_id"] = analisis_id

    print("RESPUESTA /validar:", resultado, flush=True)
    return JSONResponse(content=resultado)


@app.post("/calcular")
async def calcular(request: Request):
    data = await request.json()
    print("PAYLOAD /calcular:", data, flush=True)

    analisis_id = data.get("analisis_id")
    valor_nominal = data.get("valor_nominal")
    if valor_nominal is None:
        valor_nominal = data.get("saldo_disponible")
    porcentaje = data.get("porcentaje_propuesta", 96)

    if valor_nominal is None and analisis_id:
        analisis = obtener_analisis(analisis_id)
        if analisis:
            valor_nominal = analisis.get("saldo_disponible") or analisis.get("valor_nominal")

    try:
        pricing = calcular_vneto(valor_nominal, porcentaje)
    except Exception as e:
        body = {"status": "error", "mensaje": str(e)}
        print("RESPUESTA /calcular:", body, flush=True)
        return JSONResponse(content=body)

    if analisis_id:
        actualizar_analisis(
            analisis_id,
            vneto=pricing["vneto"],
            porcentaje=pricing["porcentaje_propuesta"],
            valor_nominal=pricing["valor_nominal"],
        )
        pricing["analisis_id"] = analisis_id

    body = {"status": "success", **pricing}
    print("RESPUESTA /calcular:", body, flush=True)
    return JSONResponse(content=body)


@app.post("/auditoria")
async def auditoria(request: Request):
    data = await request.json()
    print("PAYLOAD /auditoria:", data, flush=True)

    analisis_id = data.get("analisis_id")
    guardar = bool(data.get("guardar", True))
    operador_id = data.get("operador_id")

    if not analisis_id:
        body = {
            "status": "error",
            "mensaje": "analisis_id es requerido para auditoría.",
        }
        return JSONResponse(content=body)

    analisis = obtener_analisis(analisis_id)
    if not analisis:
        body = {
            "status": "error",
            "mensaje": f"No existe análisis {analisis_id}",
        }
        return JSONResponse(content=body)

    if guardar:
        actualizar_analisis(
            analisis_id,
            expediente_guardado=1,
            operador_id=operador_id,
        )
        analisis = obtener_analisis(analisis_id)
        mensaje = (
            "Análisis guardado en el expediente del trámite. "
            f"RUC {analisis.get('ruc')}, Vneto {analisis.get('vneto')}, "
            f"riesgo {analisis.get('estado_riesgo')}."
        )
    else:
        mensaje = "No se guardó el análisis en el expediente."

    body = {
        "status": "success",
        "analisis_id": analisis_id,
        "expediente_guardado": bool(guardar),
        "mensaje": mensaje,
        "resumen": {
            "ruc": analisis.get("ruc"),
            "titular": analisis.get("titular"),
            "numero_titulo": analisis.get("numero_titulo"),
            "valor_nominal": analisis.get("valor_nominal"),
            "saldo_disponible": analisis.get("saldo_disponible"),
            "vneto": analisis.get("vneto"),
            "estado_riesgo": analisis.get("estado_riesgo"),
            "tipo_nota": analisis.get("tipo_nota"),
            "estado": analisis.get("estado"),
        },
    }
    print("RESPUESTA /auditoria:", body, flush=True)
    return JSONResponse(content=body)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
