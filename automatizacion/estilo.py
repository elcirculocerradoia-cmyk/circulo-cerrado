"""
El estilo de las imágenes de Círculo Cerrado, en un solo sitio.

Lo usan la prueba de imágenes (pintor_cf.py --prueba) y el vídeo del día (dia.py).
Si cambias el estilo aquí, cambia en los dos.

Para que el personaje salga parecido en todas las imágenes:
  - el mismo texto de estilo delante de cada imagen,
  - la misma descripción del personaje, palabra por palabra, cada vez que sale,
  - y la misma semilla en todo el vídeo (si Cloudflare la acepta).
Con IA no queda perfecto, pero así se nota poco.

Cloudflare no deja elegir el tamaño: la imagen se recorta a 16:9 por el centro, así
que se pide una composición ancha con lo importante en la franja del medio.

FLUX entiende mejor el inglés, así que las descripciones van en inglés.
"""

# Ilustración 2D con trazo negro marcado, fondos 2D detallados y sombreados.
# Nada de texto: FLUX tiende a escribir letras.
BASE = (
    "2D cartoon illustration, bold thick black ink outlines, flat colors with soft cel shading, "
    "detailed shaded 2D background, moody lighting, comic panel style, clean lines, "
    "no text, no letters, no words, no watermark"
)

# Solo cuando en la escena sale alguien. Encuadre con aire encima de la cabeza: la imagen
# de Cloudflare es cuadrada y se recorta a 16:9 (prueba del 25/11: cortaba cabezas).
PERSONAS = (
    "simple stickman-style character with a round head and thicker solid limbs, expressive hands, "
    "clear simple facial expression with dot eyes and eyebrows, "
    "wide shot, the whole head visible with empty space above it, subject in the middle"
)

# Cuando no sale nadie (un paisaje, un objeto). Sin esto FLUX se inventa un muñeco
# (prueba del 25/11: un muñeco delante de la isla, un yate con cara).
SIN_PERSONAS = (
    "wide establishing shot, no people, no characters, no faces, empty scene, "
    "the object or place in the middle"
)

ESTILO = f"{BASE}, {PERSONAS}"      # se mantiene por compatibilidad

# La portada: más contraste y más limpia, con sitio para el texto a un lado.
ESTILO_PORTADA = (
    "2D cartoon illustration, bold thick black ink outlines, flat bright colors, high contrast, "
    "simple stickman-style character with a round head and thicker solid limbs, "
    "very exaggerated facial expression, character in the foreground on the right half, "
    "the whole head visible with empty space above it, "
    "clean simple light background, empty space on the left side, "
    "youtube thumbnail style, no text, no letters, no words, no watermark"
)


def prompt_de(descripcion: str, personajes: dict | None = None, quienes=None,
              estilo: str | None = None) -> str:
    """El texto completo de una imagen: estilo + personajes que salen + la escena."""
    quienes = [q for q in (quienes or []) if (personajes or {}).get(q)]
    if estilo is None:
        estilo = f"{BASE}, {PERSONAS}" if quienes else f"{BASE}, {SIN_PERSONAS}"
    partes = [estilo] + [personajes[q] for q in quienes] + [descripcion.strip()]
    return ". ".join(p.rstrip(". ") for p in partes) + "."
