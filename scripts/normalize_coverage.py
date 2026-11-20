"""Regenera XML sin alterar mediciones; resuelve rutas ambiguas de varios --cov."""
from pathlib import Path
import xml.etree.ElementTree as ET

from coverage import Coverage

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Cargar los datos medidos, con una raíz común en vez de varias raíces de paquetes.
    coverage = Coverage(config_file=False, data_file=str(ROOT / ".coverage"), source=[str(ROOT)])
    coverage.load()
    if not coverage.get_data().measured_files():
        raise RuntimeError("No existen mediciones de cobertura")
    output = ROOT / "coverage.xml"
    total = coverage.xml_report(outfile=str(output))
    document = ET.parse(output)
    for source in document.findall("./sources/source"):
        source.text = "."
    document.write(output, encoding="utf-8", xml_declaration=True)
    print(f"Cobertura con rutas relativas inequívocas: {total:.2f}%")
    if total < 80:
        raise RuntimeError("La cobertura no alcanza el umbral obligatorio")


if __name__ == "__main__":
    main()
