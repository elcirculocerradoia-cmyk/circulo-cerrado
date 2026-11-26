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
    "adult 2D animation frame for a serious documentary story, clean black line art, "
    "muted desaturated color palette, dark moody cinematic lighting from a single light source "
    "with soft gradient shading, gritty tense atmosphere, detailed but simple background, "
    "not cute, not childish, no bright saturated colors, "
    "no text, no letters, no words, no watermark"
)

# Solo cuando en la escena sale alguien. EXACTAMENTE como el vídeo de referencia de Rubén
# (25/11): cabeza perfectamente redonda con borde negro grueso y piel lisa gris-beige, SIN
# nariz ni orejas, ojos de puntito negro, cejas y boca de una raya, cara seria de adulto;
# cuerpo de palo NEGRO y fino (brazos y piernas de palo, manos negras). A cada personaje
# se le reconoce por el pelo (negro liso, calvo, canoso), bigote o gafas.
# NO escribir «no clothes»: Cloudflare rechazó una imagen así. Plano medio: si no, salen
# solo cabezas gigantes. Primera versión (colores vivos, caras infantiles): descartada.
PERSONAS = (
    "stick figure characters: perfectly round head with a thick black outline and flat "
    "grey-beige skin, no nose, no ears, tiny solid black dot eyes, thick simple eyebrow lines, "
    "a simple line mouth, serious deadpan adult expression; the body is a plain thin solid black "
    "stick figure: black stick torso, thin black stick arms and legs, black hands, "
    "no shirt, no suit, no clothing details on the body; "
    "medium shot from the waist up or full body, the black stick body clearly visible, "
    "empty space above the head, subject in the middle"
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
    "detailed adult 2D cartoon illustration, bold black ink outlines, muted realistic colors "
    "with soft cel shading, realistic proportions, chest-up portrait of one man facing slightly "
    "to the right, very expressive tired or scared face with dark circles under the eyes, "
    "detailed face and hair, not cute, not childish, "
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
