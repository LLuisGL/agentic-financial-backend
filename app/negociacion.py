"""Cálculo de la propuesta económica y borrador de negociación (Historia de Usuario 3).

Fórmulas del "Procedimiento de un operador promedio":
    VE     = VN * P / 100                      (valor efectivo bruto)
    CBVQ   = VE * 0.0009                        (comisión bolsa de valores Quito, 0.09%)
    Ccv    = VE * 0.005                         (comisión casa de valores, 0.5%)
    Vneto  = VE - CBVQ - Ccv - OTROS            (valor neto que recibe el vendedor)

Ejemplo de referencia (VN=$10,000, P=96.50%): VE=$9,650; descuento=$350;
CBVQ≈$8.69; Ccv=$48.25; Vneto≈$9,593.06.

Además: tabla referencial de precios de mercado (BVQ) → mediana → Gemini
recomienda el porcentaje a proponer en la negociación (HITL: el operador decide).
"""

from __future__ import annotations

import json
import os
import re
import statistics

COMISION_BOLSA_PCT = 0.0009  # 0.09%
COMISION_CASA_PCT = 0.005  # 0.5%  (documentado como 0,005)

# Tabla referencial del procedimiento (precios % de negociaciones recientes BVQ + notas ejemplo).
PRECIOS_REFERENCIA_MERCADO: list[dict] = [
    {"fecha": "8 de julio", "valor_nominal": 19421.66, "valor_efectivo": 19101.20, "precio": 98.35},
    {"fecha": "8 de julio", "valor_nominal": 4008.96, "valor_efectivo": 3942.81, "precio": 98.35},
    {"fecha": "8 de julio", "valor_nominal": 946.25, "valor_efectivo": 924.01, "precio": 97.65},
    {"fecha": "9 de julio", "valor_nominal": 10022.94, "valor_efectivo": 9862.57, "precio": 98.40},
    {"fecha": "9 de julio", "valor_nominal": 2539.74, "valor_efectivo": 2500.37, "precio": 98.45},
    {"fecha": "9 de julio", "valor_nominal": 279.20, "valor_efectivo": 270.82, "precio": 97.00},
    {"fecha": "10 de julio", "valor_nominal": 1798.96, "valor_efectivo": 1753.99, "precio": 97.50},
    {"fecha": "10 de julio", "valor_nominal": 409.59, "valor_efectivo": 389.11, "precio": 95.00},
    {"fecha": "10 de julio", "valor_nominal": 4679.25, "valor_efectivo": 4576.31, "precio": 97.80},
    {"nota": "NC-001", "valor_nominal": 395.15, "precio": 96.00},
    {"nota": "NC-002", "valor_nominal": 2409.97, "precio": 98.35},
]


def precios_referencia() -> list[float]:
    return [float(row["precio"]) for row in PRECIOS_REFERENCIA_MERCADO]


def calcular_mediana_precios(precios: list[float] | None = None) -> float:
    serie = sorted(precios if precios is not None else precios_referencia())
    if not serie:
        raise ValueError("No hay precios de referencia para calcular la mediana.")
    return round(float(statistics.median(serie)), 4)


def calcular_propuesta(valor_nominal: float, precio_negociacion_pct: float, otros_costos: float = 0.0) -> dict:
    """Calcula VE, descuento, comisiones BVQ/casa y valor neto final."""
    valor_efectivo = valor_nominal * precio_negociacion_pct / 100
    descuento = valor_nominal - valor_efectivo
    comision_bolsa = valor_efectivo * COMISION_BOLSA_PCT
    comision_casa = valor_efectivo * COMISION_CASA_PCT
    valor_neto = valor_efectivo - comision_bolsa - comision_casa - otros_costos

    return {
        "valor_nominal": round(valor_nominal, 2),
        "precio_negociacion_pct": round(precio_negociacion_pct, 4),
        "valor_efectivo": round(valor_efectivo, 2),
        "descuento": round(descuento, 2),
        "comision_bolsa": round(comision_bolsa, 2),
        "comision_casa": round(comision_casa, 2),
        "otros_costos": round(otros_costos, 2),
        "valor_neto": round(valor_neto, 2),
    }


def _parsear_json_ia(texto: str) -> dict:
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
    return {}


