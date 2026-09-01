---
description: Arma el carrusel de Instagram de una subasta — pregunta los datos, elige portada, renderiza y revisa el resultado
---

Vas a producir un carrusel de subasta de VMC. Lee primero
`.agents/skills/vmc-subastas-content/SKILL.md` si no lo tienes en contexto.

Todo esto corre desde `carrusel/`. Argumento opcional: la carpeta con las
fotos. Si no viene, es `Materiales/`.

## 1. Mira las fotos antes de preguntar nada

Arma un contact sheet de las fotos de la carpeta y **míralo**:

```bash
python3 -c "
from PIL import Image; import sys, pathlib
fs = sorted(p for p in pathlib.Path('<carpeta>').iterdir() if p.suffix.lower() in ('.png','.jpg','.jpeg'))
s = Image.new('RGB', (300*len(fs), 300))
[s.paste(Image.open(f).resize((300,300)), (i*300,0)) for i,f in enumerate(fs)]
s.save('/tmp/contact.png'); print([f.name for f in fs])"
```

De ahí sacas dos cosas que el usuario no tiene por qué deletrear:

- **Cuál va de portada.** La portada es el único slide con marca y modelo, y el
  título va arriba a la derecha en blanco. Si esa zona de la foto es cielo
  quemado, el modelo se pierde: propone otra. Un 3/4 frontal o un frontal
  limpio suele ganarle a un interior.
- **Qué orden cuenta mejor el auto.** Exterior → interior → detalle.

## 2. Pregunta los datos

Con `AskUserQuestion` o en texto, lo que sea más rápido. Son ocho campos:

marca · modelo · año corto (`25'`) · transmisión · precio base sin `US$` ·
fecha `dd/mm` · hora · tienda oficial

Propón el orden de fotos que decidiste en el paso 1 y que el usuario lo
confirme o lo cambie. No lo decidas por él en silencio.

## 3. Renderiza

El script es interactivo, así que le pasas las respuestas por stdin en el orden
exacto de las preguntas:

```bash
printf 'Toyota\nFortuner\n25'"'"'\nMecánica\n34,999\n10/08\n1:35 pm\nMaquisistema\n1 2 3\n' \
  | ./nueva-subasta.sh <carpeta>
```

Orden de las líneas: marca, modelo, año, transmisión, precio, fecha, hora,
tienda, orden de fotos.

## 4. Revisa los renders — este paso no se salta

Abre **los tres PNG** con la herramienta Read y míralos. Buscas dos fallas
concretas, ambas reales y ambas vistas ya:

- **El título contra la foto.** El modelo va en blanco y la marca en degradado;
  el tramo violeta sobre un vidrio oscuro pierde fuerza. Si no se lee, la
  solución es otra portada, no retocar el degradado.
- **La tarjeta de datos.** Un precio de cinco cifras deja la fila al límite de
  los 466px; uno de seis la revienta. Una transmisión larga
  ("Automática secuencial") hace lo mismo.

Repórtale al usuario qué viste, incluido lo que quedó justo. Si algo falla, dilo
en vez de entregarlo.

## 5. Anota

Agrega la fila en `RESULTADOS.md` (en la raíz del repo): fecha, pieza, formato, qué foto fue portada.
Las métricas se llenan a mano a las 72h.
