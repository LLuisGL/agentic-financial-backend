from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import google.generativeai as genai
import json
import re
import os
import uuid
from urllib.request import Request as UrlRequest, urlopen

from dotenv import load_dotenv

from app.database import get_db, init_db
from app.routers import casos, clientes, legacy
from app.seed_data import seed_if_empty
from app import mensajes

load_dotenv()

app = FastAPI()

app.include_router(clientes.router)
app.include_router(casos.router)
app.include_router(legacy.router)


@app.on_event("startup")
def on_startup():
    init_db()
    db = next(get_db())
    try:
        # Asegura títulos/clientes de los PDFs de prueba en cada arranque.
        seed_if_empty(db)
    finally:
        db.close()


# Usa una API key válida de https://aistudio.google.com/apikey
genai.configure(api_key=os.getenv("GENAI_APIKEY"))
model = genai.GenerativeModel("models/gemini-3.5-flash")

PROMPT_NOTA_CREDITO = """
Eres un extractor de datos de notas de crédito tributarias (Ecuador / Latinoamérica).

Analiza el PDF adjunto y extrae SOLO estos campos:
- ruc: número de RUC o cédula del titular (solo dígitos, sin guiones ni espacios).
- titular: nombre o razón social del titular de la nota.
- numero_titulo: número/código del título o de la nota de crédito, si aparece (ej. ISD-2019-000011).
- tipo_nota: tipo de nota si se puede inferir (NCD = Nota de Crédito Desmaterializada, ISD, NCE = Nota de Crédito de Excepción). Si no es claro, usa null.
- valor_nominal: monto principal / valor nominal / total de la nota (número decimal, sin símbolo de moneda ni separadores de miles; usa punto como decimal).
- saldo_disponible: saldo disponible de la nota si aparece explícito; si no, usa el mismo valor_nominal.
- fecha_emision: fecha real de emisión del documento en formato AAAA-MM-DD. NO uses el año del código de la nota (ej. en "ISD-2019-000011" el 2019 NO es automáticamente la fecha de emisión). Busca la fecha impresa en el PDF. Si no la encuentras con certeza, usa null.
- estado: estado del documento si aparece (ej. ACTIVO, ANULADO, PAGADO, PENDIENTE, VIGENTE). Si no hay estado explícito, usa null.

Reglas:
1. Responde ÚNICAMENTE con un JSON válido, sin markdown ni texto extra.
2. Si un campo no se puede leer con certeza, usa null.
3. No inventes datos.
4. Nunca confundas el año del código de la nota con la fecha de emisión.

Formato exacto:
{
  "ruc": "1790000000001",
  "titular": "Comercial Andina S.A.",
  "numero_titulo": "NCD-2024-000123",
  "tipo_nota": "NCD",
  "valor_nominal": 1500.50,
  "saldo_disponible": 1500.50,
  "fecha_emision": "2019-04-15",
  "estado": "ACTIVO"
}
"""


def descargar_pdf(url: str) -> tuple[bytes, str | None]:
    req = UrlRequest(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp:
        return resp.read(), resp.headers.get("Content-Type")


def parsear_json_gemini(texto: str) -> dict:
    """Extrae JSON aunque Gemini lo envuelva en ```json ... ```."""
    texto = (texto or "").strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", texto)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {
        "ruc": None,
        "titular": None,
        "numero_titulo": None,
        "tipo_nota": None,
        "valor_nominal": None,
        "saldo_disponible": None,
        "fecha_emision": None,
        "estado": None,
        "raw": texto,
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/formatear/datos")
async def formatear_datos_corregidos(request: Request):
    """REGLA 3: reimprime la lista completa tras una corrección en vivo del operador."""
    data = await request.json()
    datos = data.get("datos") if isinstance(data.get("datos"), dict) else data
    return {
        "status": "success",
        "mensaje_confirmacion": mensajes.mensaje_datos_actualizados(datos),
        "datos": datos,
        "pregunta_confirmacion": mensajes.PREGUNTA_CONFIRMACION_EXTRACCION,
    }


@app.post("/webhook")
async def procesar_nota(request: Request):
    data = await request.json()
    print("PAYLOAD:", data, flush=True)

    file_url = data.get("url_pdf")

    if not file_url or "{{" in str(file_url):
        body = {
            "status": "error",
            "mensaje": "url_pdf vacío o variable $memory.url_pdf no resuelta en Jelou.",
            "payload_recibido": data,
        }
        print("RESPUESTA A JELOU:", body, flush=True)
        return JSONResponse(content=body)

    try:
        pdf_bytes, content_type = descargar_pdf(file_url)
    except Exception as e:
        body = {
            "status": "error",
            "mensaje": f"No se pudo descargar el PDF: {e}",
            "url_pdf": file_url,
        }
        print("RESPUESTA A JELOU:", body, flush=True)
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
        print("RESPUESTA A JELOU:", body, flush=True)
        return JSONResponse(content=body)

    try:
        print("Enviando PDF inline a Gemini...", flush=True)
        response = model.generate_content(
            [
                {"mime_type": "application/pdf", "data": pdf_bytes},
                PROMPT_NOTA_CREDITO,
            ]
        )

        try:
            resultado_texto = response.text
        except Exception:
            resultado_texto = str(response)

        print("RESULTADO GEMINI:", resultado_texto, flush=True)
        datos = parsear_json_gemini(resultado_texto)
        mensaje_confirmacion = mensajes.mensaje_extraccion(datos)

        analisis_id = str(uuid.uuid4())
        body = {
            "status": "success",
            "mensaje": "Análisis finalizado correctamente.",
            "analisis_id": analisis_id,
            "mensaje_confirmacion": mensaje_confirmacion,
            "datos": datos,
            "ruc": datos.get("ruc"),
            "titular": datos.get("titular"),
            "numero_titulo": datos.get("numero_titulo"),
            "tipo_nota": datos.get("tipo_nota"),
            "valor_nominal": datos.get("valor_nominal"),
            "saldo_disponible": datos.get("saldo_disponible"),
            "fecha_emision": datos.get("fecha_emision"),
            "estado": datos.get("estado"),
            "url_pdf": file_url,
            "accion_sugerida": "Revisar los datos con el operador y confirmar para crear el expediente.",
            "pregunta_confirmacion": mensajes.PREGUNTA_CONFIRMACION_EXTRACCION,
        }
        print("RESPUESTA A JELOU:", body, flush=True)
        return JSONResponse(content=body)

    except Exception as e:
        body = {
            "status": "error",
            "mensaje": f"Error al analizar el PDF con Gemini: {e}",
            "url_pdf": file_url,
        }
        print("RESPUESTA A JELOU:", body, flush=True)
        return JSONResponse(content=body)


# Alias v1: las skills históricas llaman /extraer
app.add_api_route("/extraer", procesar_nota, methods=["POST"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
