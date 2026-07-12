"""
Genera PDFs de prueba alineados al contrato del equipo + fecha_emision.

Uso:
  python crear_pdf_prueba.py
"""

from pathlib import Path

VIGENTE = {
    "nombre_archivo": "nota_credito_prueba_vigente.pdf",
    "ruc": "1792146739001",
    "titular": "Empresa de Prueba S.A.",
    "numero_titulo": "NCD-2024-000123",
    "valor_nominal": "12500.75",
    "saldo_disponible": "12500.75",
    "fecha_emision": "2024-06-15",
    "tipo_nota": "ISD",
    "estado": "ACTIVO",
}

CADUCADA = {
    "nombre_archivo": "nota_credito_prueba_caducada.pdf",
    "ruc": "1792146739001",
    "titular": "Empresa de Prueba S.A.",
    "numero_titulo": "ISD-2019-000011",
    "valor_nominal": "8500.00",
    "saldo_disponible": "8500.00",
    "fecha_emision": "2019-01-10",
    "tipo_nota": "ISD",
    "estado": "ACTIVO",
}

TITULAR_DIFIERE = {
    "nombre_archivo": "nota_credito_prueba_titular.pdf",
    "ruc": "1792146739001",
    "titular": "Juan Perez Gomez",
    "numero_titulo": "NCD-2025-000456",
    "valor_nominal": "3200.50",
    "saldo_disponible": "3200.50",
    "fecha_emision": "2025-01-20",
    "tipo_nota": "NCD",
    "estado": "ACTIVO",
}


def crear_pdf(ruta: Path, datos: dict) -> None:
    contenido = f"""NOTA DE CREDITO
Tipo: {datos['tipo_nota']}
Numero Titulo: {datos['numero_titulo']}

RUC: {datos['ruc']}
Titular: {datos['titular']}
Valor Nominal: {datos['valor_nominal']}
Saldo Disponible: {datos['saldo_disponible']}
Fecha de Emision: {datos['fecha_emision']}
Estado: {datos['estado']}
"""

    texto_pdf = contenido.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lineas = texto_pdf.split("\n")

    stream_parts = ["BT", "/F1 12 Tf", "50 750 Td"]
    for i, linea in enumerate(lineas):
        if i == 0:
            stream_parts.append(f"({linea}) Tj")
        else:
            stream_parts.append(f"0 -18 Td ({linea}) Tj")
    stream_parts.append("ET")
    stream = "\n".join(stream_parts).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("latin-1")
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )

    ruta.write_bytes(pdf)
    print(f"PDF creado: {ruta.resolve()}")


if __name__ == "__main__":
    base = Path(__file__).parent
    for caso in (VIGENTE, CADUCADA, TITULAR_DIFIERE):
        crear_pdf(base / caso["nombre_archivo"], caso)
