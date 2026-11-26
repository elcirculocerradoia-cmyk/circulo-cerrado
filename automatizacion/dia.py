"""
El vídeo del día de Círculo Cerrado. Lo lanza GitHub Actions (.github/workflows/video.yml)
cada día a las 9:45 de Madrid; también se puede lanzar en un PC con todo instalado.

    python3 automatizacion/dia.py                 # hace el vídeo y lo sube programado
    SIN_SUBIR=1 python3 automatizacion/dia.py      # lo hace y no lo sube
    IDEA="..." python3 automatizacion/dia.py       # con la historia que tú digas

  1. Claude (Sonnet, plan Pro) escribe la historia: escenas.json + resumen.json.   guion.sh
  2. Gemini pone la voz por trozos y whisper dice dónde empieza cada escena.        voz.py
  3. FLUX.1-schnell en la GPU de Kaggle pinta ~150 imágenes + la portada.    kaggle_lanzar.py
  4. ffmpeg monta el vídeo con zoom lento en cada imagen.                           montaje.py
  5. La portada con el texto y la flecha.                                           portada.py
  6. Lo sube a YouTube privado y programado (solo si todo lo anterior salió bien).  subir.mjs

Deja todo en salida/AAAA-MM-DD/ (con dia.log) y apunta una línea en el historial.
Variables: CLAUDE_CODE_OAUTH_TOKEN, GEMINI_API_KEY, KAGGLE_USERNAME, KAGGLE_KEY, HF_TOKEN,
YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (las de YouTube solo para subir).
"""

import datetime
import json
import os
import subprocess
import sys
import zoneinfo
from pathlib import Path

AUTO = Path(__file__).resolve().parent
RAIZ = AUTO.parent
sys.path.insert(0, str(AUTO))
from estilo import prompt_de, ESTILO_PORTADA  # noqa: E402
from kaggle_lanzar import lanzar  # noqa: E402

ANCHO_K, ALTO_K = 1024, 576    # 16:9, múltiplos de 64

CANAL = "circulo-cerrado"

# Líneas de los pasos que se pueden enseñar en el registro público: empiezan así y no
# llevan nada del guion ni del título (voz, montaje y portada solo dan cifras).
PUBLICAS = ("==>", "####", "  trozo ", "  Gemini ", "  Cloudflare ", "  AVISO", "AVISO",
            "  Subiendo", "  Portada puesta", "  La subida", "ERROR")


def es_publica(linea: str) -> bool:
    if "portada.jpg lista" in linea:      # lleva el texto de la portada
        return False
    return linea.startswith(PUBLICAS)


