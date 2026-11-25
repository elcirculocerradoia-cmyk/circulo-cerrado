"""
Manda a Kaggle una lista de imágenes para que las pinte con su GPU, espera y se las trae.

    python kaggle_lanzar.py --prueba                 # las 20 imágenes de prueba + portada
    python kaggle_lanzar.py --trabajos t.json --salida carpeta/

Necesita (secretos de GitHub): KAGGLE_USERNAME, KAGGLE_KEY y HF_TOKEN.
  - El cuaderno de Kaggle es PRIVADO (is_private) y se llama <usuario>/circulo-pintor.
  - HF_TOKEN va dentro del cuaderno privado (Kaggle no deja poner sus secretos por la API);
    basta un token de Hugging Face de solo lectura.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NOMBRE = "circulo-pintor"


def morir(m):
    print(f"\nERROR: {m}", file=sys.stderr)
    sys.exit(1)


def kaggle(*args, capturar=True):
    p = subprocess.run(["kaggle", *args], capture_output=capturar, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def lanzar(trabajos, salida: Path, semilla=1234, espera_max=110 * 60):
    """trabajos: [(nombre.jpg, prompt, ancho, alto), ...]. Deja las imágenes en salida/."""
    usuario = os.environ.get("KAGGLE_USERNAME")
    for v in ("KAGGLE_USERNAME", "KAGGLE_KEY", "HF_TOKEN"):
        if not os.environ.get(v):
            morir(f"Falta {v}.")
    dir_k = Path(tempfile.mkdtemp())
    cabecera = (f"TRABAJOS = {json.dumps(trabajos, ensure_ascii=False)}\n"
                f"SEMILLA = {int(semilla)}\n"
                f"HF_TOKEN = {json.dumps(os.environ['HF_TOKEN'])}\n")
    cuerpo = (AQUI / "kaggle_pintor.py").read_text(encoding="utf-8")
    (dir_k / "pintor.py").write_text(cabecera + cuerpo, encoding="utf-8")
    (dir_k / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{usuario}/{NOMBRE}", "title": NOMBRE, "code_file": "pintor.py",
        "language": "python", "kernel_type": "script", "is_private": "true",
        "enable_gpu": "true", "enable_internet": "true", "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
    }, indent=1), encoding="utf-8")

    print(f"==> Mandando {len(trabajos)} imágenes a Kaggle ({usuario}/{NOMBRE})", flush=True)
    c, txt = kaggle("kernels", "push", "-p", str(dir_k))
    print("   ", txt.strip().replace(os.environ["HF_TOKEN"], "[token]")[:500], flush=True)
    if c != 0:
        morir("Kaggle no ha aceptado el cuaderno.")

    t0 = time.time()
    estado = ""
    time.sleep(30)
    while time.time() - t0 < espera_max:
        c, txt = kaggle("kernels", "status", f"{usuario}/{NOMBRE}")
        estado = txt.strip().lower()
        if "complete" in estado or "error" in estado or "cancel" in estado:
            break
        print(f"    {int(time.time() - t0) // 60} min: {txt.strip()[-60:]}", flush=True)
        time.sleep(60)
    print(f"==> Kaggle ha terminado: {estado[-80:]} ({(time.time() - t0) / 60:.0f} min)", flush=True)

    salida.mkdir(parents=True, exist_ok=True)
    c, txt = kaggle("kernels", "output", f"{usuario}/{NOMBRE}", "-p", str(salida), "-o")
    if c != 0:
        morir(f"No he podido traer lo pintado: {txt[-400:]}")
    inf = salida / "informe.json"
    informe = json.loads(inf.read_text(encoding="utf-8")) if inf.exists() else {}
    if "complete" not in estado:
        morir(f"El cuaderno de Kaggle ha fallado. Informe: {json.dumps(informe, ensure_ascii=False)[:1500]}")
    return informe


def prueba():
    sys.path.insert(0, str(AQUI))
    from estilo import prompt_de, ESTILO_PORTADA
    from pintor_cf import PERSONAJES_PRUEBA, ESCENAS_PRUEBA, PORTADA_PRUEBA
    trabajos = [[f"{i:02d}.jpg", prompt_de(d, PERSONAJES_PRUEBA, [q for q in quien.split(",") if q]), 1024, 576]
                for i, (quien, d) in enumerate(ESCENAS_PRUEBA, 1)]
    trabajos.append(["portada-base.jpg", prompt_de(PORTADA_PRUEBA, estilo=ESTILO_PORTADA), 768, 768])
    salida = AQUI.parent / "pruebas" / "imagenes-kaggle"
    informe = lanzar(trabajos, salida)
    print(json.dumps(informe, indent=1, ensure_ascii=False))
    media = informe.get("media_s_por_imagen")
    if media:
        print(f"==> {media:.1f} s por imagen → 150 imágenes ≈ {150 * media / 60:.0f} min de GPU "
              f"(+ {informe['fases'].get('bajar_modelo', 0) / 60:.0f} min bajando el modelo).")
    # La portada de prueba montada
    tmp = salida / "portada"
    (tmp / "imagenes").mkdir(parents=True, exist_ok=True)
    base = salida / "imagenes" / "portada-base.jpg"
    if base.exists():
        (tmp / "imagenes" / "portada.jpg").write_bytes(base.read_bytes())
        (tmp / "resumen.json").write_text(json.dumps({"portada": {"texto": "No Mires"}}), encoding="utf-8")
        subprocess.run([sys.executable, str(AQUI / "portada.py")], cwd=tmp, check=False)


if __name__ == "__main__":
    if "--prueba" in sys.argv:
        prueba()
    else:
        print(__doc__)
