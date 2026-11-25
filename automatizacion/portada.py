"""
Paso 5: la portada (miniatura) de YouTube, 1280×720.

    cd CARPETA_DEL_VIDEO && python3 .../automatizacion/portada.py

Parte de imagenes/portada.jpg (la pinta FLUX con el protagonista a la derecha y
sitio libre a la izquierda) y le pone encima:
  - el texto de resumen.json → portada.texto, grande, amarillo con borde negro,
  - una flecha curva roja que va del texto al personaje.
Deja portada.jpg (menos de 2 MB, como pide YouTube).
"""

import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
AMARILLO = (255, 214, 0)
ROJO = (230, 30, 35)
NEGRO = (0, 0, 0)

FUENTES = [
    os.environ.get("FUENTE_PORTADA", ""),
    "/root/.fonts/Anton-Regular.ttf",
    "/root/.fonts/ArchivoBlack-Regular.ttf",
    str(Path.home() / ".fonts" / "Anton-Regular.ttf"),
    "C:/Windows/Fonts/impact.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def fuente(tam):
    for f in FUENTES:
        if f and Path(f).exists():
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default(tam)


def cubrir(img):
    """Escala y recorta al centro hasta llenar 1280×720 (sin achatar)."""
    r = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def texto_que_cabe(d, palabras, ancho_max, alto_max):
    """Parte en 1 o 2 líneas y busca el tamaño más grande que entra."""
    opciones = [[" ".join(palabras)]]
    if len(palabras) > 1:
        for k in range(1, len(palabras)):
            opciones.append([" ".join(palabras[:k]), " ".join(palabras[k:])])
    mejor = None
    for lineas in opciones:
        for tam in range(260, 60, -6):
            f = fuente(tam)
            cajas = [d.textbbox((0, 0), l, font=f, stroke_width=tam // 14) for l in lineas]
            an = max(c[2] - c[0] for c in cajas)
            al = sum(c[3] - c[1] for c in cajas) + (len(lineas) - 1) * tam * 0.08
            if an <= ancho_max and al <= alto_max:
                if not mejor or tam > mejor[0]:
                    mejor = (tam, lineas)
                break
    return mejor or (70, [" ".join(palabras)])


def flecha(d, p0, p1, p2, grosor=16):
    """Curva de Bézier de p0 a p2 pasando cerca de p1, con punta en p2. Borde negro."""
    pts = [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])
           for t in [i / 60 for i in range(61)]]
    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
    largo, ancho = grosor * 3.2, grosor * 2.6

    def punta(extra):
        x, y = p2
        l, a = largo + extra, ancho + extra
        return [(x + extra * 0.6 * math.cos(ang), y + extra * 0.6 * math.sin(ang)),
                (x - l * math.cos(ang) + a * math.sin(ang), y - l * math.sin(ang) - a * math.cos(ang)),
                (x - l * math.cos(ang) - a * math.sin(ang), y - l * math.sin(ang) + a * math.cos(ang))]

    cuerpo = pts[:-5]
    d.line(cuerpo, fill=NEGRO, width=grosor + 12, joint="curve")
    d.polygon(punta(10), fill=NEGRO)
    d.line(cuerpo, fill=ROJO, width=grosor, joint="curve")
    d.polygon(punta(0), fill=ROJO)


def main():
    r = json.loads(Path("resumen.json").read_text(encoding="utf-8"))
    texto = (r.get("portada") or {}).get("texto") or "ES UNA TRAMPA"
    base = Path("imagenes/portada.jpg")
    if not base.exists():
        base = sorted(Path("imagenes").glob("[0-9][0-9][0-9].jpg"))[0]
    img = cubrir(Image.open(base).convert("RGB"))
    d = ImageDraw.Draw(img)

    # Texto en la mitad izquierda, centrado en vertical.
    margen = 48
    tam, lineas = texto_que_cabe(d, texto.upper().split(), W * 0.5 - margen, H * 0.62)
    f = fuente(tam)
    borde = max(6, tam // 14)
    alturas = [d.textbbox((0, 0), l, font=f, stroke_width=borde) for l in lineas]
    total = sum(c[3] - c[1] for c in alturas) + (len(lineas) - 1) * tam * 0.08
    y = (H - total) / 2 - 30
    abajo_texto, derecha_texto = 0, 0
    for l, c in zip(lineas, alturas):
        d.text((margen - c[0], y - c[1]), l, font=f, fill=AMARILLO, stroke_width=borde, stroke_fill=NEGRO)
        derecha_texto = max(derecha_texto, margen + c[2] - c[0])
        y += (c[3] - c[1]) + tam * 0.08
        abajo_texto = y

    # Flecha: sale de debajo del texto y se curva hacia el personaje (mitad derecha).
    inicio = (margen + min(derecha_texto - margen, 260) * 0.5, min(abajo_texto + 30, H - 90))
    fin = (W * 0.60, H * 0.52)
    control = ((inicio[0] + fin[0]) / 2, H - 40)
    flecha(d, inicio, control, fin)

    img.save("portada.jpg", "JPEG", quality=90, optimize=True)
    kb = Path("portada.jpg").stat().st_size / 1024
    print(f"==> portada.jpg lista: «{texto.upper()}», 1280×720, {kb:.0f} KB")


if __name__ == "__main__":
    main()
