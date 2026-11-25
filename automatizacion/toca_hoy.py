"""
¿Toca hacer el vídeo ahora? Lo pregunta GitHub Actions antes de empezar.

GitHub solo entiende la hora UTC, y Madrid cambia de hora en verano. Por eso el reloj
salta DOS veces (7:45 y 8:45 UTC) y aquí se decide cuál vale:
  - Solo si en Madrid son entre las 9:30 y las 12:00 (GitHub a veces se retrasa).
  - Y solo si hoy no se ha empezado ya otro (canales/circulo-cerrado-ultimo.txt).
    Si el primero falla, NO se repite: cada intento gasta límite de Claude.
Lanzado a mano (workflow_dispatch) siempre toca, y no apunta nada.

    python3 toca_hoy.py schedule          → imprime seguir=true / seguir=false
"""

import datetime
import sys
import zoneinfo
from pathlib import Path

MARCA = Path(__file__).resolve().parent / "canales" / "circulo-cerrado-ultimo.txt"

evento = sys.argv[1] if len(sys.argv) > 1 else "schedule"
ahora = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Madrid"))
hoy = f"{ahora:%Y-%m-%d}"

if evento != "schedule":
    print("seguir=true")
    sys.exit(0)

en_hora = datetime.time(9, 30) <= ahora.time() <= datetime.time(12, 0)
ya_hecho = MARCA.exists() and MARCA.read_text(encoding="utf-8").strip() == hoy
if en_hora and not ya_hecho:
    MARCA.write_text(hoy + "\n", encoding="utf-8")
    print("seguir=true")
else:
    print("seguir=false")
    print(f"No toca: en Madrid son las {ahora:%H:%M}" + (" y hoy ya se empezó." if ya_hecho else "."),
          file=sys.stderr)
