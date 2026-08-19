# Carruseles de Instagram — VMC Subastas

Generador de piezas para @vmcsubastas: le das el código de una oferta de
vmcsubastas.com y te devuelve los 4 PNG del carrusel listos para publicar.

Todo lo de este documento se corre desde `carrusel/`, y todas sus rutas son
relativas a esta carpeta. El otro producto del repo —los reels verticales de
marca— vive en `../reels/` y tiene su propio pipeline: [`../reels/REELS.md`](../reels/REELS.md).

## El estudio — el camino sin terminal

```bash
./estudio.sh
```

Abre una página en el navegador con todo a la vista, sin scroll: las fotos a la
izquierda, el auto en el centro, los datos a la derecha. **La interfaz está en
inglés** — las piezas que produce siguen en español.

- **Arriba** se pega el código (`63015`) o el link y se presiona *Fetch*. Trae
  marca, modelo, año, transmisión, precio, fecha, hora, tienda y la galería.
- **Photos**, a la izquierda — **no viene nada preseleccionado**: la galería llega
  entera y apagada. Clic en una foto para sumarla, clic otra vez para quitarla, y
  las que quedan se renumeran solas. **El orden en que se tocan es el orden del
  carrusel** y la primera lleva el rótulo COVER. Van tres; al llegar a tres hay
  que soltar una para cambiarla. Las fotos propias se arrastran desde el
  explorador y se sueltan sobre ese riel.
- **Centro** — el auto a tamaño grande. Se arrastra para moverlo, rueda del
  mouse para acercar, y las flechas del teclado para corregir de uno en uno
  (con Shift, de cinco en cinco). Las guías punteadas marcan dónde caen el título y la
  tarjeta. Las pestañas `1 2 3` cambian de slide.
- **Car details**, a la derecha — los ocho datos, editables. Los que faltan
  quedan marcados en rojo y el botón de generar se deshabilita.

*Generate carousel* deja los PNG y los muestra en el mismo lugar del auto, en
2×2. La pestaña `✓` vuelve al resultado, las numeradas vuelven al encuadre.
Entre 10 y 15 segundos.

- **Caption**, debajo de los datos — aparece recién con el carrusel hecho. Es
  `Posts/<slug>/copy.md` en vivo: *Draft it* se lo pide a Claude con el skill
  `copy-subastas-vmc` y deja las dos versiones, Instagram y Canal de WhatsApp
  (unos 40 segundos). Lo que se escriba encima se guarda solo, *Reload* vuelve
  a leer el archivo del disco y *Copy to clipboard* lo deja listo para pegar.

Después aparece *Download carousel*: baja los cuatro PNG y el `copy.md` en un
solo ZIP (`<slug>.zip`) y **deja la página en cero** para la siguiente subasta — galería
vacía, campos en blanco. Se borra la pantalla, no el disco: `Posts/<slug>/`
queda intacto y el carrusel se puede reabrir cuando sea.

```bash
./estudio.sh 63015-toyota-corolla   # reabrir uno hecho, para reencuadrar
```

## Y el camino por terminal, que sigue igual

```bash
./nueva-subasta.sh 62996
# → Posts/62996-toyota-hilux/1.png 2.png 3.png 4.png + datos.json
```

El `4.png` es la placa de cierre (`Materiales/cierre.png`): se copia tal cual al
final de todos los carruseles, no pasa por Remotion y no cambia nunca.

Los dos caminos usan las mismas piezas —`scraper.py` para los datos,
`ajustar.sh --render` para los PNG— así que no pueden desincronizarse.

---

## Ponerlo a funcionar en tu máquina

Esto corre local, en tu computadora, y no hay nada que desplegar. De cero a un
carrusel son cuatro pasos.

### 1 · Lo que hace falta

Dos cosas, las dos gratis, y probablemente ya tengas una:

| | Versión mínima | Comprobarlo | Para qué |
|---|---|---|---|
| **Python** | 3.9 | `python3 --version` | el estudio y el scraping |
| **Node + npm** | 18 | `node --version && npm --version` | el render de los PNG |

