# Pedido a desarrollo — una foto de mayor resolución en el CDN

Verificado el 26/08/2026 contra `cdn.vmcsubastas.com` y contra `APIs - Documents v3.pdf`.
Para pegar tal cual en el canal de desarrollo.

---

## El mensaje

> Hola. Necesito una variante de mayor resolución de las fotos de oferta en el CDN, y quiero
> darles el dato exacto de lo que llega hoy para que la pregunta sea corta.
>
> **Lo que hay hoy.** Tomo la primera foto de la galería de la oferta 63173 como ejemplo. El CDN
> publica tres archivos por foto, en `cdn.vmcsubastas.com/images/auction/<oferta>/`:
>
> | archivo | resolución | peso |
> |---|---|---|
> | `s_6a8ccd2bcf7e1.jpeg` | 244 × 183 | 8 KB |
> | `m_6a8ccd2bcf7e1.jpeg` | 460 × 345 | 23 KB |
> | `6a8ccd2bcf7e1.jpeg` (sin prefijo) | **800 × 600** | 40 KB |
>
> El de 800 × 600 es el más grande de los tres y es el que uso. Confirmo que no hay nada
> por encima:
>
> - Probé `l_`, `xl_`, `o_`, `b_`, `orig_`, `original/<hash>.jpeg` y `full/<hash>.jpeg`: **404**
>   los siete.
> - Probé `?w=1600` y `?width=1600` sobre el de 800 × 600: devuelve **los mismos 40 KB**, así que
>   no hay redimensionador por query param. Las cabeceras dicen CloudFront + Cloudflare con
>   `cache-control: immutable`, o sea archivos estáticos.
> - En el PDF de la API v3, el `images[].image` del webhook Herald apunta a **esta misma URL sin
>   prefijo**, y `offer-groups` solo expone `image_xs` e `image_md`, que son las dos más chicas.
>   Ningún endpoint de la v3 da algo distinto — no es un problema de qué endpoint llamo.
>
> **Por qué me bloquea.** El post de Instagram es de 1080 × 1080 y la foto se monta con recorte
> al cuadrado, así que necesito **≥ 1080 en el lado corto**; hoy el lado corto son 600 px. La foto
> se amplía 1.8× y se ve blanda: los bordes del auto, la placa y el emblema salen difusos. Hoy la
> amplío con Lanczos antes de renderizar, que ayuda, pero es maquillaje sobre 800 px — no hay
> detalle que recuperar.
>
> **Lo que pido, en orden de preferencia.**
>
> 1. **Un cuarto variante en el CDN**, con el mismo esquema de nombres que los tres que ya
>    existen: `l_<hash>.jpeg`, con ≥ 1080 px en el lado corto (ideal ≥ 1440). Que se genere en la
>    subida, igual que `s_` y `m_`. Así no cambia nada de mi lado más que el prefijo.
> 2. Si el archivo **tal como lo subió el vendedor** se guarda en algún bucket, la URL de ese
>    original me sirve igual — aunque venga pesado, yo lo bajo de escala.
> 3. Si ninguna de las dos es posible: díganme **a qué resolución llega la foto al backend antes
>    de que la redimensionen**. Si el vendedor ya sube 800 × 600, el pedido cambia de lugar (es
>    a la app de captura, no al CDN) y dejo de insistir acá.
>
> Tres preguntas concretas para responderme:
>
> - ¿Existe el original en algún lado, o el resize de subida es destructivo?
> - Si existe, ¿se puede publicar un variante `l_` sin migrar las ofertas viejas — nuevas
>   solamente me sirve?
> - Los `s_`/`m_`/sin-prefijo se generan en la subida. ¿Cuánto es agregar un cuarto tamaño ahí?
>
> Aparte, mientras estemos: la marca de agua "VMC" aparece quemada en parte de las ofertas y no en
> otras (63116 y 63154 llegan limpias, 63155 y 63157 con marca), y no puedo predecir cuál. Si el
> variante nuevo sale **sin** marca de agua, resuelve las dos cosas de una.

---

## Notas para mí, no para el mensaje

- El upscale con Lanczos que menciona el mensaje está en `ajustar.sh`, primer paso del render.
  Cuando el variante `l_` exista, hay que apuntar el regex de `scraper.py` (`\"image\":\"…\"`) al
  nuevo prefijo y el upscale se vuelve un no-op solo: ya salta las fotos cuyo lado corto llega
  a 1440.
- El resto del contrato de la API (token, allowlist, `transmision`, Herald) va en
  `API-INTEGRACION.md` §6. Este documento es solo la foto, que es lo único que no depende de un
  token.
- El checklist largo para la reunión sigue en `REUNION-API-FOTOS.md`.
