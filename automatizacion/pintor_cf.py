"""
Paso 3: las imágenes, con FLUX.1-schnell en Cloudflare Workers AI.

Gratis: 10.000 «neuronas» al día (se reinician a las 00:00 UTC). Cada imagen gasta unas
58 → caben unas 170 al día: un vídeo (≈150 + portada) y poco más. Si se acaban, Cloudflare
da error y NO cobra (el plan gratis no tiene forma de pasarse).

Lo que hace Cloudflare con este modelo (comprobado en su documentación, 25/11/2026):
  - Solo acepta `prompt` (hasta 2.048 letras) y `steps` (máx. 8). NO deja elegir el tamaño:
    la imagen sale como sale, y aquí se RECORTA a 16:9 por el centro. Por eso Claude
    describe escenas con lo importante en el centro.
  - La semilla no está en su esquema: se prueba una vez y, si la rechaza, se sigue sin ella.

    python3 pintor_cf.py --prueba          # las 20 imágenes de prueba → pruebas/imagenes-cloudflare/

Necesita CF_ACCOUNT_ID y CF_API_TOKEN (token con permiso «Workers AI»).
"""

import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

URL = "https://api.cloudflare.com/client/v4/accounts/{cuenta}/ai/run/@cf/black-forest-labs/flux-1-schnell"
PASOS = 4
A_LA_VEZ = 4            # peticiones en paralelo (sin pasarse: Cloudflare también limita por minuto)
_con_semilla = True     # se apaga sola si Cloudflare no la acepta


class SinNeuronas(Exception):
    """Se ha acabado lo gratis de hoy."""


def _morir(m):
    print(f"\nERROR: {m}", file=sys.stderr)
    sys.exit(1)


def _llamar(prompt: str, semilla: int | None) -> bytes:
    global _con_semilla
    cuenta, token = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not cuenta or not token:
        _morir("Faltan CF_ACCOUNT_ID o CF_API_TOKEN.")
    espera = 5
    for intento in range(1, 8):
        cuerpo = {"prompt": prompt[:2048], "steps": PASOS}
        if _con_semilla and semilla is not None:
            cuerpo["seed"] = int(semilla)
        req = urllib.request.Request(URL.format(cuenta=cuenta), data=json.dumps(cuerpo).encode(),
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            img = (d.get("result") or {}).get("image")
            if not img:
                raise RuntimeError(f"Cloudflare no ha devuelto imagen: {str(d)[:300]}")
            return base64.b64decode(img)
        except urllib.error.HTTPError as e:
            texto = e.read().decode(errors="replace")[:600].replace(token, "[token]")
            bajo = texto.lower()
            if e.code == 400 and "seed" in bajo and _con_semilla:
                print("  Cloudflare no acepta semilla: sigo sin ella.", flush=True)
                _con_semilla = False
                continue
            if "neuron" in bajo or "allocation" in bajo or "4006" in bajo:
                raise SinNeuronas(texto)
            if e.code in (429, 500, 502, 503, 504) and intento < 7:
                time.sleep(espera)
                espera = min(espera * 2, 60)
                continue
            raise RuntimeError(f"Cloudflare HTTP {e.code}: {texto}")
        except (urllib.error.URLError, TimeoutError) as e:
            if intento < 7:
                time.sleep(espera)
                continue
            raise RuntimeError(f"Cloudflare no responde: {e}")
    raise RuntimeError("Cloudflare: demasiados reintentos.")


def a_16_9(b: bytes, calidad=93) -> bytes:
    """Recorta al centro a 16:9 (un poco por encima del centro: ahí suelen estar las caras)."""
    img = Image.open(io.BytesIO(b)).convert("RGB")
    w, h = img.size
    if w / h > 16 / 9:
        nw = round(h * 16 / 9)
        x = (w - nw) // 2
        img = img.crop((x, 0, x + nw, h))
    else:
        nh = round(w * 9 / 16)
        y = max(0, min(h - nh, round((h - nh) * 0.45)))
        img = img.crop((0, y, w, y + nh))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=calidad)
    return out.getvalue()


def pintar(prompts: list[str], destinos: list[Path], semilla: int | None = None) -> dict:
    """Pinta cada prompt en su destino (JPEG 16:9). Devuelve tiempos y tamaño original."""
    t0 = time.time()
    tamanos = {}

    def una(i):
        if destinos[i].exists():          # si se relanza, no se vuelve a gastar
            return
        b = _llamar(prompts[i], semilla)
        s = Image.open(io.BytesIO(b)).size
        tamanos[s] = tamanos.get(s, 0) + 1
        destinos[i].parent.mkdir(parents=True, exist_ok=True)
        destinos[i].write_bytes(a_16_9(b))

    # La primera sola: así se sabe si acepta semilla antes de lanzar el resto.
    una(0)
    hechas = 1
    with ThreadPoolExecutor(A_LA_VEZ) as ex:
        for _ in ex.map(una, range(1, len(prompts))):
            hechas += 1
            if hechas % 25 == 0:
                print(f"  {hechas}/{len(prompts)} imágenes", flush=True)
    total = time.time() - t0
    return {"imagenes": len(prompts), "segundos": round(total, 1),
            "tamano_original": {f"{w}x{h}": n for (w, h), n in tamanos.items()},
            "con_semilla": _con_semilla}