Probado sobre Python 3.12.3, Node 24.16.0 y npm 11.13.0, en Linux.

El 3.9 de Python no es capricho: `estudio.py` usa `str.removeprefix`, que no
existe antes. El 18 de Node lo pide Remotion 4. **No hace falta nada más:** el
estudio, el servidor y el scraping usan pura librería estándar de Python — cero
`pip install`, cero entorno virtual.

En Ubuntu/Debian, si falta alguno:

```bash
sudo apt install python3 nodejs npm
```

### 2 · Instalar

```bash
git clone git@github.com:ahuacchillo/subastop-instagram.git
cd subastop-instagram/carrusel/remotion
npm install          # ~400 MB, un par de minutos. Es Remotion con todo.
cd ..
```

Si los scripts no arrancan con "permiso denegado":

```bash
chmod +x *.sh
```

### 3 · Abrirlo

```bash
./estudio.sh
```

Levanta un servidor en `http://127.0.0.1:4173/` y abre el navegador solo. Para
cerrarlo, `Ctrl-C` en esa terminal.

Si dice `Address already in use`, ya lo tenías abierto en otra terminal: usa esa
pestaña del navegador, o cierra la anterior con `Ctrl-C`.

**El primer render del día se demora bastante más.** Remotion descarga su propio
Chrome headless la primera vez (~150 MB) y bundlea sin caché. A partir del
segundo, un carrusel entero sale en 10-15 s.

Si `npx remotion` se queja de librerías del sistema (típico en un Linux recién
instalado):

```bash
cd remotion && npx remotion browser ensure
```

### 4 · Comprobar que quedó bien

Agarra un código de una subasta **abierta** —de la portada de vmcsubastas.com,
el número que va después de `/oferta/`— y córrelo:

```bash
./nueva-subasta.sh 63014
```

Si imprime las 3 rutas de `Posts/` y los PNG abren, está funcional.

Ojo con el código: las ofertas cerradas dejan de publicar su galería, y contra
una vieja el scraping falla con "no trajo fotos". Falla ruidosamente a propósito
—prefiere no renderizar antes que inventar datos—, así que ese mensaje casi
siempre significa código caducado, no instalación rota.

---

## El stack, y por qué así

Cuatro piezas, cada una elegida por una razón concreta:

| Pieza | Qué hace | Por qué esa |
|---|---|---|
| **Python, solo stdlib** (`estudio.py`, `scraper.py`) | el servidor y la lectura de la oferta | sin dependencias no hay `pip install` que se pudra ni entorno que reconstruir: se clona y corre |
| **`urllib` + regex** | sacar los datos y las fotos de vmcsubastas | la página viene renderizada del servidor, así que todo está en el HTML y no hace falta un navegador para leerla |
| **Remotion + React + Chromium** | dibujar los PNG de 1080×1080 | la pieza se diseña en código, con las mismas coordenadas de Figma, y se versiona en git — un canvas no da eso |
| **Un HTML servido desde disco** (`estudio.html`) | la interfaz | sin build, sin framework, sin `npm run dev` para la UI: se recarga el navegador y ya está el cambio |

Los dos caminos —el estudio y la terminal— comparten `scraper.py` y
`ajustar.sh --render`, así que hay **un solo camino de render** en todo el
proyecto y la página no puede desviarse de lo que produce el script.

---

## Por qué corre en local, y qué haría falta para no

Cada quien lo corre en su máquina. No hay servidor, no hay costo y no hay nada
que mantener: se clona el repo y se abre. Para una herramienta que usan una o
dos personas, eso es la respuesta correcta, no una limitación.

Igual la pregunta se hizo en serio, así que aquí queda contestada con números,
para no volver a discutirla de memoria.

Renderizar un slide lanza un **Chromium de verdad** sobre los ~630 MB de
`node_modules` de Remotion. Eso no entra en una función serverless —Vercel corta
en 250 MB de bundle, con disco de solo lectura y tiempo limitado—, así que Vercel
podría alojar la página pero nunca el render, ni en el plan pago. En un
contenedor sí corre, y bien. Medido dentro de la imagen de este repo:

| | |
|---|---|
| Carrusel completo (3 slides + placa) | **13 s** |
| Memoria en reposo | **141 MiB** |
| **Pico durante el render** | **704 MiB** |
| Imagen, con Chromium horneado | ~1.5 GB |

Ese pico de 704 MiB es el que decide todo: **descarta cualquier plan gratuito de
512 MB** (Render, y los que quedan por el estilo). Hugging Face dejó el SDK de
Docker detrás de un plan de pago, y Fly.io ya no tiene capa gratuita. Queda Cloud
Run, que para este volumen sale $0 pero exige una tarjeta registrada, o un túnel
(`cloudflared tunnel --url http://localhost:4173`) sobre esta misma máquina.

O sea: gratis, sin tarjeta y encendido siempre, ya no existe para 704 MiB. Hay
que ceder la laptop encendida o la tarjeta, y ninguna de las dos vale la pena
todavía.

### El Dockerfile que quedó

Está construido y probado —el render de 13 s de la tabla salió de él— pero no
está en uso. Es la salida de emergencia el día que se decida exponerlo:

```bash
docker build -t estudio-vmc .
docker run -p 7860:7860 -e ESTUDIO_CLAVE=loquesea estudio-vmc
```

`estudio.py` lee tres variables de entorno, y con las tres sin poner se comporta
exactamente como siempre:

| Variable | Por defecto | Para qué |
|---|---|---|
| `ESTUDIO_HOST` | `127.0.0.1` | `0.0.0.0` para escuchar fuera de la máquina |
| `PORT` | `4173` | el puerto |
| `ESTUDIO_CLAVE` | vacío | la contraseña; **vacía no hay autenticación** |

**`ESTUDIO_CLAVE` no es opcional en cuanto salga de `127.0.0.1`.** El servidor
escribe archivos y lanza un renderizador: sin clave le entregas las dos cosas a
quien dé con la URL. Si arranca escuchando fuera de `127.0.0.1` sin clave, avisa
por consola.

Y no hace falta disco persistente: *Download carousel* baja el resultado en el
momento, así que `Materiales/` y `Posts/` pueden ser efímeros.

---

## Cómo funciona

Cuatro etapas dentro de `nueva-subasta.sh`, en ese orden:

**1. Scraping.** La página de vmcsubastas viene renderizada del servidor, así
que los datos y las fotos están en el HTML — no hace falta navegador. Se sacan
con regex marca, modelo, año, transmisión, precio base, vendedor y fecha/hora
del proceso, y se descargan las 3 primeras fotos de la galería a `Materiales/<id>/`.
Se reintenta 3 veces: a veces el sitio contesta con la portada en vez de la
oferta, y se nota en que no hay galería.

**2. Datos.** Con URL o código no pregunta nada: lo que sale del sitio se da por
bueno. Con `--editar` se revisan los ocho campos uno por uno, y lo que el
scraping no encontró se pregunta siempre. Enter acepta el valor entre corchetes.

**3. Props.** Se arma un JSON por slide en un tempdir, y una copia legible en
`Posts/<slug>/datos.json` — con eso la pieza se rehace igual dentro de un año.
El slug lleva el código de oferta adelante (`62996-toyota-hilux`) porque es el
único nombre que no cambia si después se corrige la marca, y es lo que se busca
cuando hay que volver a la publicación original.

**4. Render.** Delega en `./ajustar.sh <slug> --render`, que renderiza un slide
por vez desde el `datos.json` y copia la placa de cierre al final. Hay un solo
camino de render en todo el proyecto: lo que se arregla ahí, se arregla para
todos los modos de entrada.

### Modos

```bash
./nueva-subasta.sh 62996                # código de oferta
./nueva-subasta.sh https://www.vmcsubastas.com/oferta/62996
./nueva-subasta.sh 62996 --editar       # igual, pero revisando cada dato
./nueva-subasta.sh Materiales/toyota    # fotos propias, sin scraping
./nueva-subasta.sh                      # fotos sueltas en Materiales/
```

Sin código de oferta el script pregunta todo y pide el orden de las fotos. La
primera del orden es la portada.

