---
name: vmc-ig-copy-ficha-tecnica
description: >
  Escribe el caption de Instagram (y, si lo piden, la versión para canal de WhatsApp) de una publicación de subasta de un vehículo, en el formato "ficha técnica directa": gancho + cierre de subasta + Transmisión/Vendedor/Precio Base + link directo a vmcsubastas.com, SIN pie de firma legal (nada de "link en BIO" ni "SUBASTOP S.A.C./RUC"). Úsalo cuando el usuario pegue datos de un vehículo (marca, modelo, año, transmisión, vendedor, precio base, fecha/hora de cierre) y pida el copy/caption para Instagram o WhatsApp, sobre todo si menciona "ficha técnica", "cierre de subasta", o pide ambas versiones. Si el post usa el pie "link en BIO" + "SUBASTOP S.A.C./RUC", esa es la skill vmc-instagram-copy, no esta -- pregunta si no está claro. Cubre buen estado y siniestrados (ángulo de proyecto de inversión).
---

# VMC/Subastop -- Copy de IG en formato "ficha técnica directa"

## Qué hace este skill

A partir de los datos sueltos de un vehículo (marca, modelo, año, transmisión, quién lo ofrece, precio base, fecha/hora de cierre de subasta), escribe el **caption de Instagram** listo para publicar, y si el usuario lo pide, también la **versión para canal de WhatsApp** del mismo vehículo.

El trabajo creativo real es el **gancho** (1-3 líneas de apertura) y la elección de emojis que encajen con el vehículo. El resto -- el bloque "Revisa la ficha técnica", el cierre de subasta y el link -- es una plantilla fija que se ensambla, no se reinventa.

Existe una skill hermana, `vmc-instagram-copy`, para el formato de caption que cierra con "Más info en nuestro link en BIO 👇" + la firma legal "SUBASTOP S.A.C. / RUC: 20522679781". Son dos formatos distintos que ha usado la cuenta en momentos distintos. Si no está claro cuál quiere el usuario, pregúntale -- no asumas.

## La regla que no se negocia

**Ningún dato se inventa.** Si el usuario no dio kilometraje, combustible, color, o cualquier otro dato, ese dato NO aparece en el copy. El caption solo afirma lo que el usuario proporcionó: transmisión, vendedor, precio base, fecha/hora, y la condición del vehículo (buen estado vs. siniestrado) si se sabe.

Esto no es solo prudencia legal: es la estrategia. Dejar fuera del copy todo lo que no sea Transmisión / Vendedor / Precio Base genera un "misterio" deliberado sobre el resto de las especificaciones -- eso es lo que obliga al lector a hacer clic en vmcsubastas.com para ver la ficha completa. Si rellenas ese hueco con un dato inventado, matas la razón de ser del click.

Si falta un dato imprescindible (precio base, o fecha/hora, o quién ofrece), pregúntalo antes de escribir. No lo completes "por plausibilidad".

## Anatomía del caption de Instagram

```
[GANCHO]  <- variable, 1-3 líneas, con emoji de vehículo al final

⏰ [CIERRE DE SUBASTA -- ver abajo cómo elegir la frase]

Revisa la ficha técnica: ⚙️ Transmisión: [Automática/Mecánica]
🏢 Vendedor: [entidad]
💵 Precio Base: US$ [monto]

👉 [CTA variable] en vmcsubastas.com
```

### Cómo escribir la línea de cierre de subasta

Dos variantes, según qué tan cerca esté la fecha:

- **Si la subasta es HOY** (usa la fecha real de hoy, no una fija): la urgencia es el arma más fuerte que tienes. Escribe `⏰ La subasta es HOY [día] de [mes] a la [hora] p.m.` -- el "HOY" en mayúsculas es lo que dispara el FOMO (miedo a perderse algo): el lector sabe que si no entra ahora, se quedó fuera.
- **Si la subasta es en una fecha futura**: usa `⏰ Cierre de subasta: [Día de la semana] [fecha] | [hora]`. No fabriques urgencia de "hoy" sobre una fecha que no es hoy -- se nota y resta credibilidad.

### El CTA final

Varía la frase según lo que tenga sentido mostrar:
- Vehículo en buen estado, fotos normales: "Mira las fotos completas y participa"
- Vehículo siniestrado, se quiere ser transparente sobre el estado real: "Mira las fotos del estado real y participa"
- Se quiere invitar a revisar specs no listadas: "Evalúa la ficha completa y participa"
- "Revisa todas las fotos y participa"

Todas cierran igual: `... en vmcsubastas.com`.

## Si además piden la versión de WhatsApp

Cuando el usuario pide las dos versiones (WhatsApp + Instagram) del mismo vehículo, usan el mismo gancho de fondo pero con distinta apertura:

