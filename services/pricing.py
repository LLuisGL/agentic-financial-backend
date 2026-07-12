from typing import Any


def calcular_vneto(valor_nominal: float, porcentaje_propuesta: float = 96.0) -> dict[str, Any]:
    if valor_nominal is None:
        raise ValueError("valor_nominal es requerido")
    valor = float(valor_nominal)
    porcentaje = float(porcentaje_propuesta)
    if porcentaje <= 0 or porcentaje > 100:
        raise ValueError("porcentaje_propuesta debe estar entre 0 y 100")

    vneto = round(valor * (porcentaje / 100.0), 2)
    comision = round(valor - vneto, 2)
    return {
        "valor_nominal": valor,
        "porcentaje_propuesta": porcentaje,
        "vneto": vneto,
        "comision": comision,
        "mensaje_propuesta": (
            f"Propuesta: {porcentaje:g}% del valor nominal ${valor:,.2f}. "
            f"Vneto = ${vneto:,.2f} (comisión ${comision:,.2f})."
        ),
    }
