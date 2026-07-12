"""Cálculo de la propuesta económica y borrador de negociación (Historia de Usuario 3).

Fórmulas tomadas del "Procedimiento de un operador promedio":
    VE     = VN * P / 100                      (valor efectivo bruto)
    CBVQ   = VE * 0.0009                        (comisión bolsa de valores Quito, 0.09%)
    Ccv    = VE * 0.005                         (comisión casa de valores, 0.5%)
    Vneto  = VE - CBVQ - Ccv - OTROS            (valor neto que recibe el vendedor)

Ejemplo de referencia (VN=$10,000, P=96.50%): VE=$9,650; descuento=$350;
CBVQ≈$8.69; Ccv=$48.25; Vneto≈$9,593.06.
"""

COMISION_BOLSA_PCT = 0.0009  # 0.09%
COMISION_CASA_PCT = 0.005  # 0.5%


def calcular_propuesta(valor_nominal: float, precio_negociacion_pct: float, otros_costos: float = 0.0) -> dict:
    valor_efectivo = valor_nominal * precio_negociacion_pct / 100
    descuento = valor_nominal - valor_efectivo
    comision_bolsa = valor_efectivo * COMISION_BOLSA_PCT
    comision_casa = valor_efectivo * COMISION_CASA_PCT
    valor_neto = valor_efectivo - comision_bolsa - comision_casa - otros_costos

    return {
        "valor_nominal": round(valor_nominal, 2),
        "precio_negociacion_pct": precio_negociacion_pct,
        "valor_efectivo": round(valor_efectivo, 2),
        "descuento": round(descuento, 2),
        "comision_bolsa": round(comision_bolsa, 2),
        "comision_casa": round(comision_casa, 2),
        "otros_costos": round(otros_costos, 2),
        "valor_neto": round(valor_neto, 2),
    }


def generar_borrador(caso, cliente, titulo, negociacion) -> str:
    return f"""BORRADOR DE FICHA DE NEGOCIACIÓN (pendiente de revisión y aprobación del operador)
Expediente: #{caso.id}
Fecha: {negociacion.creado_en:%Y-%m-%d %H:%M}

TITULAR
  Nombre/Razón social: {cliente.razon_social}
  RUC/Cédula: {cliente.ruc_cedula}
  Representante legal: {cliente.representante_legal or "N/A"}

TÍTULO
  Número: {titulo.numero_titulo if titulo else "N/A"}
  Tipo: {titulo.tipo_nota if titulo else "N/A"}
  Valor nominal: ${negociacion.valor_nominal:,.2f}

PROPUESTA ECONÓMICA
  Precio de negociación: {negociacion.precio_negociacion_pct:.2f}%
  Valor efectivo (VE): ${negociacion.valor_efectivo:,.2f}
  Descuento (VN - VE): ${negociacion.descuento:,.2f}
  Comisión bolsa de valores (0.09%): ${negociacion.comision_bolsa:,.2f}
  Comisión casa de valores (0.5%): ${negociacion.comision_casa:,.2f}
  Otros costos: ${negociacion.otros_costos:,.2f}
  VALOR NETO A RECIBIR: ${negociacion.valor_neto:,.2f}

CONDICIONES SOLICITADAS POR EL CLIENTE
  Vigencia de la autorización: {negociacion.vigencia_autorizacion or "No especificada"}
  Cuenta destino: {negociacion.cuenta_destino or "No especificada"}
  Instrucciones especiales: {negociacion.instrucciones_especiales or "Ninguna"}

Este documento es un borrador. La liquidación, transferencia y endoso quedan
como propuesta / alerta / solicitud de aprobación y no se ejecutan en producción
hasta contar con aprobación humana explícita.
"""
