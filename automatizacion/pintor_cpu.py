"""
Las imágenes con FLUX.1-schnell SIN GPU, en los ordenadores de GitHub (gratis, sin tarjeta).

Por qué: Cloudflare gratis solo da ~57 imágenes al día (cada una gasta ~175 de sus 10.000
neuronas: medido el 25/11) y un vídeo necesita ~150. Aquí no hay límite diario; a cambio
cada imagen tarda más, así que el vídeo reparte las imágenes entre varios ordenadores a la vez.

  - Programa: stable-diffusion.cpp (lo compila el workflow).
  - Modelo: second-state/FLUX.1-schnell-GGUF (Apache 2.0, sin registro): versión comprimida
    a 4 bits de FLUX.1-schnell (~6,7 GB) + T5 a 4 bits + CLIP + VAE. ~10 GB en total.
  - Aquí SÍ se elige el tamaño (16:9 directo, sin recortar) y la semilla.

    SD_BIN=... MODELOS=... python pintor_cpu.py --prueba          # 3 imágenes y lo que tarda
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ANCHO, ALTO = 1024, 576        # 16:9, múltiplos de 64
PASOS = 4


def _rutas():
    sd = os.environ.get("SD_BIN", "sd")
    m = Path(os.environ.get("MODELOS", "modelos"))
    return sd, {
        "diffusion": m / "flux1-schnell-Q4_0.gguf",
        "t5": m / "t5xxl-Q4_0.gguf",
        "clip": m / "clip_l.safetensors",
        "vae": m / "ae.safetensors",
    }


def pintar_una(prompt: str, destino: Path, semilla: int, ancho=ANCHO, alto=ALTO) -> float:
    """Pinta una imagen PNG en `destino`. Devuelve los segundos que ha tardado."""
    sd, r = _rutas()
    destino.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    cmd = [sd, "--diffusion-model", str(r["diffusion"]), "--t5xxl", str(r["t5"]),
           "--clip_l", str(r["clip"]), "--vae", str(r["vae"]),
           "-p", prompt, "--cfg-scale", "1.0", "--sampling-method", "euler",
           "--steps", str(PASOS), "-W", str(ancho), "-H", str(alto),
           "-s", str(semilla), "-t", str(os.cpu_count() or 4), "-o", str(destino)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 or not destino.exists():
        raise RuntimeError(f"stable-diffusion.cpp ha fallado ({p.returncode}): {(p.stderr or p.stdout)[-800:]}")
    return time.time() - t


def prueba():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from estilo import prompt_de, ESTILO_PORTADA
    from pintor_cf import PERSONAJES_PRUEBA, ESCENAS_PRUEBA, PORTADA_PRUEBA
    salida = Path(__file__).resolve().parent.parent / "pruebas" / "imagenes-cpu"
    salida.mkdir(parents=True, exist_ok=True)
    # Una con el protagonista, una con dos personajes y una sin nadie; y la portada (cuadrada).
    elegidas = [0, 6, 3]
    trabajos = []
    for i in elegidas:
        quien, d = ESCENAS_PRUEBA[i]
        trabajos.append((f"{i + 1:02d}.png", prompt_de(d, PERSONAJES_PRUEBA, [q for q in quien.split(",") if q]),
                         ANCHO, ALTO))
    trabajos.append(("portada-base.png", prompt_de(PORTADA_PRUEBA, estilo=ESTILO_PORTADA), 768, 768))
    informe = {"nucleos": os.cpu_count(), "imagenes": {}}
    for nombre, prompt, w, h in trabajos:
        print(f"==> Pintando {nombre} ({w}×{h})...", flush=True)
        try:
            s = pintar_una(prompt, salida / nombre, semilla=1234, ancho=w, alto=h)
            informe["imagenes"][nombre] = round(s, 1)
            print(f"    {s:.0f} s", flush=True)
        except RuntimeError as e:
            informe["imagenes"][nombre] = f"ERROR: {e}"
            print(f"    ERROR: {e}", flush=True)
        (salida / "informe.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf-8")
    hechas = [v for v in informe["imagenes"].values() if isinstance(v, float)]
    if not hechas:
        sys.exit(1)
    media = sum(hechas) / len(hechas)
    print(f"==> Media: {media:.0f} s por imagen con {os.cpu_count()} núcleos. "
          f"150 imágenes en 8 ordenadores a la vez ≈ {150 / 8 * media / 60:.0f} min.")


if __name__ == "__main__":
    if "--prueba" in sys.argv:
        prueba()
    else:
        print(__doc__)
