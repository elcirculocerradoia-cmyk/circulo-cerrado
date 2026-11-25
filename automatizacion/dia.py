"""
El vídeo del día de Círculo Cerrado. Lo lanza GitHub Actions (.github/workflows/video.yml)
cada día a las 9:45 de Madrid; también se puede lanzar en un PC con todo instalado.

    python3 automatizacion/dia.py                 # hace el vídeo y lo sube programado
    SIN_SUBIR=1 python3 automatizacion/dia.py      # lo hace y no lo sube
    IDEA="..." python3 automatizacion/dia.py       # con la historia que tú digas

  1. Claude (Sonnet, plan Pro) escribe la historia: escenas.json + resumen.json.   guion.sh
  2. Gemini pone la voz por trozos y whisper dice dónde empieza cada escena.        voz.py
  3. FLUX.1-schnell en Cloudflare pinta ~150 imágenes + la de la portada.           pintor_cf.py
  4. ffmpeg monta el vídeo con zoom lento en cada imagen.                           montaje.py
  5. La portada con el texto y la flecha.                                           portada.py
  6. Lo sube a YouTube privado y programado (solo si todo lo anterior salió bien).  subir.mjs

Deja todo en salida/AAAA-MM-DD/ (con dia.log) y apunta una línea en el historial.
Variables: CLAUDE_CODE_OAUTH_TOKEN, GEMINI_API_KEY, CF_ACCOUNT_ID, CF_API_TOKEN,
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
from pintor_cf import pintar, SinNeuronas  # noqa: E402

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

    log("\n########## 3. Imágenes (FLUX en Cloudflare) ##########\n")
    e = json.loads((carpeta / "escenas.json").read_text(encoding="utf-8"))
    r = json.loads((carpeta / "resumen.json").read_text(encoding="utf-8"))
    pers = e.get("personajes", {})
    prompts = [prompt_de(s["imagen"], pers, s.get("quien")) for s in e["escenas"]]
    port = r.get("portada", {})
    # La portada va aparte: un retrato detallado (no el muñeco negro), con su propia descripción.
    prompts.append(prompt_de(port.get("imagen", "a terrified young man, chest-up"), estilo=ESTILO_PORTADA))
    (carpeta / "prompts.json").write_text(json.dumps(prompts, indent=1, ensure_ascii=False), encoding="utf-8")
    destinos = [carpeta / "imagenes" / f"{i:03d}.jpg" for i in range(1, len(prompts))]
    destinos.append(carpeta / "imagenes" / "portada.jpg")
    from estilo import BASE, PERSONAS
    simples = [prompt_de(s["imagen"], estilo=f"{BASE}, {PERSONAS}" if s.get("quien") else None)
               for s in e["escenas"]] + [None]
    log(f"==> FLUX pinta {len(prompts)} imágenes (semilla {hoy:%Y%m%d})\n")
    try:
        medida = pintar(prompts, destinos, semilla=int(f"{hoy:%Y%m%d}"), simples=simples)
    except SinNeuronas as x:
        log(f"\nERROR: se ha acabado lo gratis de hoy en Cloudflare (10.000 neuronas): {x}\n")
        sys.exit(1)
    except RuntimeError as x:
        log(f"\nERROR: {x}\n")
        sys.exit(1)
    if medida["fallos"]:
        log(f"  AVISO: {len(medida['fallos'])} imágenes rechazadas, sustituidas por la de al lado.\n")
    log(f"==> Listas en {medida['segundos']:.0f} s. Tamaño original: {medida['tamano_original']}. "
        f"Semilla: {'sí' if medida['con_semilla'] else 'no'}.\n")
    (carpeta / "medidas.json").write_text(json.dumps(medida, indent=1), encoding="utf-8")

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