```
📲 Versión para CANAL DE WHATSAPP
⏰ ¡HOY [FECHA] A LA [HORA]! 🚨
🔥 [GANCHO]

Revisa la ficha técnica: ⚙️ Transmisión: [X] 🏢 Vendedor: [Y] 💵 Precio Base: US$ [Z]

📲 Mira las fotos completas y participa aquí: 👉 vmcsubastas.com
```

```
📸 Versión para INSTAGRAM
🔥 [MISMO GANCHO, sin el aviso de countdown al inicio]

⏰ La subasta es HOY [día] de [mes] a la [hora] p.m.

Revisa la ficha técnica: ⚙️ Transmisión: [X] 🏢 Vendedor: [Y] 💵 Precio Base: US$ [Z]

👉 Mira las fotos completas y participa en vmcsubastas.com
```

La diferencia entre canales es solo de textura: WhatsApp abre con el aviso de countdown (🚨) porque es un mensaje directo que compite con notificaciones; Instagram deja que el gancho hable primero porque compite en un feed visual. El gancho, los datos y el link son los mismos.

Si el usuario solo pide Instagram (el caso más común), omite por completo la sección de WhatsApp -- no la ofrezcas de más.

## El gancho: elige el ángulo según el vehículo

El gancho no describe specs -- vende un beneficio concreto en un par de líneas, y termina (o incluye) un emoji que combine el tipo de vehículo con su condición.

**Vehículos en buen estado -- elige según lo que hace especial a esa unidad:**

- **Confiabilidad / alta rotación de reventa** -- para modelos con fama de duraderos (Corolla, Hilux, Yaris). Ej: "¡El sedán más buscado y confiable del mercado!"
- **Casi nuevo, precio de usado** -- para modelos del año o recientísimos. Ej: "¡Un 2024 con un punto de partida increíble!"
- **Espacio / confort / estilo de vida** -- SUVs, familiares. Abre con una pregunta que interpela al lector: "¿Buscas espacio, confort y presencia?"
- **Fuerza / trabajo pesado** -- pickups, utilitarios. Ej: "¡Fuerza imparable y trabajo pesado!"
- **Demanda alta / reventa rápida** -- cuando el modelo es de los más buscados del mercado. Ej: "¡El auto más comercial y buscado del mercado!"

**Vehículos siniestrados / recuperados -- un solo ángulo, bien ejecutado:**

El enfoque va directo al comprador que sabe lo que está comprando: inversionista, taller, repuestero. El gancho vende la **rentabilidad de reacondicionar**, no esconde el daño pero tampoco abre con la lista de golpes. Menciona la condición en la misma o segunda línea, como la razón del precio bajo -- no como advertencia aislada.

Plantilla de referencia: "¡El proyecto ideal para rentabilizar rápido! [Vehículo] en subasta. Unidad siniestrada con un precio de partida increíble. La ecuación perfecta para reacondicionar y sacarle el máximo provecho con una inversión súper baja."

No uses aquí los ángulos de "confiabilidad" o "casi nuevo" -- no aplican a una unidad chocada y suenan falsos.

## Emojis por tipo de vehículo (para el gancho)

Usa el emoji que combine mejor con vehículo + condición, no siempre el mismo:

| Situación | Emoji sugerido |
|---|---|
| Sedán confiable, buen estado | 🚗💨 |
| Auto siniestrado / chocado | 🚗💥 o 🚘💥 |
| SUV espaciosa | 🚙✨ |
| Auto muy demandado / "de moda" | 🚗🔥 |
| Pickup / trabajo pesado | 🛻💪 |

## Flujo de trabajo

1. **Reúne los datos**: marca, modelo, año, transmisión, vendedor, precio base, fecha/hora de cierre, condición (buen estado o siniestrado). Si falta precio base, fecha/hora o vendedor, pregunta -- no los inventes.
2. **Decide si la subasta es HOY** (compara con la fecha de hoy) para elegir entre "La subasta es HOY..." o "Cierre de subasta: ...".
3. **Fija la condición** del vehículo. Si no está clara y el usuario no lo aclara, pregunta antes de elegir ángulo -- no asumas buen estado por default.
4. **Elige el ángulo de gancho** de la librería de arriba, el que la unidad sostenga honestamente.
5. **Escribe el gancho** (1-3 líneas) con su emoji.
6. **Ensambla** el bloque fijo (cierre de subasta + ficha técnica + CTA) sin agregar datos no provistos.
7. Si piden ambos canales, añade también la versión de WhatsApp con la apertura de countdown.
8. Entrega el caption listo. Si el usuario está publicando varios vehículos, sepáralos claramente y no repitas el mismo ángulo de gancho entre ellos.

## Ejemplos trabajados (del historial real de la cuenta)

