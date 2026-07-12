import json

from app import models


def cliente_a_dict(cliente: models.Cliente) -> dict:
    return {
        "id": cliente.id,
        "ruc_cedula": cliente.ruc_cedula,
        "razon_social": cliente.razon_social,
        "tipo_persona": cliente.tipo_persona,
        "representante_legal": cliente.representante_legal,
        "creado_en": cliente.creado_en.isoformat(),
    }


def titulo_a_dict(titulo: models.Titulo) -> dict:
    return {
        "id": titulo.id,
        "numero_titulo": titulo.numero_titulo,
        "tipo_nota": titulo.tipo_nota,
        "valor_nominal": titulo.valor_nominal,
        "saldo_disponible": titulo.saldo_disponible,
        "estado": titulo.estado,
        "fecha_emision": titulo.fecha_emision.isoformat() if titulo.fecha_emision else None,
        "bloqueado": titulo.bloqueado,
        "tiene_restriccion": titulo.tiene_restriccion,
        "url_documento": titulo.url_documento,
    }


def evento_a_dict(evento: models.EventoCaso) -> dict:
    return {
        "id": evento.id,
        "tipo": evento.tipo,
        "descripcion": evento.descripcion,
        "data": json.loads(evento.data_json) if evento.data_json else None,
        "creado_en": evento.creado_en.isoformat(),
    }


def diligencia_a_dict(diligencia: models.DebidaDiligencia) -> dict:
    return {
        "identidad_ok": diligencia.identidad_ok,
        "capacidad_legal_ok": diligencia.capacidad_legal_ok,
        "representacion_legal_ok": diligencia.representacion_legal_ok,
        "beneficiario_final": diligencia.beneficiario_final,
        "kyc_formulario_ok": diligencia.kyc_formulario_ok,
        "origen_fondos_ok": diligencia.origen_fondos_ok,
        "riesgo_match": diligencia.riesgo_match,
        "riesgo_detalle": diligencia.riesgo_detalle,
        "resultado": diligencia.resultado,
        "pendientes": json.loads(diligencia.pendientes_json) if diligencia.pendientes_json else [],
    }


def negociacion_a_dict(negociacion: models.Negociacion) -> dict:
    return {
        "id": negociacion.id,
        "valor_nominal": negociacion.valor_nominal,
        "precio_negociacion_pct": negociacion.precio_negociacion_pct,
        "valor_efectivo": negociacion.valor_efectivo,
        "descuento": negociacion.descuento,
        "comision_bolsa": negociacion.comision_bolsa,
        "comision_casa": negociacion.comision_casa,
        "otros_costos": negociacion.otros_costos,
        "valor_neto": negociacion.valor_neto,
        "vigencia_autorizacion": negociacion.vigencia_autorizacion,
        "instrucciones_especiales": negociacion.instrucciones_especiales,
        "cuenta_destino": negociacion.cuenta_destino,
        "estado": negociacion.estado,
        "borrador_texto": negociacion.borrador_texto,
        "creado_en": negociacion.creado_en.isoformat(),
    }


def caso_a_dict(caso: models.Caso, incluir_relaciones: bool = True) -> dict:
    data = {
        "id": caso.id,
        "operador": caso.operador,
        "estado": caso.estado,
        "proxima_accion": caso.proxima_accion,
        "observaciones": caso.observaciones,
        "creado_en": caso.creado_en.isoformat(),
        "actualizado_en": caso.actualizado_en.isoformat(),
        "cliente": cliente_a_dict(caso.cliente),
        "titulo": titulo_a_dict(caso.titulo) if caso.titulo else None,
    }
    if incluir_relaciones:
        data["bitacora"] = [evento_a_dict(e) for e in caso.eventos]
        data["diligencia"] = diligencia_a_dict(caso.diligencia) if caso.diligencia else None
        data["negociaciones"] = [negociacion_a_dict(n) for n in caso.negociaciones]
    return data
