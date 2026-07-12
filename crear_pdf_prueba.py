"""
Genera un PDF de prueba de nota de crédito con datos conocidos.
Uso:
  python crear_pdf_prueba.py
"""

from pathlib import Path

# Datos que Gemini debería extraer
RUC = "1792146739001"
VALOR_NOMINAL = "12500.75"
ESTADO = "ACTIVO"


def crear_pdf(ruta: Path) -> None:
    # PDF mínimo válido (texto seleccionable) sin librerías externas
    contenido = f"""NOTA DE CREDITO

RUC: {RUC}
Valor Nominal: {VALOR_NOMINAL}
Estado: {ESTADO}

Cliente: Empresa de Prueba S.A.
Documento: NC-001-001-000012345
"""

    # Escapar paréntesis para sintaxis PDF
    texto_pdf = contenido.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lineas = texto_pdf.split("\n")

    # Construir operadores de texto PDF (una línea debajo de otra)
    y = 750
    stream_parts = ["BT", "/F1 14 Tf", "50 750 Td"]
    for i, linea in enumerate(lineas):
        if i == 0:
            stream_parts.append(f"({linea}) Tj")
        else:
            stream_parts.append(f"0 -22 Td ({linea}) Tj")
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
    print(f"Datos esperados -> ruc={RUC}, valor_nominal={VALOR_NOMINAL}, estado={ESTADO}")


if __name__ == "__main__":
    crear_pdf(Path(__file__).parent / "nota_credito_prueba.pdf")
