# Evidencia de pruebas de software

## Pruebas agregadas

Archivo: `tests/test_observability.py`

Casos cubiertos:

- Escritura de una traza en archivo JSONL.
- Generacion de resumen agregado.
- Calculo de tasa de exito.
- Creacion de archivo `summary.json`.
- Tolerancia a lineas JSON corruptas en logs.

## Comandos sugeridos

```bash
python -m unittest discover tests
python scripts/analyze_logs.py
python -m streamlit run app.py
```

## Resultado esperado

- Las pruebas unitarias deben finalizar en `OK`.
- El analizador debe crear `observability_data/metrics_summary.json`.
- El dashboard debe mostrar KPIs aunque todavia no existan trazas.

## Nota de ejecucion local

En este entorno de Codex no habia Python instalado en PATH ni una instalacion asociada al lanzador `py`, por lo que no fue posible ejecutar las pruebas aqui. Los archivos quedaron preparados para ejecutarse en el ambiente Python del proyecto.