En el prompt del orden alcanza con escribir la portada: `3` se completa a
`3 1 2` con las que falten, en el orden del listado. El carrusel siempre sale de
3 slides (o de las que haya, si hay menos).

### Datos del sitio, fotos mías

```bash
./subasta-fotos-propias.sh 62996 Materiales/toyota
```

Scrapea los ocho datos de la oferta pero arma el carrusel con las fotos de esa
carpeta. Para cuando la galería del sitio es mala o hay fotos mejores del patio.
Sí pregunta el orden: si las fotos las eligió una persona, cuál va de portada
es una decisión suya, no del sitio.

Es un wrapper de `nueva-subasta.sh 62996 --fotos <carpeta>` — un solo generador,
tres formas de entrar.

### La marca de agua — se pide el original, no se despeja

Las fotos del CDN vienen con la marca "vmc Subastas / powered by SUBASTOP.Co"
quemada en el pixel, en los tres tamaños que publica (`s_` 244×183, `m_` 460×345
y 800×600 sin prefijo). No es un overlay de CSS: la pone nuestra propia web al
subir la foto, y no hay variante limpia publicada.

Se probó revertirla. La capa es idéntica en todas las fotos, así que sale con
un ajuste por pixel calibrado contra originales, pero el resultado no llegó a
calidad publicable: la foto queda en 800×450 —la web *encaja* la foto en el
cuadro y rellena con borroso, y solo ese rectángulo es despejable— y el ruido de
la calibración se ve como moteado en las zonas planas. Se descartó.

**El camino es pedirle al equipo de la web el archivo pre-marca**: existe antes
de que el pipeline lo estampe, y además rompe el techo de 800×600, que para un
carrusel de 1080×1080 se nota. Mientras tanto, las fotos se usan con marca.

### Con Claude Code

```
/subasta 62996
```

Hace lo mismo pero con el paso de criterio incluido: mira las fotos antes de
elegir portada (si el título cae contra un cielo quemado propone otra) y revisa
los tres PNG al final. Definido en `../.claude/commands/subasta.md`; el sistema
visual completo está en `../.agents/skills/vmc-subastas-content/SKILL.md`.

---

## El diseño

```
carrusel/remotion/src/
├── brand/vmc.ts          ← tokens VOYAGER del carrusel. Fuente de verdad.
├── subasta.ts            ← subasta de ejemplo, solo para el Studio
├── posts/AutoSlide.tsx   ← el slide del carrusel
└── Root.tsx              ← composición `Auto`; el slide lo elige `indice`
```

Ningún componente define colores, sombras ni degradados propios: si un número no
está en `vmc.ts`, no existe. Los reels tienen su propia mitad del kit en
`../reels/remotion/src/brand/vmc.ts`; `sans`, `gradient.borde` y
`shadow.glassInset` están en los dos archivos, y si tocas uno hay que tocar el
otro en el mismo commit. Las coordenadas son absolutas contra el frame de
1080×1080, iguales a las de Figma, para poder comparar render contra diseño sin
recalcular nada.

Dos reglas que se rompen solas si no se saben:

- **Marca y modelo salen únicamente en la primera imagen.** De la segunda en
  adelante se repite todo lo demás idéntico: es lo que hace que el carrusel se
  lea como una sola pieza al deslizar.
- **El borde degradado del glass no se puede hacer con `background-clip`.** Los
  rellenos son translúcidos y el degradado se ve a través, tiñendo la tarjeta de
  naranja. Va en capa aparte con máscara `xor` — ver `<BordeGlass>`.

Para trabajar el componente:

```bash
cd remotion && npm run dev
```

Abre el Studio con la subasta de ejemplo de `subasta.ts`. Se previsualiza el
slide 0; para ver los otros se cambia `indice` en el panel de props.

---

## Ajustar el encuadre

La foto se monta con `objectFit: cover`, así que el recorte al 1080×1080 sale
del centro. Cuando eso se come parte del auto —está bajo en la foto, corrido, o
la foto es muy horizontal— se corrige por foto en el `datos.json`:

