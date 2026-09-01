---
name: vmc-subastas-content
description: Genera contenido de Instagram para VMC Subastas (@vmcsubastas) con Remotion — carruseles de autos en subasta, posts de cierre y piezas de campaña, siguiendo el sistema VOYAGER pixel-perfect.
---

# Instagram Content — VMC Subastas

Skill para producir el contenido de Instagram de VMC Subastas. Documenta el
sistema visual, el pipeline técnico y el flujo de trabajo. Se lee entero antes
de tocar un componente.

## Identidad

- **Producto:** VMC Subastas — subastas de vehículos en Perú
- **Cuenta:** @vmcsubastas · vmcsubastas.com
- **Sistema de diseño:** VOYAGER (`7bjDwC20BX1AFrv9Q8BOIb` en Figma)
- **Formato base:** post 1:1, 1080×1080

## Sistema Visual — VOYAGER

Los tokens del carrusel viven en `carrusel/remotion/src/brand/vmc.ts`. **Ese
archivo es la fuente de verdad.** (Los reels tienen su propia mitad del kit en
`reels/remotion/src/brand/vmc.ts`.) Ningún componente define colores, sombras ni degradados
propios: si un número no está en `vmc.ts`, no existe.

### Tipografía
| Rol | Fuente | Pesos |
|---|---|---|
| Todo | Plus Jakarta Sans | 500 Medium, 600 SemiBold, 700 Bold, 800 ExtraBold |
| Inicial del avatar del vendedor | Roboto | 700 |

### Paleta
```
#FCFAFA  text/neutral-inverse — textos sobre foto (NO es blanco puro)
#FFFFFF  bordes glass y textos dentro de tarjeta
#ED8936  naranja VOYAGER
#8460E5  violeta VOYAGER
#AE8EFF  violeta claro (barra del logo)
#5A35C2  índigo (barra del logo)
#2E0F70  índigo profundo (label SUBASTAS del logo)
```

### Glass — dos recetas, no una

Conviven dos variantes y **no son intercambiables**:

| Variante | Blur | Cola del degradado | Dónde |
|---|---|---|---|
| Ligero | `5px` | transparente | header del vendedor, flechas |
| Denso | `20px` | `rgba(113,113,113,0.5)` | tarjeta de datos del auto |

El denso es más opaco porque tiene que leerse encima de cualquier foto, incluida
una foto quemada de mediodía. Nunca poner la tarjeta de datos en glass ligero.

Las tres superficies comparten elevación: `0px 8px 24px rgba(0,0,0,0.1)`
exterior + `inset 0px 1px 6px rgba(255,255,255,0.45)` interior.

### El borde degradado — la trampa

El spec de Figma llama al borde "VYStrokes1, blanco 1.5px", pero los SVG
exportados traen un degradado (blanco → naranja → violeta → blanco) y es lo que
se ve en el render. Se usa el degradado.

**No se puede hacer con `background-clip: border-box`.** Los rellenos glass son
translúcidos, así que el degradado del borde se ve a través de ellos y tiñe la
tarjeta entera de naranja y violeta. Se hace con una capa aparte y máscara
`xor` — ver `<BordeGlass>` en `posts/AutoSlide.tsx`. Es el único método correcto.

### Reglas inquebrantables

- Sin emojis en las piezas visuales. SVG inline únicamente.
- El logo VMC va **siempre** en la esquina inferior derecha, en `x 855.29 / y 952.32`, tamaño `179.51 × 66.69`. No se mueve, no se escala, no se recolorea.
- Las coordenadas de los componentes son **absolutas contra el frame de 1080×1080**, iguales a las de Figma. No traducir a flex a nivel de página: así se compara render contra diseño sin recalcular nada.
- Textos sobre foto llevan su sombra (`shadow.textNombre` / `shadow.textMarca`). Sin ella se pierden en un cielo quemado.
- El precio va formateado en los datos, no calculado en el componente.

## Anatomía del carrusel de un auto

Referencia pixel-perfect: frame `51` del sistema (nodo `7340:30564`).