**Toyota Corolla 2016, automático, buen estado -- US$ 3,499, vendedor Pacífico, subasta HOY 14 de agosto 1:15 p.m.**
> 🔥 ¡El sedán más buscado y confiable del mercado! Toyota Corolla 2016 en subasta 🚗💨
>
> La oportunidad perfecta para asegurar un modelo de altísima rotación comercial y excelente margen de reventa.
>
> ⏰ La subasta es HOY 14 de agosto a la 1:15 p.m.
>
> Revisa la ficha técnica: ⚙️ Transmisión: Automática 🏢 Vendedor: Pacífico 💵 Precio Base: US$ 3,499
>
> 👉 Mira las fotos completas y participa en vmcsubastas.com

**Toyota Etios 2018, mecánico, SINIESTRADO -- US$ 1,799, vendedor Pacífico, subasta HOY 14 de agosto 1:05 p.m.**
> 🔥 ¡El proyecto ideal para rentabilizar rápido! Toyota Etios 2018 en subasta 🚗💥
>
> Unidad siniestrada con un precio de partida increíble. La ecuación perfecta para reacondicionar y sacarle el máximo provecho con una inversión súper baja.
>
> ⏰ La subasta es HOY 14 de agosto a la 1:05 p.m.
>
> Revisa la ficha técnica: ⚙️ Transmisión: Mecánica 🏢 Vendedor: Pacífico 💵 Precio Base: US$ 1,799
>
> 👉 Mira las fotos del estado real y participa en vmcsubastas.com

**Mitsubishi Outlander 2018, automática, buen estado -- US$ 10,999, vendedor MAF Perú, cierre miércoles 26 de agosto 1:20 p.m.**
> ¿Buscas espacio, confort y presencia? ¡Esta Mitsubishi Outlander 2018 puede ser tuya! 🚙✨
>
> Una SUV espaciosa, cómoda y elegante, ideal tanto para uso personal como para asegurar un proyecto de excelente margen comercial.
>
> ⏰ Cierre de subasta: Miércoles 26 de agosto | 1:20 p.m.
>
> Revisa la ficha técnica: ⚙️ Transmisión: Automática 🏢 Vendedor: MAF Perú 💵 Precio Base: US$ 10,999
>
> 👉 Mira el detalle completo y las fotos en vmcsubastas.com

**Toyota Hilux 2024, mecánica, buen estado -- US$ 9,999, vendedor MAF Perú, cierre miércoles 26 de agosto 1:00 p.m.**
> ¡Fuerza imparable y trabajo pesado! Toyota Hilux 2024 en subasta 🛻💪
>
> La pick-up más cotizada y resistente. Una máquina 2024 lista para cualquier terreno, con demanda altísima y valor de reventa garantizado.
>
> ⏰ Cierre de subasta: Miércoles 26 de agosto | 1:00 p.m.
>
> Revisa la ficha técnica: ⚙️ Transmisión: Mecánica 🏢 Vendedor: MAF Perú 💵 Precio Base: US$ 9,999
>
> 👉 Revisa todas las fotos y participa en vmcsubastas.com

## Verificación antes de entregar

- ¿Cada dato del bloque (transmisión, vendedor, precio base, fecha/hora) viene de lo que dio el usuario, sin nada inventado ni completado?
- ¿La línea de cierre usa "HOY" solo si la fecha de la subasta es literalmente hoy?
- ¿El ángulo del gancho corresponde al tipo de vehículo y a su condición real (no se usó "confiable" para un siniestrado, ni se escondió que es siniestrado)?
- ¿El caption NO incluye el pie "link en BIO" ni "SUBASTOP S.A.C. / RUC"? (si el usuario lo pide, esa es la otra skill, `vmc-instagram-copy`)
- Si publicó varios vehículos a la vez, ¿cada uno tiene un ángulo de gancho distinto?

## Edge cases

- **No queda claro qué formato de pie quiere el usuario** (este, sin firma, vs. el de `vmc-instagram-copy`, con firma SUBASTOP/RUC): pregunta antes de escribir, sobre todo si es la primera vez que trabajas con esa cuenta en la sesión.
- **Condición ambigua** (no dice si es siniestrado o no): pregunta. No asumas buen estado por default -- un choque no dicho que sale como "seminuevo" es el error más caro de este tipo de copy.
- **Faltan datos del bloque fijo** (vendedor, precio base o fecha/hora): son obligatorios para el CTA a tener sentido. Pregúntalos, no los omitas ni inventes.
- **Activo no vehicular** (maquinaria, propiedades, etc.): el método transfiere (gancho + ficha + CTA), pero la librería de ángulos y emojis está calibrada para vehículos -- ajusta el ángulo al activo y dilo explícitamente.
