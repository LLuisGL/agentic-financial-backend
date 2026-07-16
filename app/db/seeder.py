"""Datos de demostración: se cargan una sola vez si la base está vacía.

Permiten demostrar de extremo a extremo la reutilización de antecedentes
(HU1), duplicados/riesgo (HU2) y negociación (HU3) sin depender de una
integración real con el SRI o DECEVALE.
"""

import datetime

from sqlalchemy.orm import Session

from app import models


def seed_if_empty(db: Session) -> None:
    if db.query(models.Cliente).first():
        return

    cliente1 = models.Cliente(
        ruc_cedula="1790012345001",
        razon_social="Comercial Andina S.A.",
        tipo_persona="JURIDICA",
        representante_legal="María Fernanda Torres",
    )
    cliente2 = models.Cliente(
        ruc_cedula="0912345678",
        razon_social="Carlos Alberto Muñoz",
        tipo_persona="NATURAL",
    )
    cliente3 = models.Cliente(
        ruc_cedula="1791234567001",
        razon_social="Exportadora Pacífico Cía. Ltda.",
        tipo_persona="JURIDICA",
        representante_legal="Jorge Iván Salcedo",
    )
    db.add_all([cliente1, cliente2, cliente3])
    db.flush()

    titulo1 = models.Titulo(
        cliente_id=cliente1.id,
        numero_titulo="NCD-2024-000123",
        tipo_nota="NCD",
        valor_nominal=10000.0,
        saldo_disponible=10000.0,
        estado="VIGENTE",
        fecha_emision=datetime.date(2024, 3, 15),
    )
    titulo2 = models.Titulo(
        cliente_id=cliente2.id,
        numero_titulo="ISD-2021-000045",
        tipo_nota="ISD",
        valor_nominal=5000.0,
        saldo_disponible=5000.0,
        estado="VIGENTE",
        fecha_emision=datetime.date(2021, 5, 10),  # caducada: > 4 años
    )
    titulo3 = models.Titulo(
        cliente_id=cliente3.id,
        numero_titulo="NCE-2024-000789",
        tipo_nota="NCE",
        valor_nominal=25000.0,
        saldo_disponible=18000.0,
        estado="PARCIALMENTE_NEGOCIADA",
        fecha_emision=datetime.date(2024, 1, 20),
        tiene_restriccion=True,
    )
    titulo4 = models.Titulo(
        cliente_id=cliente1.id,
        numero_titulo="NCD-2024-000500",
        tipo_nota="NCD",
        valor_nominal=8000.0,
        saldo_disponible=3500.0,
        estado="PARCIALMENTE_NEGOCIADA",
        fecha_emision=datetime.date(2024, 6, 1),
    )
    db.add_all([titulo1, titulo2, titulo3, titulo4])
    db.flush()

    caso_previo = models.Caso(
        cliente_id=cliente1.id,
        titulo_id=titulo1.id,
        operador="Ana Paredes",
        estado="CERRADO",
        proxima_accion=None,
        observaciones="Caso anterior cerrado exitosamente, sirve como antecedente.",
    )
    db.add(caso_previo)

    db.add_all(
        [
            models.ListaRiesgo(ruc_cedula="1791234567001", nombre="Exportadora Pacífico Cía. Ltda.", motivo="PEP", nivel="MEDIO"),
            models.ListaRiesgo(ruc_cedula=None, nombre="Persona Sancionada Ejemplo", motivo="SANCIONADO", nivel="ALTO"),
        ]
    )

    db.commit()
