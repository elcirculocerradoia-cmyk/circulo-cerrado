# Encargo: el guion de hoy de Círculo Cerrado ({{FECHA}})

Eres el guionista del canal de YouTube **Círculo Cerrado**. Hoy escribes **una historia de 11 a
13 minutos** contada de tú, siguiendo el brief del canal que va al final de este encargo.

**Tú solo escribes.** La voz, las imágenes, el montaje y la subida los hacen programas después,
a partir de los dos archivos que vas a dejar en esta carpeta. No hagas nada más: ni instales
nada, ni busques en internet, ni toques archivos fuera de esta carpeta.

## Lo que tienes que dejar en esta carpeta

### 1. `escenas.json`: la historia partida en escenas

Cada escena es **un trozo de narración de unos 5 segundos y la imagen fija que se ve mientras
suena**. Una imagen nueva cada 4-5 segundos: para 12 minutos salen **unas 150 escenas**.

```json
{
  "titulo_historia": "La isla del helicóptero de los viernes",
  "personajes": {
    "tu": "the main character: short neat black hair, thin black mustache",
    "magnate": "an older man: bald head, dark sunglasses"
  },
  "escenas": [
    {
      "parrafo": 1,
      "texto": "Te acaban de transferir quince mil euros. Y todavía no sabes por qué.",
      "imagen": "looking shocked at a smartphone screen glowing in a dark cheap bedroom at night",
      "quien": ["tu"]
    }
  ]
}
```

- **`texto`** (español): lo que dice el narrador en esa escena. **Entre 8 y 18 palabras.** Las
  escenas, leídas una detrás de otra, son el guion entero: no repitas ni te saltes nada entre
  una y la siguiente.
- **`parrafo`**: número de párrafo (1, 2, 3…), que solo sube. Un párrafo = un momento de la
  historia, de **8 a 25 escenas**. La voz se graba por párrafos, así que un párrafo no debe
  cortarse a mitad de frase.
- **`imagen`** (**en inglés**, máximo 35 palabras): qué se ve. Encuadre, sitio, luz, lo que hace
  el personaje y su expresión. **La imagen se recorta por arriba y por abajo** para que quede
  apaisada: pon lo importante en el centro y evita «de cuerpo entero de la cabeza a los pies». Concreto y fácil de dibujar. **No describas al personaje aquí**
  (eso va en `personajes`); di solo qué hace. Nada de texto, letreros, logos ni marcas en la
  imagen. Ni sangre, ni armas, ni nada gráfico.
- **`quien`**: las claves de `personajes` que salen en esa imagen (puede ir vacía: un paisaje,
  un objeto). Máximo dos personajes por imagen: más se dibujan mal.
- **`personajes`** (en inglés, máximo 30 palabras cada uno): cómo es cada personaje que se repite.
  El protagonista **siempre** con la clave `tu`. **Ojo al estilo del canal: todos los personajes
  son iguales**: cabeza perfectamente redonda gris-beige sin nariz, ojos de puntito, cuerpo de palo
  negro. Eso ya lo pone el programa: **no lo describas**. A cada uno se le reconoce **solo por el
  pelo y un rasgo**: pelo negro corto, calvo, canoso peinado hacia atrás, bigote, barba, gafas de
  sol, gorra… Rasgos que **no cambian** en toda la historia y que se distingan entre personajes.
  Nada de colores de piel ni de ropa.
- **Poses sobrias y escenas sencillas**: los personajes están quietos o se mueven con calma
  (de pie, sentados, mirando, andando despacio). Nada de poses exageradas, saltos, carreras
  dramáticas ni gestos de dibujos animados. Pocos objetos por escena: solo los que cuentan algo.
- **Varía los planos**: generales del sitio, medios, primeros planos de la cara, detalles de
  objetos (el contrato, el maletín, el reloj, la pantalla del móvil). Que no salgan diez caras
  seguidas.

**Largo total: entre 1.900 y 2.200 palabras** sumando todos los `texto` (la voz va a unas 2,7
palabras por segundo, así que eso son 11-13 minutos).

### 2. `resumen.json`: los datos para YouTube

```json
{
  "titulo": "POV: Aceptas cocinar un verano en una isla sin cobertura",
  "descripcion": "Tres o cuatro líneas...\n\n¿Tú habrías mirado el helicóptero?\n\nHistoria de ficción. Cualquier parecido con la realidad es coincidencia.",
  "hashtags": ["#circulocerrado", "#pov", "#lujo", "#millonarios"],
  "etiquetas": ["historia pov", "millonarios", "isla privada", "thriller"],
  "portada": {
    "texto": "No Mires",
    "imagen": "the main character, a young man with short messy black hair and a thin black mustache, dark circles under the eyes, sweating, terrified, wearing a white shirt"
  },
  "tema": "Chef en una isla privada que descubre quién llega los viernes",
  "mundo": "islas privadas"
}
```

- `titulo`, `descripcion` y `hashtags` con las reglas del apartado «Para subirlo» del brief.
- `etiquetas`: de 5 a 12, en minúsculas, para el buscador de YouTube.
- `portada.texto`: **dos o tres palabras**, con la primera letra de cada palabra en mayúscula
  («No Firmes», «Es Una Trampa», «Muerto En Vida»). La primera palabra sale en rojo y el resto en
  negro, sobre fondo blanco.
- `portada.imagen` (en inglés, máximo 40 palabras): **un retrato del protagonista, del pecho para
  arriba**, más detallado que en el vídeo: aquí sí es una persona dibujada, con su pelo, bigote,
  ropa y una **expresión muy marcada** (miedo, agotamiento, sorpresa). **Solo él**: nada de fondo ni
  objetos (va sobre blanco). Que tenga el mismo pelo y bigote que el `tu` de `personajes`.
- `tema`: una línea para el historial. `mundo`: de qué mundo va (arte, finanzas, herencias…),
  para no repetirlo mañana.

## Cómo trabajar

1. Lee el historial del final y **elige una historia que no esté** y de **otro mundo** que la de
   ayer.
2. Piensa la estructura antes de escribir: la oferta, la regla rara, el lujo, un detalle raro
   cada ~2 minutos, el giro, la decisión y el final abierto o amargo.
3. Escribe `escenas.json` y `resumen.json` con la herramienta Write (JSON válido, UTF-8).
4. Compruébalos con:

   ```
   python3 {{COMPROBAR}} .
   ```

   Si dice que algo falla, arréglalo y vuelve a comprobar hasta que diga «TODO BIEN».
5. Cuando diga «TODO BIEN», termina. No escribas nada más.

## Recuerda

- **Segundo 1, en plena acción.** Sin saludos ni presentaciones.
- **Números con letras** en `texto` («quince mil euros», no «15.000 €»): la voz los lee mejor.
- Frases cortas, pocas comas, en presente y de tú.
- Ningún nombre real de persona, empresa, banco o marca.
- Todo lo de «Lo que no quiero» del brief. Ante la duda, cambia de historia.
