"""
Comprueba lo que ha escrito Claude (escenas.json y resumen.json) y, si está bien,
escribe guion.txt (el texto entero, por párrafos).

    python3 comprobar_guion.py CARPETA_DEL_VIDEO

Sale con 0 y dice «TODO BIEN» si se puede seguir; si no, sale con 1 y dice qué arreglar.
Lo lanza Claude mientras escribe (para corregirse) y guion.sh al final (para no seguir
con un guion roto).
"""

import json
import re
import sys
from pathlib import Path

PALABRAS_MIN, PALABRAS_MAX = 1700, 2100
ESCENA_MIN, ESCENA_MAX = 10, 15         # palabras por escena (≈ 4-6 s de voz a 2,3 palabras/s)
ESCENAS_MIN, ESCENAS_MAX = 140, 230
CAMARAS = {"acercar", "alejar", "izquierda", "derecha", "arriba"}
RELLENO = {"#viral", "#fyp", "#parati", "#foryou", "#shorts"}


def palabras(t: str) -> int:
    return len(re.findall(r"\S+", t))


def comprobar(carpeta: Path) -> list[str]:
    fallos = []
    try:
        e = json.loads((carpeta / "escenas.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ["Falta escenas.json."]
    except json.JSONDecodeError as x:
        return [f"escenas.json no es JSON válido: {x}"]
    try:
        r = json.loads((carpeta / "resumen.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ["Falta resumen.json."]
    except json.JSONDecodeError as x:
        return [f"resumen.json no es JSON válido: {x}"]

    # ── escenas.json ────────────────────────────────────────────────────────
    pers = e.get("personajes") or {}
    esc = e.get("escenas") or []
    if "tu" not in pers:
        fallos.append("En 'personajes' falta el protagonista con la clave 'tu'.")
    for k, d in pers.items():
        if palabras(d) > 30:
            fallos.append(f"El personaje '{k}' tiene {palabras(d)} palabras de descripción (máximo 30).")
    if not (ESCENAS_MIN <= len(esc) <= ESCENAS_MAX):
        fallos.append(f"Hay {len(esc)} escenas y tienen que ser entre {ESCENAS_MIN} y {ESCENAS_MAX} (≈180).")
    total, anterior = 0, 0
    cortas, largas = [], []
    for i, s in enumerate(esc, 1):
        t = (s.get("texto") or "").strip()
        img = (s.get("imagen") or "").strip()
        p = s.get("parrafo")
        n = palabras(t)
        total += n
        if not t:
            fallos.append(f"La escena {i} no tiene 'texto'.")
        elif n < ESCENA_MIN:
            cortas.append(i)
        elif n > ESCENA_MAX:
            largas.append(i)
        if not img:
            fallos.append(f"La escena {i} no tiene 'imagen'.")
        elif palabras(img) > 35:
            fallos.append(f"La imagen de la escena {i} tiene {palabras(img)} palabras (máximo 35).")
        if re.search(r"\d", t):
            fallos.append(f"La escena {i} tiene cifras: escribe los números con letras («{t[:50]}…»).")
        if not isinstance(p, int) or p < anterior:
            fallos.append(f"La escena {i}: 'parrafo' tiene que ser un número que no baja.")
        else:
            anterior = p
        if s.get("camara") and s["camara"] not in CAMARAS:
            fallos.append(f"La escena {i}: 'camara' tiene que ser una de {sorted(CAMARAS)}.")
        for q in s.get("quien") or []:
            if q not in pers:
                fallos.append(f"La escena {i} usa el personaje '{q}', que no está en 'personajes'.")
        if len(s.get("quien") or []) > 2:
            fallos.append(f"La escena {i} tiene más de dos personajes.")
    # Unas pocas fuera de rango se toleran (una frase corta de impacto queda bien).
    if len(cortas) > len(esc) // 10:
        fallos.append(f"Demasiadas escenas con menos de {ESCENA_MIN} palabras: {cortas[:15]}")
    if largas:
        fallos.append(f"Escenas con más de {ESCENA_MAX} palabras (pártelas): {largas[:15]}")
    if not (PALABRAS_MIN <= total <= PALABRAS_MAX):
        fallos.append(f"El guion tiene {total} palabras y tiene que tener entre {PALABRAS_MIN} y {PALABRAS_MAX}.")
    # Párrafos de tamaño razonable (la voz se graba por párrafos).
    por_parrafo = {}
    for s in esc:
        por_parrafo.setdefault(s.get("parrafo"), 0)
        por_parrafo[s.get("parrafo")] += 1
    grandes = [p for p, n in por_parrafo.items() if n > 25]
    if grandes:
        fallos.append(f"Párrafos con más de 25 escenas (pártelos): {grandes}")

    # ── resumen.json ────────────────────────────────────────────────────────
    titulo = (r.get("titulo") or "").strip()
    if not titulo:
        fallos.append("resumen.json: falta 'titulo'.")
    elif len(titulo) > 90:
        fallos.append(f"resumen.json: el título tiene {len(titulo)} caracteres (máximo 90).")
    if not (r.get("descripcion") or "").strip():
        fallos.append("resumen.json: falta 'descripcion'.")
    elif "ficción" not in r["descripcion"]:
        fallos.append("resumen.json: la descripción tiene que llevar la línea «Historia de ficción…».")
    tags = [h if h.startswith("#") else f"#{h}" for h in (r.get("hashtags") or [])]
    if not (3 <= len(tags) <= 5):
        fallos.append(f"resumen.json: {len(tags)} hashtags; tienen que ser de 3 a 5.")
    if "#circulocerrado" not in tags:
        fallos.append("resumen.json: falta #circulocerrado.")
    for t in tags:
        if t != t.lower() or re.search(r"[áéíóúüñ\s]", t) or t in RELLENO:
            fallos.append(f"resumen.json: el hashtag {t} no vale (minúsculas, sin tildes, nada de relleno ni #shorts).")
    port = r.get("portada") or {}
    if not port.get("texto") or not (1 <= len(port["texto"].split()) <= 3):
        fallos.append("resumen.json: portada.texto tiene que ser de 1 a 3 palabras.")
    if not port.get("imagen"):
        fallos.append("resumen.json: falta portada.imagen.")
    for k in ("tema", "mundo"):
        if not (r.get(k) or "").strip():
            fallos.append(f"resumen.json: falta '{k}'.")
    return fallos


def main():
    carpeta = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    fallos = comprobar(carpeta)
    if fallos:
        print("HAY QUE ARREGLAR:")
        for f in fallos:
            print(f"  - {f}")
        sys.exit(1)
    e = json.loads((carpeta / "escenas.json").read_text(encoding="utf-8"))
    parrafos = {}
    for s in e["escenas"]:
        parrafos.setdefault(s["parrafo"], []).append(s["texto"].strip())
    (carpeta / "guion.txt").write_text("\n\n".join(" ".join(v) for v in parrafos.values()) + "\n",
                                      encoding="utf-8")
    total = sum(palabras(s["texto"]) for s in e["escenas"])
    print(f"{len(e['escenas'])} escenas, {len(parrafos)} párrafos, {total} palabras "
          f"(≈{total / 2.3 / 60:.1f} min de voz).")
    print("TODO BIEN")


if __name__ == "__main__":
    main()
