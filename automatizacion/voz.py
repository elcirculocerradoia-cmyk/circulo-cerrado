"""
Paso 2: la voz del vídeo y en qué segundo empieza cada escena.

    cd CARPETA_DEL_VIDEO && python3 .../automatizacion/voz.py

Lee escenas.json y deja:
    assets/voz.wav     la narración entera
    tiempos.json       [{"escena": 1, "inicio": 0.0, "fin": 4.8}, ...]

Cómo:
  1. Gemini TTS (gemini-3.8-flash-tts, voz Charon, como Curiosidades) no lee 12 minutos
     de una vez, así que se graba en TROZOS de párrafos enteros (~350 palabras, ~2 min)
     y se pegan con una pausa corta entre ellos.
  2. whisper (faster-whisper, en el procesador) escucha la voz y da el segundo de cada
     palabra.
  3. Se casan las palabras del guion con las que oyó whisper para saber dónde empieza
     cada escena. Donde no casan (números, palabras raras), se reparte por letras.

Necesita GEMINI_API_KEY. Opcional: VOZ, ESTILO, MODELO_VOZ.
"""

import base64
import difflib
import io
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import wave
from pathlib import Path

VOZ = os.environ.get("VOZ", "Charon")
MODELO_VOZ = os.environ.get("MODELO_VOZ", "gemini-3.8-flash-tts")
ESTILO = os.environ.get("ESTILO", (
    "Narrador de historias en español de España. Voz grave, pausada y cercana, "
    "como si le contara un secreto al oído a quien escucha. Tensión contenida. "
    "Frases cortas con pausas breves entre ellas. Sin gritar y sin voz de anuncio."
))
PALABRAS_TROZO = int(os.environ.get("PALABRAS_TROZO", "350"))
PAUSA_TROZOS = 0.5      # segundos de silencio entre trozos
COLA = 1.5              # segundos de imagen después de la última palabra
MIN_S, MAX_S = 9 * 60, 16 * 60


def morir(m):
    print(f"\nERROR: {m}", file=sys.stderr)
    sys.exit(1)


# ── 1. Gemini ────────────────────────────────────────────────────────────────
def gemini(texto: str) -> bytes:
    """Devuelve un WAV. Reintenta si Gemini dice que va saturado (429/5xx)."""
    clave = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not clave:
        morir("Falta GEMINI_API_KEY.")
    moderno = MODELO_VOZ.startswith("gemini-3.8-")
    contenido = {"type": "text",
                 "text": texto if moderno else f"Read the following text with this delivery: {ESTILO}\n\n{texto}"}
    if moderno:
        contenido["annotations"] = [{"type": "speech_metadata", "style": ESTILO}]
    cuerpo = json.dumps({
        "model": MODELO_VOZ,
        "input": [{"type": "user_input", "content": [contenido]}],
        "response_format": {"type": "audio", "mime_type": "audio/wav"} if moderno else {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": VOZ}]},
        "store": False,
    }).encode()
    espera = 20
    for intento in range(1, 7):
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/interactions", data=cuerpo,
            headers={"Content-Type": "application/json", "x-goog-api-key": clave})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                datos = json.load(r)
            break
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="replace")[:500].replace(clave, "[clave]")
            if e.code in (429, 500, 502, 503, 504) and intento < 6:
                print(f"  Gemini {e.code}; reintento {intento} en {espera} s", flush=True)
                time.sleep(espera)
                espera = min(espera * 2, 180)
                continue
            morir(f"Gemini TTS HTTP {e.code}: {detalle}")
        except (urllib.error.URLError, TimeoutError) as e:
            if intento < 6:
                print(f"  Gemini sin respuesta ({e}); reintento {intento} en {espera} s", flush=True)
                time.sleep(espera)
                continue
            morir(f"Gemini no responde: {e}")
    if datos.get("status") != "completed":
        morir(f"Gemini no ha terminado ({datos.get('status')}).")
    audios = [c for s in datos.get("steps", []) if s.get("type") == "model_output"
              for c in s.get("content", []) if c.get("type") == "audio"]
    if len(audios) != 1:
        morir("Gemini no ha devuelto un único audio.")
    b = base64.b64decode(audios[0]["data"])
    tipo = (audios[0].get("mime_type") or "").lower()
    if tipo.startswith("audio/l16"):           # modelos viejos: PCM a pelo
        rate = int(re.search(r"rate=(\d+)", tipo).group(1))
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b)
        b = out.getvalue()
    if b[:4] != b"RIFF":
        morir("Gemini ha devuelto un audio que no es WAV.")
    return b


def trozos(escenas):
    """Párrafos enteros juntos hasta ~PALABRAS_TROZO palabras."""
    parrafos = {}
    for s in escenas:
        parrafos.setdefault(s["parrafo"], []).append(s["texto"].strip())
    salida, actual = [], []
    for textos in parrafos.values():
        p = " ".join(textos)
        if actual and len(" ".join(actual + [p]).split()) > PALABRAS_TROZO:
            salida.append("\n\n".join(actual))
            actual = []
        actual.append(p)
    if actual:
        salida.append("\n\n".join(actual))
    return salida


