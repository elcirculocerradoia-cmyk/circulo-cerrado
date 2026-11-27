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

# Ilustración 2D tipo cómic oscuro, trazo negro grueso, fondos 2D reconocibles con contorno
# negro, paleta apagada y una sola luz dramática. Nada de texto: FLUX tiende a escribir letras.
# 28/11: en el vídeo del 27 se colaron imágenes FOTORREALISTAS (sobre todo paisajes y objetos):
# por eso lo de «no es una foto» va AL PRINCIPIO (CLIP solo lee las primeras ~75 palabras).
BASE = (
    "2D hand-drawn dark comic illustration, NOT a photograph, not photorealistic, no 3D render, "
    "thick black ink outlines on every object, flat cel shading, "
    "adult animation frame for a serious documentary story, "
    "recognizable well-built 2D environment drawn with defined black lines, clean and not cluttered, "
    "muted earthy greyish or dull blue-green palette, dramatic single light source such as a ceiling "
    "lamp, a bathroom light or street lamps, simple soft shadows, "
    "not cute, not childish, no bright saturated colors, "
    "no text, no letters, no words, no watermark"
)

# 26/11: el estilo PERFECTO para Rubén es la imagen 01 de la 1.ª tanda de Kaggle
# (pruebas/referencias/estilo-perfecto-kaggle-01-original.jpg). Poses sobrias, nada «goofy».
# 28/11 (instrucciones nuevas de Rubén): stick-figure expresivo, cuerpos delgados negros,
# cabezas redondas, expresiones claras (cejas marcadas, sudor, ojeras, seriedad, tensión).
# NO escribir «no clothes» (Cloudflare lo rechazaba). Plano medio: si no, salen cabezas gigantes.
PERSONAS = (
    "expressive stick figure characters: perfectly round head with a thick black outline and flat "
    "grey-beige skin, no nose, no ears, small solid black dot eyes, thick marked eyebrows, "
    "a simple line mouth, clear direct adult expression such as tension, seriousness, sweat drops "
    "or dark circles under the eyes; thin solid black stick body, thin black stick arms and legs, "
    "black hands; calm restrained pose, subtle natural body language, no exaggerated or dynamic poses; "
    "medium shot from the waist up or full body, the black stick body clearly visible, "
    "subject in the middle"
)

# Cuando no sale nadie (un paisaje, un objeto). Sin esto FLUX se inventa un muñeco, y sin
# insistir en el dibujo le salen FOTOS (28/11).
SIN_PERSONAS = (
    "wide establishing shot drawn in the same 2D comic style with black outlines, "
    "no people, no characters, no faces, empty scene, the object or place in the middle"
)

# Lo primero que lee FLUX en cada imagen (CLIP solo mira el principio).
AVISO = "2D hand-drawn dark comic illustration with thick black ink outlines, not a photo"

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
    """El texto completo de una imagen, en este ORDEN (28/11): aviso corto de dibujo, la ESCENA,
    los personajes y al final el estilo largo. FLUX.1-schnell solo lee ~256 piezas de texto: si
    el estilo va delante, lo que se corta es la escena, que es lo más importante."""
    quienes = [q for q in (quienes or []) if (personajes or {}).get(q)]
    aviso = [AVISO] if estilo is None else []      # la portada (fondo blanco) va sin él
    if estilo is None:
        estilo = f"{BASE}, {PERSONAS}" if quienes else f"{BASE}, {SIN_PERSONAS}"
    partes = (aviso + [descripcion.strip()] + [personajes[q] for q in quienes] + [estilo])
    return ". ".join(p.rstrip(". ") for p in partes) + "."
