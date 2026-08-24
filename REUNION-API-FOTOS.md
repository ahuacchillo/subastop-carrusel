# Reunión con desarrollo — fotos sin marca de agua

**Fecha:** 24/08/2026 · **Pide:** Abraham (Instagram) · **Decide:** equipo web

## Contexto en tres líneas

Las fotos del CDN vienen con "vmc Subastas / powered by SUBASTOP.Co" **quemada en el
pixel**, en los tres tamaños publicados (`s_` 244×183, `m_` 460×345, y 800×600 sin
prefijo). No es un overlay de CSS: la estampa nuestro propio pipeline al subir, y no hay
variante limpia publicada. Revertirla se probó y no llega a calidad publicable.

Además, hoy los datos de la oferta salen de **regex sobre el HTML** de
`vmcsubastas.com/oferta/<id>` (`carrusel/scraper.py`): cualquier cambio de maquetación lo
rompe sin aviso.

---

## 1. La pregunta que decide todo

- [ ] **¿El archivo pre-marca se conserva o se descarta al subir?**

Si el pipeline estampa y sobrescribe, esto no es un problema de acceso sino de retención:
hay que cambiar el upload antes que nada.

- [ ] ¿Desde cuándo aplicaría el cambio?
- [ ] ¿Hay backfill de ofertas ya publicadas, o solo de aquí en adelante?

## 2. Antes de aceptar "te hacemos una API"

- [ ] Si el original ya está en el bucket, **¿alcanza con lectura al bucket, o un prefijo
      `orig_` junto a `s_`/`m_`?** Un path más es un día; una API son semanas.
- [ ] **¿Se puede dejar de quemar la marca y ponerla como overlay en el front?** Si es
      viable, resuelve para todos y el resto de la reunión sobra.
- [ ] Puente mientras tanto: ¿pueden dejar el original en una carpeta por oferta, a mano,
      para las subastas destacadas?

## 3. Acceso

- [ ] Autenticación: ¿token estático, service account, allowlist de IP? Corre **local y en
      Cloud Run** — necesito algo que sirva en los dos.
- [ ] ¿Entrada por código de oferta (`63014`) y salida con las fotos **en orden de
      galería**? El orden importa: la primera es la portada.
- [ ] ¿Rate limit?
- [ ] ¿Hay staging para probar sin tocar producción?
- [ ] ¿URLs estables o firmadas con expiración? Si expiran, ¿cuánto? (re-subo a GCS para
      que Meta pueda leer el render).

## 4. Calidad — el punto que justifica todo esto

- [ ] ¿Qué resolución real tiene el original? Para 1080×1080 necesito **≥1080 en el lado
      corto**; hoy el techo es 800×600.
- [ ] ¿Viene **sin encajar**? Hoy la web mete la foto en 800×450 y rellena con borroso.
      Quiero el encuadre completo del vendedor, no el letterbox.
- [ ] ¿Es el JPEG tal cual lo subió el vendedor, o re-encodeado?
- [ ] ¿EXIF/orientación confiable, o hay fotos rotadas?
- [ ] ¿Devuelve **toda** la galería o solo las primeras N?

## 5. El resto del contrato — aprovechar el viaje

- [ ] ¿La misma respuesta puede traer marca, modelo, año, transmisión, precio base,
      vendedor, fecha y hora?
- [ ] ¿Precio base **también en ofertas cerradas y negociables**? Hoy lo leo del payload
      porque esa tarjeta no se pinta.
- [ ] ¿Estado de la oferta y zona horaria de `processDatetime`?

## 6. Operación

- [ ] ¿Versionado y aviso de cambios, o me entero cuando falla?
- [ ] ¿A quién escribo un martes 8pm con subasta en curso?
- [ ] ¿Qué pasa si el vendedor reemplaza una foto después de que publiqué?

## 7. Legal y marca

- [ ] Publicar sin marca de agua en nuestro propio feed: ¿marketing y legal lo aprueban?
      La marca protege contra reventa de fotos; en @vmcsubastas no aporta.
- [ ] ¿Hay vendedores (concesionarios) cuyas fotos no puedan ir sin la marca?

---

## Salir de la reunión con esto

- [ ] Un `curl` que funcione contra una oferta real. Si todavía no hay endpoint, al menos
      **la ruta del original en el bucket, confirmada en pantalla**.
- [ ] Responsable y fecha comprometida.
- [ ] Camino elegido: `bucket` / `overlay en front` / `API nueva` / `carpeta manual`.

### Notas de la reunión