```json
"fotos": [
  { "src": "autos/x-1.jpeg", "foco": "50% 35%", "escala": 1.2 },
  "autos/x-2.jpeg"
]
```

`foco` es un `object-position` y mueve el recorte; `escala` acerca, y lo hace
alrededor del foco, no del centro. Un string suelto es lo mismo que
`"50% 50%"` con `escala: 1` — o sea, el comportamiento de siempre. Todos los
`datos.json` viejos siguen renderizando byte a byte igual.

Pero a mano no se aciertan esos números: se ajustan en el estudio, arrastrando.

```bash
./estudio.sh 62915-dfsk-glory            # reabrir para reencuadrar
./ajustar.sh 62915-dfsk-glory --render   # rehacer los PNG desde datos.json
```

Al reabrir, la galería ofrece **las fotos que ya usó ese carrusel** (las de
`remotion/public/autos/`) y no las de `Materiales/`. Es a propósito: son las únicas que
mapean exacto contra el encuadre guardado, y adivinar por posición le pega el
encuadre a la foto equivocada apenas el orden no fue 1-2-3.

**Una foto apaisada no se mueve en vertical** hasta que la acerques. Recortada
en cuadrado no sobra nada arriba ni abajo, así que no hay foto escondida para
revelar; el zoom es el que crea ese margen.

Para trabajar el componente en sí —mover coordenadas, tocar el glass— sigue
siendo el Studio (`cd remotion && npm run dev`). Esa es la herramienta del
que diseña la pieza; el estudio es la del que arma el post.

## Revisar antes de publicar

Este paso no se salta. Dos fallas que ya pasaron:

- **El título contra la foto.** El modelo va en blanco arriba a la derecha; si
  esa zona de la foto es cielo quemado, se pierde. Se resuelve eligiendo otra
  portada, no subiéndole sombra al texto.