def a_pcm(wav: bytes, rate=24000) -> bytes:
    """Cualquier WAV → PCM 16 bits mono a `rate`, con ffmpeg (por si un trozo viene distinto)."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1",
                        "-ar", str(rate), "pipe:1"], input=wav, capture_output=True)
    if p.returncode:
        morir(f"ffmpeg no ha podido leer un trozo de voz: {p.stderr.decode()[:300]}")
    return p.stdout


# ── 2 y 3. whisper y casar escenas con palabras ─────────────────────────────
def normal(t: str) -> list[str]:
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", t)


def escuchar(wav: Path):
    from faster_whisper import WhisperModel
    modelo = WhisperModel(os.environ.get("WHISPER", "small"), device="cpu", compute_type="int8",
                          cpu_threads=os.cpu_count() or 4)
    partes, _ = modelo.transcribe(str(wav), language="es", word_timestamps=True,
                                  vad_filter=False, beam_size=1)
    palabras = []
    for p in partes:
        for w in p.words or []:
            for tok in normal(w.word):
                palabras.append((tok, w.start, w.end))
    return palabras


def casar(escenas, oidas, duracion):
    """El segundo en que empieza cada escena."""
    guion, de_escena = [], []
    for i, s in enumerate(escenas):
        for tok in normal(s["texto"]):
            guion.append(tok)
            de_escena.append(i)
    sm = difflib.SequenceMatcher(None, guion, [w[0] for w in oidas], autojunk=False)
    momento = [None] * len(guion)          # segundo de cada palabra del guion, si se oyó
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            momento[a + k] = oidas[b + k][1]

    # Lo que no se oyó, se rellena repartiendo por posición entre los vecinos que sí.
    conocidos = [(i, t) for i, t in enumerate(momento) if t is not None]
    if len(conocidos) < len(guion) * 0.5:
        print(f"  AVISO: whisper solo casa {len(conocidos)}/{len(guion)} palabras; reparto por letras.")
        conocidos = []
    if not conocidos:
        conocidos = [(0, 0.0), (len(guion) - 1, duracion - COLA)]
    if conocidos[0][0] != 0:
        conocidos.insert(0, (0, max(0.0, conocidos[0][1] - 0.35 * conocidos[0][0])))
    for (i0, t0), (i1, t1) in zip(conocidos, conocidos[1:]):
        for i in range(i0 + 1, i1):
            momento[i] = t0 + (t1 - t0) * (i - i0) / (i1 - i0)
    ult_i, ult_t = conocidos[-1]
    for i in range(ult_i + 1, len(guion)):
        momento[i] = ult_t + 0.35 * (i - ult_i)
    momento[0] = momento[0] if momento[0] is not None else 0.0

    inicios = []
    for e in range(len(escenas)):
        idx = de_escena.index(e) if e in de_escena else None
        inicios.append(momento[idx] if idx is not None else (inicios[-1] if inicios else 0.0))
    inicios[0] = 0.0
    # Que nunca vaya hacia atrás y que cada imagen dure al menos 1,2 s.
    for i in range(1, len(inicios)):
        inicios[i] = max(inicios[i], inicios[i - 1] + 1.2)
    fin_total = duracion + COLA
    tiempos = []
    for i, ini in enumerate(inicios):
        fin = inicios[i + 1] if i + 1 < len(inicios) else fin_total
        tiempos.append({"escena": i + 1, "inicio": round(ini, 3), "fin": round(min(fin, fin_total), 3)})
    return tiempos, len([m for m in sm.get_matching_blocks()]), len(conocidos)


def main():
    e = json.loads(Path("escenas.json").read_text(encoding="utf-8"))
    escenas = e["escenas"]
    Path("assets").mkdir(exist_ok=True)

    lista = trozos(escenas)
    print(f"==> Voz con Gemini ({MODELO_VOZ}, voz {VOZ}) en {len(lista)} trozos", flush=True)
    rate = 24000
    silencio = b"\0\0" * int(rate * PAUSA_TROZOS)
    pcm = b""
    for i, t in enumerate(lista, 1):
        t0 = time.time()
        wav = gemini(t)
        Path(f"assets/trozo-{i:02d}.wav").write_bytes(wav)
        trozo = a_pcm(wav, rate)
        pcm += (silencio if pcm else b"") + trozo
        print(f"  trozo {i}/{len(lista)}: {len(t.split())} palabras → {len(trozo) / 2 / rate:.1f} s "
              f"({time.time() - t0:.0f} s)", flush=True)
        if i < len(lista):
            time.sleep(3)   # sin prisa: el plan gratis de Gemini limita las peticiones por minuto
    with wave.open("assets/voz.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    duracion = len(pcm) / 2 / rate
    print(f"==> Voz lista: assets/voz.wav, {duracion / 60:.1f} min", flush=True)
    if not (MIN_S <= duracion <= MAX_S):
        morir(f"La voz dura {duracion / 60:.1f} min y tiene que durar entre {MIN_S // 60} y {MAX_S // 60}.")

    print("==> whisper escucha la voz para saber dónde empieza cada escena", flush=True)
    t0 = time.time()
    oidas = escuchar(Path("assets/voz.wav"))
    tiempos, _, casadas = casar(escenas, oidas, duracion)
    Path("tiempos.json").write_text(json.dumps(tiempos, indent=1), encoding="utf-8")
    durs = [t["fin"] - t["inicio"] for t in tiempos]
    print(f"  {len(oidas)} palabras oídas, {casadas} casadas con el guion ({time.time() - t0:.0f} s)")
    print(f"  {len(tiempos)} imágenes: {min(durs):.1f}-{max(durs):.1f} s, "
          f"{sum(durs) / len(durs):.1f} s de media")
    print("==> tiempos.json listo")


if __name__ == "__main__":
    main()