# ── La prueba de 20 imágenes ──────────────────────────────────────────────────
PERSONAJES_PRUEBA = {
    "tu": "the main character: a young man in his late twenties, short messy brown hair, "
          "thin mustache, white chef jacket, nervous eyes",
    "magnate": "a tall rich man in his sixties, slicked back silver hair, dark sunglasses, "
               "black tailored suit, gold watch",
}
ESCENAS_PRUEBA = [
    ("tu", "sitting at a small kitchen table in a tiny cheap apartment at night, unpaid bills scattered, warm lamp light"),
    ("tu", "looking shocked at a smartphone screen glowing in the dark bedroom"),
    ("tu", "standing at a small private airport next to a sleek white private jet, sunny day"),
    ("", "a luxury private island seen from above, turquoise sea, white villa with pool, palm trees"),
    ("tu", "walking into a huge luxurious marble kitchen with copper pots, sunlight through big windows"),
    ("magnate", "standing on a terrace at sunset holding a glass of red wine, looking at the sea"),
    ("tu,magnate", "the rich man handing a thick contract to the main character across a dark wooden desk in an elegant office"),
    ("tu", "cooking a fancy dish in the luxury kitchen, flames rising from a pan, focused face"),
    ("", "a long candlelit dining table with eight empty chairs, silver plates, chandelier, night"),
    ("tu", "close up of the main character's worried face, sweat on the forehead, dim light"),
    ("", "a black helicopter landing on a helipad at night, bright spotlights, wind"),
    ("tu", "peeking through the gap of a half open door into a dark corridor, suspicious"),
    ("", "a locked steel door at the end of a dark corridor with a red light above it"),
    ("tu", "lying awake in a luxurious bed at night, moonlight through the curtains, eyes wide open"),
    ("magnate", "sitting in a leather armchair in a dark library, face half in shadow, smiling coldly"),
    ("", "an open briefcase full of stacks of money on a glass table, dramatic light"),
    ("tu", "running along a moonlit beach, looking back over the shoulder, scared"),
    ("", "a luxury yacht anchored near the island at night, all lights on, mysterious"),
    ("tu,magnate", "the rich man putting a hand on the shoulder of the main character in a hallway, tense"),
    ("tu", "standing alone on a wooden pier at dawn, looking at the horizon, the island behind"),
]


def prueba():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from estilo import prompt_de, ESTILO_PORTADA
    raiz = Path(__file__).resolve().parent.parent
    salida = raiz / "pruebas" / "imagenes-cloudflare"
    prompts = [prompt_de(d, PERSONAJES_PRUEBA, [q for q in quien.split(",") if q])
               for quien, d in ESCENAS_PRUEBA]
    prompts.append(prompt_de("terrified face looking up at a black helicopter in the night sky",
                             PERSONAJES_PRUEBA, ["tu"], estilo=ESTILO_PORTADA))
    destinos = [salida / f"{i:02d}.jpg" for i in range(1, len(prompts))] + [salida / "portada-base.jpg"]
    print(f"==> Prueba: {len(prompts)} imágenes con FLUX.1-schnell en Cloudflare", flush=True)
    try:
        r = pintar(prompts, destinos, semilla=1234)
    except SinNeuronas as e:
        _morir(f"Se ha acabado lo gratis de hoy en Cloudflare: {e}")
    print(f"==> Hecho en {r['segundos']:.0f} s ({r['segundos'] / len(prompts):.1f} s por imagen con "
          f"{A_LA_VEZ} a la vez). Tamaño que da Cloudflare: {r['tamano_original']}. "
          f"Semilla: {'sí' if r['con_semilla'] else 'no'}.")
    (salida / "informe.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    # La portada de prueba, con su texto y flecha, para verla entera.
    import subprocess
    tmp = salida / "portada"
    (tmp / "imagenes").mkdir(parents=True, exist_ok=True)
    (tmp / "imagenes" / "portada.jpg").write_bytes((salida / "portada-base.jpg").read_bytes())
    (tmp / "resumen.json").write_text(json.dumps({"portada": {"texto": "NO MIRES"}}), encoding="utf-8")
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "portada.py")], cwd=tmp, check=False)
    print(f"==> Imágenes en {salida}")


if __name__ == "__main__":
    if "--prueba" in sys.argv:
        prueba()
    else:
        print(__doc__)
