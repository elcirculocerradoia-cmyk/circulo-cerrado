"""
Paso 4: el montaje con ffmpeg. Imágenes fijas con zoom lento (Ken Burns) + la voz.

    cd CARPETA_DEL_VIDEO && python3 .../automatizacion/montaje.py

Lee imagenes/001.jpg… (una por escena), tiempos.json y assets/voz.wav.
Deja video.mp4: 1920×1080, 30 fps, H.264 + AAC.

Cada imagen se escala a 4K antes del zoom: con zoompan a 1080 el movimiento lento
va a saltitos; a 4K no se nota. Los clips se hacen a la vez (uno por núcleo) y se
pegan sin volver a comprimir. Los cortes van en el fotograma exacto del segundo
que dio voz.py, así que la imagen cambia con la frase.
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FPS = 30
ZOOM = 0.12          # cuánto se acerca (o se aleja) en cada imagen: 12 %

# Movimientos, por turnos, para que no sean todos iguales.
# `on` es el fotograma dentro del clip y N el total de fotogramas del clip.
MOVIMIENTOS = [
    # acercarse al centro
    ("1+{z}*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    # alejarse desde el centro
    ("1+{z}-{z}*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    # acercarse un poco y deslizarse de izquierda a derecha
    ("1+{z}", "(iw-iw/zoom)*on/{N}", "ih/2-(ih/zoom/2)"),
    # acercarse a la parte de arriba (caras)
    ("1+{z}*on/{N}", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*0.3"),
    # deslizarse de derecha a izquierda
    ("1+{z}", "(iw-iw/zoom)*(1-on/{N})", "ih/2-(ih/zoom/2)"),
]


def morir(m):
    print(f"\nERROR: {m}", file=sys.stderr)
    sys.exit(1)


def clip(i, img, n, destino):
    z, x, y = (s.format(z=ZOOM, N=max(n - 1, 1)) for s in MOVIMIENTOS[i % len(MOVIMIENTOS)])
    filtro = (f"scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
              f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s=1920x1080:fps={FPS},"
              f"format=yuv420p")
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(img), "-vf", filtro,
                        "-frames:v", str(n), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "20", "-pix_fmt", "yuv420p", "-threads", "1", str(destino)],
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"clip {i + 1}: {p.stderr[-400:]}")


def main():
    tiempos = json.loads(Path("tiempos.json").read_text(encoding="utf-8"))
    imgs = sorted(Path("imagenes").glob("[0-9][0-9][0-9].jpg"))   # no la de la portada
    if len(imgs) != len(tiempos):
        morir(f"Hay {len(imgs)} imágenes y {len(tiempos)} escenas en tiempos.json.")
    if not Path("assets/voz.wav").exists():
        morir("Falta assets/voz.wav.")

    # Fotogramas exactos: el corte de cada escena se redondea al fotograma, sobre el
    # tiempo ACUMULADO, para que en 12 minutos no se descuadre con la voz.
    cortes = [round(t["inicio"] * FPS) for t in tiempos] + [round(tiempos[-1]["fin"] * FPS)]
    cuadros = [max(1, b - a) for a, b in zip(cortes, cortes[1:])]

    tmp = Path("clips")
    tmp.mkdir(exist_ok=True)
    trabajos = os.cpu_count() or 4
    print(f"==> Montando {len(imgs)} clips con zoom lento ({trabajos} a la vez)", flush=True)
    with ThreadPoolExecutor(trabajos) as ex:
        futuros = [ex.submit(clip, i, img, n, tmp / f"{i + 1:03d}.mp4")
                   for i, (img, n) in enumerate(zip(imgs, cuadros))]
        for k, f in enumerate(futuros, 1):
            try:
                f.result()
            except RuntimeError as e:
                morir(str(e))
            if k % 25 == 0:
                print(f"  {k}/{len(futuros)}", flush=True)

    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{(tmp / f'{i + 1:03d}.mp4').resolve().as_posix()}'\n"
                             for i in range(len(imgs))), encoding="utf-8")
    print("==> Juntando los clips con la voz", flush=True)
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
                        "-i", "assets/voz.wav", "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                        "-movflags", "+faststart", "video.mp4"], capture_output=True, text=True)
    if p.returncode:
        morir(f"ffmpeg no ha podido juntar el vídeo: {p.stderr[-600:]}")

    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", "video.mp4"], capture_output=True, text=True).stdout)
    print(f"==> video.mp4 listo: {d / 60:.1f} min, {Path('video.mp4').stat().st_size / 1e6:.0f} MB")
    for c in tmp.glob("*.mp4"):
        c.unlink()


if __name__ == "__main__":
    main()
