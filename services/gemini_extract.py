import json
import os
import re
from urllib.request import Request as UrlRequest, urlopen

import google.generativeai as genai

# Contrato unificado: campos del equipo + fecha_emision (necesaria para ISD)
PROMPT_NOTA_CREDITO = """
Eres un extractor de datos de notas de crédito tributarias (Ecuador / Latinoamérica).

Analiza el PDF adjunto y extrae SOLO estos campos:
- ruc: número de RUC o cédula del titular (solo dígitos, sin guiones ni espacios).
- titular: nombre o razón social del titular de la nota.
- numero_titulo: número del título o de la nota de crédito, si aparece.
- tipo_nota: tipo de nota si se puede inferir (NCD = Nota de Crédito Desmaterializada, ISD, NCE = Nota de Crédito de Excepción). Si no es claro, usa null.
- valor_nominal: monto principal / valor nominal / total de la nota (número decimal, sin símbolo de moneda ni separadores de miles; usa punto como decimal).
- saldo_disponible: saldo disponible de la nota si aparece explícito; si no, usa el mismo valor_nominal.
- fecha_emision: fecha de emisión en formato ISO YYYY-MM-DD. Si solo hay día/mes/año en otro formato, conviértelo.
- estado: estado del documento si aparece (ej. ACTIVO, ANULADO, PAGADO, PENDIENTE, VIGENTE, EMBARGADO, BLOQUEADO). Si no hay estado explícito, usa null.

Reglas:
1. Responde ÚNICAMENTE con un JSON válido, sin markdown ni texto extra.
2. Si un campo no se puede leer con certeza, usa null.
3. No inventes datos.
4. No calcules vigencia ni riesgo: solo extrae lo que aparece en el PDF.

Formato exacto:
{
  "ruc": "1790000000001",
  "titular": "Comercial Andina S.A.",
  "numero_titulo": "NCD-2024-000123",
  "tipo_nota": "NCD",
  "valor_nominal": 1500.50,
  "saldo_disponible": 1500.50,
  "fecha_emision": "2024-03-15",
  "estado": "ACTIVO"
}
"""

_CAMPOS_VACIOS = {
    "ruc": None,
    "titular": None,
    "numero_titulo": None,
    "tipo_nota": None,
    "valor_nominal": None,
    "saldo_disponible": None,
    "fecha_emision": None,
    "estado": None,
}


def configurar_gemini() -> genai.GenerativeModel:
    # Compatibilidad: equipo usa GENAI_APIKEY; local también acepta GEMINI_API_KEY
    api_key = os.getenv("GENAI_APIKEY") or os.getenv("GEMINI_API_KEY") or ""
    if not api_key:
        print(
            "ADVERTENCIA: falta GENAI_APIKEY o GEMINI_API_KEY en el entorno/.env",
            flush=True,
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("models/gemini-3.5-flash")


def descargar_pdf(url: str) -> tuple[bytes, str | None]:
    req = UrlRequest(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp:
        return resp.read(), resp.headers.get("Content-Type")


def _normalizar_aliases(data: dict) -> dict:
    """Acepta nombres viejos (nombre_titular/estado_documento) y los unifica."""
    if data.get("titular") is None and data.get("nombre_titular") is not None:
        data["titular"] = data.get("nombre_titular")
    if data.get("estado") is None and data.get("estado_documento") is not None:
        data["estado"] = data.get("estado_documento")
    if data.get("saldo_disponible") is None and data.get("valor_nominal") is not None:
        data["saldo_disponible"] = data.get("valor_nominal")
    return data


def parsear_json_gemini(texto: str) -> dict:
    """Extrae JSON aunque Gemini lo envuelva en ```json ... ```."""
    texto = (texto or "").strip()
    try:
        data = json.loads(texto)
        return _normalizar_aliases({**_CAMPOS_VACIOS, **data})
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", texto)
    if match:
        try:
            data = json.loads(match.group(0))
            return _normalizar_aliases({**_CAMPOS_VACIOS, **data})
        except json.JSONDecodeError:
            pass

    return {**_CAMPOS_VACIOS, "raw": texto}


def extraer_datos_pdf(
    pdf_bytes: bytes, model: genai.GenerativeModel
) -> tuple[dict, str]:
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
    return parsear_json_gemini(resultado_texto), resultado_texto
