"""
Paso 5: la portada (miniatura) de YouTube, 1280×720, como la de referencia (25/11):

    ┌──────────────────────────────────────┐
    │            ↙~~~~~~~                  │   fondo BLANCO
    │  [retrato del        Muerto          │   primera palabra en ROJO
    │   protagonista]      En Vida         │   el resto en NEGRO
    └──────────────────────────────────────┘   flecha negra fina, dibujada a mano

    cd CARPETA_DEL_VIDEO && python3 .../automatizacion/portada.py

Parte de imagenes/portada.jpg: un retrato CUADRADO sobre fondo blanco que pinta FLUX
(pintor_cf.py no la recorta). Se pega a la izquierda y el texto va a la derecha.
El texto sale de resumen.json → portada.texto. Deja portada.jpg.
"""

import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BLANCO = (255, 255, 255)
ROJO = (226, 35, 38)
NEGRO = (17, 17, 17)

FUENTES = [
    os.environ.get("FUENTE_PORTADA", ""),
    str(Path.home() / ".fonts" / "PatrickHand-Regular.ttf"),
    "/root/.fonts/PatrickHand-Regular.ttf",
    "C:/Windows/Fonts/segoepr.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def fuente(tam):
    for f in FUENTES:
        if f and Path(f).exists():
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default(tam)


def lineas_de(texto: str):
    """«Muerto En Vida» → [('Muerto', rojo), ('En Vida', negro)]."""
    p = texto.strip().split()
    if not p:
        p = ["Es", "Una", "Trampa"]
    p = [w[:1].upper() + w[1:] for w in p]
    if len(p) == 1:
        return [(p[0], ROJO)]
    return [(p[0], ROJO), (" ".join(p[1:]), NEGRO)]


def tam_que_cabe(d, lineas, ancho, alto):
    for tam in range(200, 40, -4):
        f = fuente(tam)
        cajas = [d.textbbox((0, 0), t, font=f) for t, _ in lineas]
        an = max(c[2] - c[0] for c in cajas)
        al = sum(c[3] - c[1] for c in cajas) + (len(lineas) - 1) * tam * 0.18
        if an <= ancho and al <= alto:
            return tam
    return 40


def curva(p0, p1, p2, n=50):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])
            for t in [i / n for i in range(n + 1)]]


def flecha(d, p0, p1, p2, grosor=7):
    """Flecha negra fina con punta abierta (dos rayas), como dibujada con rotulador."""
    pts = curva(p0, p1, p2)
    d.line(pts, fill=NEGRO, width=grosor, joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0])
    largo = grosor * 5
    for giro in (math.radians(35), -math.radians(35)):
        x = p2[0] - largo * math.cos(ang + giro)
        y = p2[1] - largo * math.sin(ang + giro)
        d.line([(x, y), p2], fill=NEGRO, width=grosor)
    for p in (p2, pts[0]):           # puntas redondeadas
        d.ellipse([p[0] - grosor / 2, p[1] - grosor / 2, p[0] + grosor / 2, p[1] + grosor / 2], fill=NEGRO)


def main():
    r = json.loads(Path("resumen.json").read_text(encoding="utf-8"))
    texto = (r.get("portada") or {}).get("texto") or "Es Una Trampa"
    base = Path("imagenes/portada.jpg")
    if not base.exists():
        base = sorted(Path("imagenes").glob("[0-9][0-9][0-9].jpg"))[0]

    lienzo = Image.new("RGB", (W, H), BLANCO)
    retrato = Image.open(base).convert("RGB")
    # Cuadrado al alto de la miniatura, pegado a la izquierda.
    lado = H
    r_w, r_h = retrato.size
    escala = lado / min(r_w, r_h)
    retrato = retrato.resize((round(r_w * escala), round(r_h * escala)), Image.LANCZOS)
    x0 = (retrato.width - lado) // 2
    retrato = retrato.crop((x0, 0, x0 + lado, lado))
    lienzo.paste(retrato, (0, 0))
    d = ImageDraw.Draw(lienzo)

    # Texto en la franja derecha, un poco por debajo del centro (arriba va la flecha).
    izq, der = 700, W - 40
    lineas = lineas_de(texto)
    tam = tam_que_cabe(d, lineas, der - izq, H * 0.5)
    f = fuente(tam)
    cajas = [d.textbbox((0, 0), t, font=f) for t, _ in lineas]
    alto = sum(c[3] - c[1] for c in cajas) + (len(lineas) - 1) * tam * 0.18
    y = H * 0.58 - alto / 2
    arriba_texto = y
    for (t, color), c in zip(lineas, cajas):
        an = c[2] - c[0]
        x = izq + ((der - izq) - an) / 2
        d.text((x - c[0], y - c[1]), t, font=f, fill=color)
        y += (c[3] - c[1]) + tam * 0.18

    # Flecha: sale de encima del texto y se curva hacia la cara del retrato.
    inicio = (izq + (der - izq) * 0.55, arriba_texto - 35)
    fin = (lado - 60, H * 0.28)
    control = ((inicio[0] + fin[0]) / 2 + 40, fin[1] - 120)
    flecha(d, inicio, control, fin, grosor=8)

    lienzo.save("portada.jpg", "JPEG", quality=92, optimize=True)
    kb = Path("portada.jpg").stat().st_size / 1024
    print(f"==> portada.jpg lista: «{texto}», 1280×720, {kb:.0f} KB")


if __name__ == "__main__":
    main()
