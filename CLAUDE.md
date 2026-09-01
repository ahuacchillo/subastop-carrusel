# Subastop · Carrusel

Generador de carruseles de Instagram para @vmcsubastas: le das el código de una oferta de vmcsubastas.com y te devuelve los 4 PNG del carrusel listos para publicar, junto con el copy generado para el post.

## Comandos

```bash
./estudio.sh                                         # las ofertas abiertas, en el navegador
./nueva-subasta.sh 63014                             # código de oferta → PNG en Posts/<slug>/
python3 api.py                                       # qué ofertas hay abiertas, por terminal
python3 elegir.py Materiales/63014                   # qué tres fotos elegiría el modelo
cd remotion && npm install && npm run dev            # el Remotion Studio del slide
```

Renderizar completo toma cerca de un minuto por subasta. Para revisar composición usa `remotion still`, no el render completo.

## Dónde va cada archivo

- Fotos de una subasta descargadas → `Materiales/<id>/` (ignorado en git).
- Elementos fijos de marca (logos, cierres) → `Materiales/`.
- Renders finales y copy generado → `Posts/<slug>/` (ignorado en git).
- Componentes y composiciones Remotion → `remotion/src/`.
- Tokens de diseño VMC → `remotion/src/brand/vmc.ts`.

## Flujo del Estudio

1. `./estudio.sh` levanta el servidor local en Python (`estudio.py`) y abre la interfaz web (`estudio.html`).
2. Consulta la API de subastas abiertas (`api.py`).
3. Descarga las fotos de la subasta a `Materiales/<id>/`.
4. El modelo de visión de DeepSeek (`elegir.py`) selecciona las 3 fotos óptimas:
   - 1: Portada (frontal)
   - 2: Interior (o lateral si no hay)
   - 3: Trasera (mostrando placa)
   - Evalúa además si el auto tiene choque o daño visible.
5. Remotion renderiza los 4 slides (`render.mjs`).
6. DeepSeek redacta el copy del post según las características y estado.
7. Se puede descargar el ZIP o publicar directamente a Instagram Graph API (`publicar.py`).

## Requisitos del sistema

- Node.js 20+ y Python 3.10+
- `ffmpeg`, `ffprobe` e `imagemagick` (`convert` o `magick`).
- Llaves en el home de usuario:
  - DeepSeek API: `~/deepseek-clave.txt` (o variable `DEEPSEEK_API_KEY`)
  - Instagram Graph API: `~/ig-token.txt` (o variable `IG_TOKEN`)

## Skills y Comandos de Claude Code

- `/subasta` (`.claude/commands/subasta.md`): Asistente guiado para armar el carrusel de una subasta paso a paso.
- `vmc-ig-copy-ficha-tecnica`: Redacción de copy de venta para Instagram.
- `vmc-subastas-content`: Estilo, formato y lineamientos de piezas de subasta.

## Idioma

- Comentarios de código en inglés.
- Documentación y textos de cara al usuario en español neutro.
