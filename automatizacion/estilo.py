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

# Solo cuando en la escena sale alguien. Como el vídeo de referencia (25/11): muñecos con
# el CUERPO NEGRO MACIZO (tronco, brazos, piernas y manos negros y gruesos) y una cabeza
# redonda grande de color liso con la cara simple. Sin ropa: a cada personaje se le
# reconoce por la cabeza (pelo, bigote, color, gafas). Encuadre con aire encima de la
# cabeza: la imagen de Cloudflare es cuadrada y se recorta a 16:9.
PERSONAS = (
    "stickman characters: solid black silhouette body, thick solid black arms and legs, "
    "solid black hands, no clothes, large round flat-colored head with a thick black outline, "
    "simple expressive cartoon face, "
    "wide shot, the whole head visible with empty space above it, subject in the middle"
)

# Cuando no sale nadie (un paisaje, un objeto). Sin esto FLUX se inventa un muñeco
# (prueba del 25/11: un muñeco delante de la isla, un yate con cara).
SIN_PERSONAS = (
    "wide establishing shot, no people, no characters, no faces, empty scene, "
    "the object or place in the middle"
)

ESTILO = f"{BASE}, {PERSONAS}"      # se mantiene por compatibilidad

# La portada, como la miniatura de referencia (25/11): retrato del protagonista sobre fondo
# BLANCO liso, más detallado que en el vídeo y con la expresión muy marcada. La imagen
# cuadrada se pega a la izquierda de la miniatura y el texto va a la derecha (portada.py).
ESTILO_PORTADA = (
    "2D cartoon illustration, bold thick black ink outlines, flat colors with soft cel shading, "
    "chest-up portrait of one character facing slightly to the right, "
    "very exaggerated facial expression, detailed face and hair, "
    "plain pure white background, nothing else in the image, centered, "
    "no text, no letters, no words, no watermark"
)


def prompt_de(descripcion: str, personajes: dict | None = None, quienes=None,
              estilo: str | None = None) -> str:
    """El texto completo de una imagen: estilo + personajes que salen + la escena."""
    quienes = [q for q in (quienes or []) if (personajes or {}).get(q)]
    if estilo is None:
        estilo = f"{BASE}, {PERSONAS}" if quienes else f"{BASE}, {SIN_PERSONAS}"
    partes = [estilo] + [personajes[q] for q in quienes] + [descripcion.strip()]
    return ". ".join(p.rstrip(". ") for p in partes) + "."