| Elemento | Posición | Sale en |
|---|---|---|
| Foto del auto | full bleed, `objectFit: cover` | todas |
| Header del vendedor (glass ligero) | `45, 49` · `372×104` | todas |
| Modelo + Marca (derecha, `x 1009.56`) | `y 42` y `y 94` | **solo la portada** |
| Flecha izquierda | `45.19, 515.22` | todas menos la primera |
| Flecha derecha | `942.42, 515.22` | todas menos la última |
| Píldora de fecha | `45, 778.25` · `353×51` | todas |
| Tarjeta de datos (glass denso) | `45, 845` · `466×176` | todas |
| Logo VMC | `855.29, 952.32` | todas |

**La marca y el modelo salen únicamente en la primera imagen.** De la segunda en
adelante se repite todo lo demás idéntico: es lo que hace que el carrusel se lea
como una sola pieza al deslizar, y lo que deja la foto respirar.

El bloque de marca y modelo **se solapa a propósito** (~42px). No es un error de
posición. Separarlos rompe el remate visual.

## Pipeline técnico

```
Instagram/
├── .claude/commands/subasta.md
├── reels/                    # el otro producto, pipeline aparte (reels/REELS.md)
└── carrusel/                 # ← todo lo de este skill
    ├── Materiales/           # lo que entrega el usuario: fotos, logo, SVGs
    │   └── <auto>/           # una subcarpeta por subasta
    ├── Posts/<slug>/         # renders listos + datos.json de la pieza
    ├── nueva-subasta.sh      # ← el generador
    └── remotion/             # proyecto Remotion del carrusel
        ├── public/
        │   ├── autos/        # fotos ya normalizadas, prefijadas por slug
        │   └── brand/vmc-logo.svg
        └── src/
            ├── brand/vmc.ts  # tokens VOYAGER del carrusel — fuente de verdad
            ├── subasta.ts    # solo el ejemplo que se ve en el Studio
            ├── posts/AutoSlide.tsx
            └── Root.tsx      # una composición `Auto`; el slide lo elige `indice`
```

### Publicar un carrusel nuevo

```bash
cd carrusel
./nueva-subasta.sh Materiales/<auto>
```

Pregunta los ocho datos, lista las fotos de esa carpeta, pide el orden, y deja
`Posts/<slug>/` con los PNG y el `datos.json` que los reproduce. No edita
código: los datos entran a Remotion por `--props`.

Con `/subasta` en Claude Code se hace lo mismo pero con el paso de criterio
incluido — elegir portada mirando las fotos y revisar los renders.

**Los renders se verifican mirándolos.** Siempre. Ver abajo.

### Ajustar el diseño (no los datos)

Para trabajar el componente en el Studio (`npm run dev`), `src/subasta.ts` tiene
una subasta de ejemplo. Se previsualiza el slide 0; para ver los otros se cambia
`indice` en el panel de props del Studio.

### Verificar un render

No se da por bueno un render sin mirarlo. Dos cosas que fallan siempre:

- **Contraste del titular contra la foto.** El modelo va en blanco arriba a la derecha; si esa zona de la foto es cielo quemado, se pierde. Se resuelve eligiendo otra foto de portada, no subiéndole sombra al texto.
- **Desborde de la tarjeta de datos.** Un precio de cinco cifras o una transmisión larga ("Automática secuencial") empujan la fila. La fila usa `space-between` para aguantarlo, pero se comprueba.

Truco para comprobar alineación contra Figma: poner el PNG exportado de Figma
como foto de fondo y renderizar encima. Si algo está movido, se ve doble al
instante. Es más rápido y más honesto que medir a ojo.

## Antes de construir una pieza — PREGUNTAR SIEMPRE

Paso obligatorio. Nunca se asume el material visual.

1. Revisar `carrusel/Materiales/`.
2. Preguntarle al usuario, con el guion de slides ya en la mano:
   - Qué fotos van y en qué orden (cuál es la portada).
   - Qué falta y hay que generar o pedir.
3. Recién con esa respuesta se produce.

Las fotos reales del auto **siempre** ganan a cualquier render o stock. En
subastas la foto real —con el rayón, con el patio de fondo— es la que da
credibilidad; una foto de catálogo hace dudar de que el auto exista.

## Ciclo de aprendizaje

Después de publicar, anotar resultados en `RESULTADOS.md` (raíz del proyecto).
Antes de armar una pieza nueva, leerlo: el formato y el orden de fotos se
eligen con lo que ya funcionó, no de cero.
