# Integración con la API v3 — estado

**Fecha:** 26/08/2026 · **Escribe:** Abraham (Instagram) · **Continúa:** [`REUNION-API-FOTOS.md`](REUNION-API-FOTOS.md)

Verificado hoy contra producción, no leído del documento: `offer-groups` responde 200 sin
token; `offers/state` y `offers/replay` responden `401 UNAUTHENTICATED`.

## 1. De dónde salen hoy los datos

`carrusel/scraper.py` hace regex sobre el HTML de `vmcsubastas.com/oferta/<id>` y saca marca,
modelo, año, transmisión, precio base, vendedor, fecha/hora de cierre y las URLs de la galería.
Funciona, pero cualquier cambio de maquetación lo rompe sin aviso: ese es el motivo de migrar,
no la velocidad.

## 2. Qué campo trae cada endpoint

| Campo del carrusel | Hoy (scraper) | `offer-groups` (sin auth) | `offers/state/{id}` (token) | Webhook Herald |
|---|---|---|---|---|
| Marca | h1 | dentro de `name` | `Marca` | `brand` |
| Modelo | h1 | dentro de `name` | `Modelo` | `model` |
| Año | h1 | `model_year` | `Año` | `year` |
| **Transmisión** | HTML | **no** | **no** | **no** |
| Precio base | payload JS | `base_price` | `Precio base` | `base_price` |
| Vendedor | HTML | solo con `scope:index`, en minúsculas | `Vendedor` | `seller` |
| Fecha y hora de cierre | `processDatetime` | `close_date` + `readable_close_date` | `Fecha Subasta` | `close_date` |
| Galería completa, en orden | 8 URLs | **no**, solo portada `xs`/`md` | `Imagenes` (forma no documentada) | `images[]` |
| Estado / tipo de oferta | no | `state`, `offer_type` | `Estado`, `Tipo Oferta` | `offer_type` |
| Placa | no | no | `Placa` | `plate` |

Confirmado: el `id` de `offer-groups` (p. ej. `63154`) es el mismo número de la URL pública
`/oferta/63154` y el que ya usa `nueva-subasta.sh`. No hay traducción de códigos que resolver.

## 3. Bloqueantes para conectar

1. **Token.** Hace falta un Bearer de un `ApiClient` activo. Sin él, `state` y `replay` son 401.
2. **Allowlist de IP — el punto que más demora.** El estudio corre en **Cloud Run**, y la IP de
   salida de Cloud Run es dinámica: no se puede poner en una allowlist tal cual. Salir por IP fija
   obliga a montar VPC connector + Cloud NAT con IP reservada (infra nuestra, con costo mensual).
   Antes de gastar eso hay que preguntar: **¿el token solo alcanza para nuestro cliente?** Si la
   respuesta es sí, la integración arranca esta semana. Lo mismo aplica a la máquina local, que
   tampoco tiene IP fija.
3. **Staging.** No quiero probar reintentos y errores contra producción en día de subasta.
4. **Rate limit, versionado y a quién se avisa** cuando cambia el contrato.

## 4. Lo que la API **no** resuelve

- **Fotos: sigue igual que el 24/08.** `Imagenes` de `state` y `images[]` de Herald apuntan al
  mismo CDN de siempre. Verificado hoy sobre las ofertas en vivo: el techo sigue siendo
  **800×600** (`s_` 244×183, `m_` 460×345, sin prefijo 800×600) y la marca de agua sigue apareciendo
  en parte de las ofertas — 63116 y 63154 llegan limpias, 63155 y 63157 con el "VMC" quemado, y
  63189 llega con relleno a los lados. Es por subida, no por tamaño: no se puede predecir cuál
  viene limpia. Para 1080×1080 necesito ≥1080 en el lado corto. **Ningún endpoint nuevo cambia esto.**
  Probado también el CDN directo el 26/08: no hay variante mayor (`l_`, `xl_`, `o_`, `b_`,
  `original/`, `full/` → 404) ni resizer por query param (`?w=1600` devuelve los mismos 31 KB).
  Es CloudFront sirviendo archivos estáticos, así que el pedido no es "un endpoint": es que
  publiquen un archivo que hoy no existe.
- **Transmisión:** no está en ninguna de las cuatro APIs, y va en el caption de ficha técnica.
- **Orden y forma de `Imagenes`:** el documento dice "listado de imagenes de la oferta" y nada más.
  El orden importa: la primera foto es la portada del carrusel.

## 5. Plan, en el orden en que conviene hacerlo

| Fase | Qué | Depende de | Esfuerzo |
|---|---|---|---|
| 0 | Usar `offer-groups` para la agenda: qué cierra hoy y mañana, con id, precio base, hora y stats. Se puede hacer **ya**, no pide token. | nadie | medio día |
| 1 | `api.py` con `state/{id}` en lugar del regex; el scraper queda solo de respaldo para transmisión. Misma interfaz `leer(codigo)`, cero cambios aguas abajo. | token + allowlist | un día |
| 2 | Recibir el webhook Herald en el Cloud Run que ya tenemos: avisa apenas se publica una oferta y elimina el sondeo. | que registren nuestra URL + el secreto | un día |
| 3 | Fotos limpias ≥1080. | la reunión del 24/08, sin resolver | — |

`replay` y `bids` no entran en el pipeline del carrusel. Sirven para contenido posterior
("cómo se movió la puja en el último minuto"); no los voy a integrar hasta que haya un post que
los pida.

## 6. Pedido concreto a desarrollo

1. Token Bearer y nombre del `ApiClient`, para producción y staging.
2. Decidir la allowlist: token solo, excepción para nuestro cliente, o la IP fija que tengamos
   que montar nosotros. **Esta respuesta define la fecha de la fase 1.**
3. Agregar `transmision` al response de `state` (y a Herald).
4. Especificar `Imagenes`: forma, orden, cuántas y la resolución máxima disponible.
   Y publicar un variante nuevo en el CDN —`l_<hash>.jpeg` con ≥1080 en el lado corto, o el
   original tal como lo subió el vendedor— junto a los tres que ya existen. Mientras no exista,
   `ajustar.sh` amplía la foto con Lanczos antes de renderizar: los bordes salen definidos en
   vez de blandos, pero es maquillaje sobre 800 px, no detalle nuevo.
5. Registrar la URL de nuestro Cloud Run en Herald y darnos el secreto. Nota: hoy
   `X-VMC-Signature` viaja como el secreto en texto plano, no como HMAC del cuerpo; conviene
   cambiarlo a HMAC antes de exponer el receptor.
6. Rate limit, política de versionado y contacto para un martes 8 p.m. con subasta en curso.