def main():
    hoy = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Madrid"))
    canales = AUTO / "canales"
    historial = canales / f"{CANAL}-historial.md"
    programados = canales / f"{CANAL}-programados.json"
    carpeta = RAIZ / "salida" / f"{hoy:%Y-%m-%d}"
    if carpeta.exists():
        carpeta.rename(carpeta.with_name(f"{carpeta.name}-{hoy:%H%M%S}-anterior"))
    carpeta.mkdir(parents=True)
    flog = open(carpeta / "dia.log", "w", encoding="utf-8")

    def log(t, publico=True):
        # Todo va a dia.log (que viaja cifrado). A la pantalla, que en GitHub Actions es
        # PÚBLICA, solo lo que no cuenta nada del vídeo: títulos de paso, avisos y cifras.
        flog.write(t)
        flog.flush()
        if publico:
            print(t, end="", flush=True)

    env = dict(os.environ, TZ="Europe/Madrid", HISTORIAL=str(historial), PYTHONUNBUFFERED="1")

    def paso(nombre, cmd):
        log(f"\n########## {nombre} ##########\n")
        p = subprocess.Popen(cmd, cwd=carpeta, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1, encoding="utf-8")
        for linea in p.stdout:
            log(linea, publico=es_publica(linea))
        if p.wait() != 0:
            log(f"\nERROR: ha fallado «{nombre}». Todo lo hecho está en {carpeta}\n")
            sys.exit(1)

    log(f"Empieza el día {hoy:%Y-%m-%d %H:%M} (Madrid) en {carpeta}\n")
    paso("1. Guion (Claude)", ["bash", str(AUTO / "guion.sh")])
    paso("2. Voz (Gemini) y tiempos (whisper)", [sys.executable, str(AUTO / "voz.py")])

    log("\n########## 3. Imágenes (FLUX en la GPU gratis de Kaggle) ##########\n")
    e = json.loads((carpeta / "escenas.json").read_text(encoding="utf-8"))
    r = json.loads((carpeta / "resumen.json").read_text(encoding="utf-8"))
    pers = e.get("personajes", {})
    # [nombre, descripción completa, ancho, alto]: 16:9 directo para el vídeo; la portada,
    # cuadrada (portada.py la pega a la izquierda de la miniatura).
    trabajos = [[f"{i:03d}.jpg", prompt_de(s["imagen"], pers, s.get("quien")), ANCHO_K, ALTO_K]
                for i, s in enumerate(e["escenas"], 1)]
    port = r.get("portada", {})
    trabajos.append(["portada.jpg", prompt_de(port.get("imagen", "a terrified young man, chest-up"),
                                              estilo=ESTILO_PORTADA), 768, 768])
    (carpeta / "prompts.json").write_text(json.dumps(trabajos, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"==> Kaggle pinta {len(trabajos)} imágenes (semilla {hoy:%Y%m%d})\n")
    informe = lanzar(trabajos, carpeta, semilla=int(f"{hoy:%Y%m%d}"), espera_max=240 * 60)
    # Las que falten (Kaggle descarta las que salen negras): la de al lado.
    imgs = carpeta / "imagenes"
    faltan = [t[0] for t in trabajos[:-1] if not (imgs / t[0]).exists()]
    if len(faltan) > max(1, len(trabajos) // 10):
        log(f"\nERROR: Kaggle no ha pintado {len(faltan)} de {len(trabajos)} imágenes.\n")
        sys.exit(1)
    hechas = sorted(x.name for x in imgs.glob("[0-9][0-9][0-9].jpg"))
    for f in faltan:
        cerca = min(hechas, key=lambda h: abs(int(h[:3]) - int(f[:3])))
        (imgs / f).write_bytes((imgs / cerca).read_bytes())
    if faltan:
        log(f"  AVISO: {len(faltan)} imágenes sustituidas por la de al lado.\n")
    medida = {k: informe.get(k) for k in ("gpus", "s_por_imagen_efectivo", "total_s", "fases", "errores")}
    log(f"==> Listas: {informe.get('s_por_imagen_efectivo')} s por imagen con {informe.get('gpus')} GPU; "
        f"Kaggle en total {(informe.get('total_s') or 0) / 60:.0f} min.\n")
    (carpeta / "medidas.json").write_text(json.dumps(medida, indent=1, ensure_ascii=False), encoding="utf-8")

    paso("4. Montaje (ffmpeg)", [sys.executable, str(AUTO / "montaje.py")])
    paso("5. Portada", [sys.executable, str(AUTO / "portada.py")])

    with open(historial, "a", encoding="utf-8") as h:
        h.write(f"- {hoy:%Y-%m-%d} · {r.get('mundo', '?')} · {r['titulo']} — {r.get('tema', '')}\n")

    if os.environ.get("SIN_SUBIR"):
        log("\nSIN_SUBIR: el vídeo se queda hecho, sin subir.\n")
    elif not os.environ.get("YT_REFRESH_TOKEN"):
        log("\nSin YT_REFRESH_TOKEN: no subo nada.\n")
    else:
        paso("6. Subir a YouTube (programado)",
             ["node", str(AUTO / "subir.mjs"), "--dir", str(carpeta), "--canal", CANAL,
              "--programados", str(programados)])
    log("\nHecho: el vídeo y todo lo demás van en el paquete cifrado.\n")
    flog.close()


if __name__ == "__main__":
    main()
