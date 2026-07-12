CREATE TABLE IF NOT EXISTS clientes (
    ruc TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS analisis (
    id TEXT PRIMARY KEY,
    url_pdf TEXT,
    ruc TEXT,
    titular TEXT,
    numero_titulo TEXT,
    valor_nominal REAL,
    saldo_disponible REAL,
    fecha_emision TEXT,
    tipo_nota TEXT,
    estado TEXT,
    estado_riesgo TEXT,
    observaciones_json TEXT,
    vneto REAL,
    porcentaje REAL,
    expediente_guardado INTEGER NOT NULL DEFAULT 0,
    operador_id TEXT,
    created_at TEXT NOT NULL
);
