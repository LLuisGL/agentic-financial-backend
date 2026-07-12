import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "agentic.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

SEED_CLIENTES = [
    ("1792146739001", "Empresa de Prueba S.A.", 1),
    ("0999999999001", "Comercial Andina Cia. Ltda.", 1),
    ("1790000000001", "Cliente Demo Ecuador S.A.", 1),
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        for ruc, nombre, activo in SEED_CLIENTES:
            conn.execute(
                """
                INSERT OR IGNORE INTO clientes (ruc, nombre, activo)
                VALUES (?, ?, ?)
                """,
                (ruc, nombre, activo),
            )
        conn.commit()


def buscar_cliente_por_ruc(ruc: str | None) -> dict[str, Any] | None:
    if not ruc:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT ruc, nombre, activo FROM clientes WHERE ruc = ?",
            (ruc,),
        ).fetchone()
    return dict(row) if row else None


def crear_analisis(
    *,
    url_pdf: str | None,
    ruc: str | None,
    titular: str | None,
    numero_titulo: str | None,
    valor_nominal: float | None,
    saldo_disponible: float | None,
    fecha_emision: str | None,
    tipo_nota: str | None,
    estado: str | None,
) -> str:
    analisis_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analisis (
                id, url_pdf, ruc, titular, numero_titulo, valor_nominal,
                saldo_disponible, fecha_emision, tipo_nota, estado,
                estado_riesgo, observaciones_json, vneto, porcentaje,
                expediente_guardado, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, 0, ?)
            """,
            (
                analisis_id,
                url_pdf,
                ruc,
                titular,
                numero_titulo,
                valor_nominal,
                saldo_disponible,
                fecha_emision,
                tipo_nota,
                estado,
                created_at,
            ),
        )
        conn.commit()
    return analisis_id


def actualizar_analisis(analisis_id: str, **campos: Any) -> None:
    if not campos:
        return
    permitidos = {
        "ruc",
        "titular",
        "numero_titulo",
        "valor_nominal",
        "saldo_disponible",
        "fecha_emision",
        "tipo_nota",
        "estado",
        "estado_riesgo",
        "observaciones_json",
        "vneto",
        "porcentaje",
        "expediente_guardado",
        "operador_id",
        "url_pdf",
    }
    updates = {k: v for k, v in campos.items() if k in permitidos}
    if "observaciones_json" in updates and not isinstance(updates["observaciones_json"], str):
        updates["observaciones_json"] = json.dumps(
            updates["observaciones_json"], ensure_ascii=False
        )
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [analisis_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE analisis SET {cols} WHERE id = ?", values)
        conn.commit()


def obtener_analisis(analisis_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analisis WHERE id = ?", (analisis_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    if data.get("observaciones_json"):
        try:
            data["observaciones"] = json.loads(data["observaciones_json"])
        except json.JSONDecodeError:
            data["observaciones"] = []
    else:
        data["observaciones"] = []
    return data
