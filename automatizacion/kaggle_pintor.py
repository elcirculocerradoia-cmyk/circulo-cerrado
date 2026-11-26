"""
Lo que se ejecuta DENTRO de Kaggle, con su GPU gratis: pinta las imágenes con FLUX.1-schnell.
No se lanza a mano: kaggle_lanzar.py le pega delante la lista de trabajos (TRABAJOS, SEMILLA,
HF_TOKEN) y lo sube a Kaggle con `kaggle kernels push`.

Kaggle da DOS GPU T4 (16 GB cada una). Se reparten las imágenes entre las dos, cada una en
su propio proceso, y cada proceso:
  1.º textos: T5 + CLIP convierten sus descripciones en números; se borran.
  2.º dibujo: FLUX a 5 bits (GGUF de city96, 8,3 GB) + el VAE pintan una a una.

Primera prueba (26/11): en bf16 una T4 tardaba 77 s por imagen (la T4 no tiene bf16 de
verdad). Ahora se prueba primero fp16, que la T4 sí hace rápido; si salen negras, bf16.

Deja en /kaggle/working: imagenes/<nombre>.jpg e informe.json (tiempos y errores).
"""
# ── (aquí kaggle_lanzar.py pega TRABAJOS, SEMILLA y HF_TOKEN) ──

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SALIDA = Path("/kaggle/working")
INFORME = SALIDA / "informe.json"


def guardar(informe):
    INFORME.write_text(json.dumps(informe, indent=1, ensure_ascii=False))


# Lo que hace cada GPU, como programa aparte (Kaggle ejecuta este archivo como un cuaderno y
# ahí repartir con multiprocessing falla): se escribe a /tmp y se lanza uno por GPU.
TRABAJADOR = r'''
import json, os, sys, time
from pathlib import Path
args = json.loads(Path(sys.argv[1]).read_text())
gpu, lote, base, gguf, semilla, salida_json = (args["gpu"], args["lote"], args["base"], args["gguf"],
                                               args["semilla"], args["salida"])
SALIDA = Path("/kaggle/working")
os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import gc
import torch
from diffusers import FluxPipeline, FluxTransformer2DModel, GGUFQuantizationConfig

res = {"gpu": gpu, "fases": {}, "imagenes": {}, "errores": []}
for tipo in (torch.float16, torch.bfloat16):
    pipe = tr = numeros = None
    try:
        t = time.time()
        pipe = FluxPipeline.from_pretrained(base, transformer=None, vae=None, torch_dtype=tipo).to("cuda")
        numeros = []
        with torch.no_grad():
            for nombre, prompt, w, h in lote:
                pe, ppe, _ = pipe.encode_prompt(prompt=prompt, prompt_2=prompt, max_sequence_length=256)
                numeros.append((pe.cpu(), ppe.cpu()))
        pipe = None
        gc.collect()
        torch.cuda.empty_cache()
        res["fases"][f"textos_{tipo}"] = round(time.time() - t, 1)

        t = time.time()
        tr = FluxTransformer2DModel.from_single_file(
            gguf, quantization_config=GGUFQuantizationConfig(compute_dtype=tipo),
            torch_dtype=tipo, config=base, subfolder="transformer")
        pipe = FluxPipeline.from_pretrained(base, transformer=tr, text_encoder=None, text_encoder_2=None,
                                            tokenizer=None, tokenizer_2=None, torch_dtype=tipo).to("cuda")
        res["fases"][f"cargar_flux_{tipo}"] = round(time.time() - t, 1)

        negras = 0
        for (nombre, prompt, w, h), (pe, ppe) in zip(lote, numeros):
            t = time.time()
            with torch.no_grad():
                img = pipe(prompt_embeds=pe.to("cuda", tipo), pooled_prompt_embeds=ppe.to("cuda", tipo),
                           width=w, height=h, num_inference_steps=4, guidance_scale=0.0,
                           generator=torch.Generator("cuda").manual_seed(semilla)).images[0]
            if max(img.convert("L").getextrema()) < 10:      # negra: este tipo no vale
                negras += 1
                if negras >= 2:
                    raise RuntimeError("imágenes negras")
                continue
            img.convert("RGB").save(SALIDA / "imagenes" / nombre, "JPEG", quality=93)
            res["imagenes"][nombre] = round(time.time() - t, 1)
            print(f"  GPU {gpu} · {nombre}: {time.time() - t:.1f} s ({tipo})", flush=True)
        res["tipo"] = str(tipo)
        break
    except Exception as e:  # noqa: BLE001
        res["errores"].append(f"GPU {gpu} {tipo}: {type(e).__name__}: {str(e)[:500]}")
        print(f"  GPU {gpu}: con {tipo} ha fallado: {e}", flush=True)
        pipe = tr = numeros = None
        gc.collect()
        torch.cuda.empty_cache()
Path(salida_json).write_text(json.dumps(res))


'''