def recomendar_porcentaje_con_ia(
    *,
    mediana: float | None = None,
    monto_negociar: float | None = None,
    tipo_nota: str | None = None,
    precio_minimo_cliente: float | None = None,
) -> dict:
    """Consulta a Gemini el % recomendado anclado a la mediana de la tabla referencial."""
    precios = precios_referencia()
    mediana_calc = mediana if mediana is not None else calcular_mediana_precios(precios)

    api_key = os.getenv("GENAI_APIKEY")
    if not api_key:
        # Sin API key: fallback determinista a la mediana (sigue siendo útil para el operador).
        return {
            "porcentaje_recomendado": mediana_calc,
            "justificacion": (
                "Sin GENAI_APIKEY: se recomienda la mediana de la tabla referencial BVQ "
                f"({mediana_calc}%)."
            ),
            "fuente": "mediana_tabla_referencial",
            "modelo": None,
        }

    genai_mod = __import__("google.generativeai", fromlist=["generativeai"])
    genai_mod.configure(api_key=api_key)
    model = genai_mod.GenerativeModel("models/gemini-2.5-flash")

    prompt = f"""
Eres un analista de negociación de notas de crédito tributarias en Ecuador (BVQ).
Debes recomendar UN porcentaje de precio de negociación (P) para proponer al operador humano.

Datos de mercado (tabla referencial del procedimiento del operador):
{json.dumps(PRECIOS_REFERENCIA_MERCADO, ensure_ascii=False)}

Precios (%): {precios}
Mediana de todos los porcentajes: {mediana_calc}

Contexto de la operación actual:
- monto_a_negociar: {monto_negociar}
- tipo_nota: {tipo_nota}
- precio_minimo_cliente: {precio_minimo_cliente}

Reglas:
1. Ancla la recomendación en la mediana ({mediana_calc}). Puedes ajustar levemente (+/- 1.5 pp) según volumen, dispersión del mercado y precio mínimo del cliente.
2. Si hay precio_minimo_cliente, la recomendación NO debe ser menor a ese mínimo.
3. El porcentaje debe estar entre 90 y 100.
4. Responde ÚNICAMENTE JSON válido, sin markdown:
{{"porcentaje_recomendado": 97.8, "justificacion": "texto breve"}}
"""

    response = model.generate_content(prompt)
    try:
        texto = response.text
    except Exception:
        texto = str(response)

    data = _parsear_json_ia(texto)
    try:
        recomendado = float(data.get("porcentaje_recomendado"))
    except (TypeError, ValueError):
        recomendado = mediana_calc

    if precio_minimo_cliente is not None:
        recomendado = max(recomendado, float(precio_minimo_cliente))
    recomendado = min(100.0, max(90.0, round(recomendado, 4)))

    return {
        "porcentaje_recomendado": recomendado,
        "justificacion": str(data.get("justificacion") or f"Recomendación anclada a la mediana {mediana_calc}%."),
        "fuente": "gemini+mediana_tabla_referencial",
        "modelo": "models/gemini-2.5-flash",
        "raw": texto,
    }


def construir_recomendacion_propuesta(
    *,
    valor_base: float | None = None,
    tipo_nota: str | None = None,
    precio_minimo_cliente: float | None = None,
    otros_costos: float = 0.0,
) -> dict:
    """Empaqueta mediana + recomendación IA + cálculo estimado de Vneto (si hay monto)."""
    precios = precios_referencia()
    mediana = calcular_mediana_precios(precios)
    ia = recomendar_porcentaje_con_ia(
        mediana=mediana,
        monto_negociar=valor_base,
        tipo_nota=tipo_nota,
        precio_minimo_cliente=precio_minimo_cliente,
    )
    porcentaje = float(ia["porcentaje_recomendado"])

    resultado = {
        "precios_referencia": PRECIOS_REFERENCIA_MERCADO,
        "precios": precios,
        "mediana": mediana,
        "porcentaje_recomendado": porcentaje,
        "justificacion": ia["justificacion"],
        "fuente": ia["fuente"],
        "modelo": ia.get("modelo"),
        "calculo_estimado": None,
    }
    if valor_base is not None and valor_base > 0:
        resultado["calculo_estimado"] = calcular_propuesta(valor_base, porcentaje, otros_costos)
    return resultado


def generar_borrador(caso, cliente, titulo, negociacion, recomendacion: dict | None = None) -> str:
    from app import mensajes

    return mensajes.mensaje_propuesta_ticket(
        negociacion=negociacion,
        titular=cliente.razon_social if cliente else None,
        ruc=cliente.ruc_cedula if cliente else None,
        codigo_nota=titulo.numero_titulo if titulo else None,
        recomendacion=recomendacion,
    )