- **La tarjeta de datos.** Un precio de cinco cifras deja la fila al límite de
  los 466px; uno de seis la revienta. Una transmisión larga ("Automática
  secuencial") hace lo mismo.

Después de publicar, la fila va a `../RESULTADOS.md`. Las métricas se llenan a mano
desde IG Insights a las 72h. Antes de armar una pieza nueva se lee ese archivo:
el formato y el orden de fotos se eligen con lo que ya funcionó.

---

## Pendientes

Ordenados por lo que más duele.

### 1. Generador de copys — hecho, con una dependencia nueva

El hueco ya no es entero. `Posts/<slug>/copy.md` existe, el estudio lo muestra
al lado de los slides, se guarda solo y viaja en el ZIP:

```
Posts/<slug>/
├── 1.png 2.png 3.png 4.png
├── datos.json
└── copy.md             ← caption de feed + Stories + hashtags
```

La receta ya está fijada: `../.claude/skills/copy-subastas-vmc/SKILL.md` — léxico
prohibido ("remate", "puja", "mejor postor"), estructura de ficha, patrones de
titular y las reglas sobre el estado del vehículo, que es donde más se metió la
pata. Hoy Claude la lee y deja las dos versiones (Instagram y Canal de
WhatsApp) en `copy.md`; el estudio solo lo muestra.

`POST /generar-copy` arma el prompt con `datos.json` y llama al CLI de Claude
(`claude -p … --allowed-tools Skill Write`), que lee la skill y **escribe el
archivo él mismo**. Es a propósito: pedirle el texto por stdout devuelve el
texto más una nota de lo que hizo, y esa nota termina dentro del `copy.md`. El
archivo es el contrato, y así no hay nada que parsear.

La regla §1 viaja en el prompt aunque ya esté en la skill. Sin ella el borrador
vuelve con "ágil", "económico de mantener", "de ciudad" — atributos que nadie
dio, que es el error que la propia skill llama el más repetido.

Dos cosas que esto trae: el estudio ahora **depende del CLI de Claude** para ese
botón (sin él, el resto sigue funcionando y el textarea se escribe a mano), y
cuando haya API, se cambia el `subprocess.run` por la llamada y nada más — la
página no se entera.

**Pedido abierto: opción de API key.** Hoy el botón exige el CLI instalado y con
sesión iniciada, lo que no sirve en el contenedor ni para nadie del equipo que
no use Claude Code. Falta la bifurcación en `generar_copy()`:

- Con `ANTHROPIC_API_KEY` en el entorno → llamada directa a la API de Mensajes
  (`claude-sonnet-5` alcanza para un caption), mandando el contenido de
  `../.claude/skills/copy-subastas-vmc/SKILL.md` como prompt de sistema y los datos
  de la subasta como mensaje. Con `urllib` de la stdlib basta: no hace falta el
  SDK y el proyecto se queda sin dependencias.
- Sin la variable → el `subprocess.run` del CLI que ya existe.
- Sin ninguno de los dos → error claro en la página, no un traceback.

La respuesta se escribe en el mismo `copy.md`, así que la página no cambia. La
clave va en el entorno —nunca en el repo— y en el contenedor viaja igual que
`ESTUDIO_CLAVE`.

### 2. Un bundle de Remotion por slide

Cada `npx remotion still` bundlea de nuevo. Se arregla pasando a la API de Node
(`@remotion/renderer`), que bundlea una vez y renderiza los tres. Marcado con
`ponytail:` en `ajustar.sh`. **Menos urgente de lo que parecía:** medido desde el
estudio, un carrusel entero sale en 9–14s. La primera ejecución del día es la
lenta; después el caché de Remotion hace el trabajo.

### 3. `../RESULTADOS.md` está vacío

Ocho carruseles publicados, cero métricas anotadas. Sin esos números el criterio
de portada es opinión. El experimento abierto es el orden de fotos: frontal →
interior → 3/4 contra uno que abra en 3/4.

### 4. Los reels no están en el pipeline

Son otro producto con otro flujo, y desde el split viven en su propio árbol
(`../reels/`, con su propio proyecto Remotion): se montan a mano y se renderizan
con `npm run reel:<nombre>`. **Todo eso está documentado aparte en
[`../reels/REELS.md`](../reels/REELS.md)** — metodología, stack, reglas y
pendientes. Empieza por ahí si vas a tocar un reel.

Lo que sigue pendiente: sus datos están quemados en una constante dentro del `.tsx`
(`NEGOCIABLE`, `VENDER`, `VENDESOLO`). Merecen el mismo tratamiento que el carrusel:
props por JSON y una entrada en el script.

### 5. Solo vmcsubastas.com

El scraping es específico de ese sitio. @subascars.pe no tiene scraper: ahí hay
que usar el modo manual con fotos propias.

### 6. El scraping es regex contra HTML

Si vmcsubastas cambia el markup, se rompe. Falla ruidosamente (sale con "no
trajo fotos") en vez de renderizar datos vacíos, que es lo importante, pero
alguien va a tener que arreglar los patrones algún día.

### 7. El carrusel está fijo en 3 slides

Instagram acepta 10. Tres es una decisión, no un límite técnico, pero está
cableada en tres lugares (el `[:3]` del scraping, el `TODAS` del orden, y el
guion visual de las flechas).

### 8. El render no es 100% determinista

Renderizar el mismo slide dos veces puede dar PNG distintos. Medido: la
diferencia son ~2500 píxeles (0.2% de la imagen) concentrados en el texto de la
píldora de fecha — antialiasing, invisible a ojo. Es anterior a todo esto y no
afecta lo publicado, pero significa que no se puede usar el md5 como prueba de
que un cambio no rompió nada. Hay que mirar.

### 9. Fotos y renders fuera del repo

`Materiales/<auto>/` y `Posts/` están en `.gitignore`: son 50 MB que se
regeneran con el código de oferta. La consecuencia es que no hay historial
compartido de piezas publicadas. Si el equipo lo necesita, va a un Drive, no a
git.

**El material de los reels sí va al repo**, y es la excepción a propósito: una toma
de un generador no se puede volver a pedir, aunque repitas el prompt exacto. Vive en
`../reels/tomas/`, fuera de este árbol, y por eso ya no hace falta desexcluir nada
a mano en el `.gitignore`.
