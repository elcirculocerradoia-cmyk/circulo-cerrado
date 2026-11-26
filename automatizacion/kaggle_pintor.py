"""
Lo que se ejecuta DENTRO de Kaggle, con su GPU gratis (T4, 16 GB): pinta las imágenes con
FLUX.1-schnell. No se lanza a mano: kaggle_lanzar.py le pega delante la lista de trabajos
(TRABAJOS, SEMILLA, HF_TOKEN) y lo sube a Kaggle con `kaggle kernels push`.

Cómo cabe en 16 GB:
  1.º los textos: T5 + CLIP en la GPU convierten TODAS las descripciones en números; se borran.
  2.º el dibujo: FLUX comprimido a 8 bits (GGUF, 12,6 GB) + el VAE pintan una a una.
Así cada modelo entra solo en la GPU y no hay que moverlos a cada imagen.

Deja en /kaggle/working: imagenes/<nombre>.jpg e informe.json (tiempos y errores).
"""
# ── (aquí kaggle_lanzar.py pega TRABAJOS, SEMILLA y HF_TOKEN) ──

import json
import os
import subprocess
import sys
import time
from pathlib import Path

T_INICIO = time.time()
SALIDA = Path("/kaggle/working")
(SALIDA / "imagenes").mkdir(parents=True, exist_ok=True)
informe = {"gpu": None, "fases": {}, "imagenes": {}, "errores": []}


def guardar_informe():
    (SALIDA / "informe.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False))


def fase(nombre, t0):
    informe["fases"][nombre] = round(time.time() - t0, 1)
    guardar_informe()
    print(f"==> {nombre}: {time.time() - t0:.0f} s", flush=True)


t = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "diffusers==0.35.1", "transformers==4.56.1", "accelerate==1.10.1",
                "gguf==0.17.1", "sentencepiece", "protobuf",
                "huggingface_hub[hf_transfer]==0.34.4"], check=True)
fase("instalar", t)

import torch  # noqa: E402
from huggingface_hub import snapshot_download, hf_hub_download  # noqa: E402

informe["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "SIN GPU"
print("GPU:", informe["gpu"], flush=True)

t = time.time()
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
BASE = snapshot_download("black-forest-labs/FLUX.1-schnell", token=HF_TOKEN,  # noqa: F821
                         allow_patterns=["model_index.json", "scheduler/*", "text_encoder/*",
                                         "text_encoder_2/*", "tokenizer/*", "tokenizer_2/*",
                                         "vae/*", "transformer/config.json"])
# Formato que entiende diffusers (el de second-state es para stable-diffusion.cpp: falló el 26/11).
GGUF = hf_hub_download("city96/FLUX.1-schnell-gguf", "flux1-schnell-Q8_0.gguf")
fase("bajar_modelo", t)

from diffusers import FluxPipeline, FluxTransformer2DModel, GGUFQuantizationConfig  # noqa: E402

# La T4 no tiene bf16 de verdad: se prueba bf16 y, si sale negro o falla, fp16.
for TIPO in (torch.bfloat16, torch.float16):
    informe["tipo"] = str(TIPO)
    try:
        # 1.º Los textos
        t = time.time()
        pipe = FluxPipeline.from_pretrained(BASE, transformer=None, vae=None, torch_dtype=TIPO).to("cuda")
        numeros = []
        with torch.no_grad():
            for nombre, prompt, w, h in TRABAJOS:  # noqa: F821
                pe, ppe, _ = pipe.encode_prompt(prompt=prompt, prompt_2=prompt, max_sequence_length=256)
                numeros.append((pe.cpu(), ppe.cpu()))
        del pipe
        torch.cuda.empty_cache()
        fase(f"textos_{TIPO}", t)

        # 2.º El dibujo
        t = time.time()
        tr = FluxTransformer2DModel.from_single_file(
            GGUF, quantization_config=GGUFQuantizationConfig(compute_dtype=TIPO),
            torch_dtype=TIPO, config=BASE, subfolder="transformer")
        pipe = FluxPipeline.from_pretrained(BASE, transformer=tr, text_encoder=None, text_encoder_2=None,
                                            tokenizer=None, tokenizer_2=None, torch_dtype=TIPO).to("cuda")
        fase(f"cargar_flux_{TIPO}", t)

        negras = 0
        for (nombre, prompt, w, h), (pe, ppe) in zip(TRABAJOS, numeros):  # noqa: F821
            t = time.time()
            with torch.no_grad():
                img = pipe(prompt_embeds=pe.to("cuda", TIPO), pooled_prompt_embeds=ppe.to("cuda", TIPO),
                           width=w, height=h, num_inference_steps=4, guidance_scale=0.0,
                           generator=torch.Generator("cuda").manual_seed(SEMILLA)).images[0]  # noqa: F821
            if max(img.convert("L").getextrema()) < 10:      # negra: el tipo no vale
                negras += 1
                if negras >= 2:
                    raise RuntimeError("imágenes negras")
            img.convert("RGB").save(SALIDA / "imagenes" / nombre, "JPEG", quality=93)
            informe["imagenes"][nombre] = round(time.time() - t, 1)
            guardar_informe()
            print(f"  {nombre}: {time.time() - t:.1f} s", flush=True)
        break
    except Exception as e:  # noqa: BLE001
        informe["errores"].append(f"{TIPO}: {type(e).__name__}: {str(e)[:600]}")
        guardar_informe()
        print(f"  Con {TIPO} ha fallado: {e}", flush=True)
        torch.cuda.empty_cache()

hechas = [v for v in informe["imagenes"].values()]
informe["total_s"] = round(time.time() - T_INICIO, 1)
if hechas:
    informe["media_s_por_imagen"] = round(sum(hechas) / len(hechas), 2)
guardar_informe()
print(json.dumps(informe, indent=1), flush=True)
if not hechas:
    sys.exit(1)