def main():
    t_inicio = time.time()
    (SALIDA / "imagenes").mkdir(parents=True, exist_ok=True)
    informe = {"fases": {}, "imagenes": {}, "errores": []}

    t = time.time()
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "diffusers==0.35.1", "transformers==4.56.1", "accelerate==1.10.1",
                    "gguf==0.17.1", "sentencepiece", "protobuf",
                    "huggingface_hub[hf_transfer]==0.34.4"], check=True)
    informe["fases"]["instalar"] = round(time.time() - t, 1)

    t = time.time()
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
    from huggingface_hub import snapshot_download, hf_hub_download
    base = snapshot_download("black-forest-labs/FLUX.1-schnell", token=HF_TOKEN,  # noqa: F821
                             allow_patterns=["model_index.json", "scheduler/*", "text_encoder/*",
                                             "text_encoder_2/*", "tokenizer/*", "tokenizer_2/*",
                                             "vae/*", "transformer/config.json"])
    # 5 bits (8,3 GB): el de 8 bits llenaba la T4 y no quedaba sitio para pintar (26/11).
    gguf = hf_hub_download("city96/FLUX.1-schnell-gguf", "flux1-schnell-Q5_K_S.gguf")
    informe["fases"]["bajar_modelo"] = round(time.time() - t, 1)
    guardar(informe)

    # ¿Cuántas GPU hay? (sin importar torch aquí: los hijos eligen la suya)
    n = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True).stdout.count("GPU ")
    n = max(1, min(n, 2))
    informe["gpus"] = n
    print(f"==> {n} GPU", flush=True)
    lotes = [TRABAJOS[i::n] for i in range(n)]  # noqa: F821

    t = time.time()
    Path("/tmp/trabajador.py").write_text(TRABAJADOR)
    procesos = []
    for g in range(n):
        Path(f"/tmp/lote{g}.json").write_text(json.dumps({
            "gpu": g, "lote": lotes[g], "base": base, "gguf": gguf, "semilla": SEMILLA,  # noqa: F821
            "salida": f"/tmp/res{g}.json"}))
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(g),
                   PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
        procesos.append(subprocess.Popen([sys.executable, "/tmp/trabajador.py", f"/tmp/lote{g}.json"], env=env))
    for p in procesos:
        p.wait()
    resultados = []
    for g in range(n):
        f = Path(f"/tmp/res{g}.json")
        resultados.append(json.loads(f.read_text()) if f.exists()
                          else {"gpu": g, "fases": {}, "imagenes": {}, "errores": [f"GPU {g}: el proceso no terminó"]})
    informe["fases"]["pintar_total"] = round(time.time() - t, 1)
    for r in resultados:
        informe["imagenes"].update(r["imagenes"])
        informe["errores"] += r["errores"]
        informe["fases"].update({f"gpu{r['gpu']}_{k}": v for k, v in r["fases"].items()})
        informe[f"tipo_gpu{r['gpu']}"] = r.get("tipo")
    hechas = list(informe["imagenes"].values())
    informe["total_s"] = round(time.time() - t_inicio, 1)
    if hechas:
        informe["media_s_por_imagen_y_gpu"] = round(sum(hechas) / len(hechas), 2)
        informe["s_por_imagen_efectivo"] = round(informe["fases"]["pintar_total"] / len(hechas), 2)
    guardar(informe)
    print(json.dumps(informe, indent=1), flush=True)
    if not hechas:
        sys.exit(1)


if __name__ == "__main__":
    main()
