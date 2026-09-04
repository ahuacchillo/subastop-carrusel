import { AbsoluteFill, Img, staticFile } from "remotion";
import React from "react";
import { color, sans, shadow } from "../brand/vmc";
import type { Subasta } from "../subasta";
import { AutoSlide, Flecha, Header } from "./AutoSlide";

// ═════════════════════════════════════════════════════════════════════════════
// Variante "gancho de curiosidad": el mismo carrusel clásico, con un slide de
// intriga antepuesto.
//
// 1: la portada desenfocada, con la pregunta de intriga.
// 2..N: las fotos de siempre (frente, interior, atrás — AutoSlide indice
//       0..N-1), pixel-iguales al carrusel clásico. Solo la portada (2) suma
//       el pedido de comentario encima.
//
// Entre una subasta y otra lo único que cambia es la pregunta del slide 1 (la
// escribe DeepSeek) y el logo del vendedor, si hay uno — todo lo demás es el
// mismo componente que ya rendería un carrusel clásico.
// ═════════════════════════════════════════════════════════════════════════════

const GanchoSlide: React.FC<{ s: Subasta; texto: string }> = ({ s, texto }) => {
  const f = s.fotos[0];
  const { src, foco = "50% 50%" } = typeof f === "string" ? { src: f } : f;

  return (
    <AbsoluteFill style={{ background: color.white, overflow: "hidden" }}>
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: foco,
          filter: "blur(28px)",
          // Escalado para que el borde desenfocado no asome fuera del frame.
          transform: "scale(1.1)",
        }}
      />
      {/* Tinte violeta en vez de negro/gris plano: hasta el desenfoque se
          siente de la marca, no de un blur genérico de cualquier feed. */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(165deg, rgba(46,15,112,0.55) 0%, rgba(46,15,112,0.35) 45%, rgba(46,15,112,0.65) 100%)",
        }}
      />
      {/* Vendedor + pregunta, agrupados y centrados: sin la insignia
          "Subasta abierta" (ya sacada), pero el logo se queda — es la
          credibilidad del post, no ruido. */}
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: 70,
          // Más margen a la derecha que a la izquierda: ahí vive la flecha
          // (x 942-1035), y una pregunta larga de DeepSeek puede llegar a
          // rozarla si el bloque es simétrico.
          right: 170,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 40,
        }}
      >
        <Header tienda={s.tienda} logo={s.logo} enFlujo logoAltura={96} />
        <div
          style={{
            fontFamily: sans,
            fontWeight: 800,
            fontSize: 66,
            lineHeight: 1.2,
            textAlign: "center",
            color: color.inverse,
            textShadow: shadow.textNombre,
          }}
        >
          {texto}
        </div>
      </div>

      {/* Misma flecha, misma posición que en el carrusel de 4 fotos: sin
          override de `top`, queda centrada verticalmente a la derecha. */}
      <Flecha hacia="der" />
    </AbsoluteFill>
  );
};

/**
 * El pedido de comentario, encima de la revelación — no depende de que
 * alguien lea el caption. Va debajo del título, antes de que empiece la
 * tarjeta de datos (top 845).
 */
/** El bocadillo de chat: el ícono es lo que dice "comenta" antes de leer una
    sola letra, así el CTA no depende del color para distinguirse de la
    fecha. */
const IconoComentario: React.FC = () => (
  <svg width={26} height={26} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
    <path
      d="M4 4.5h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9.5L5 21.5V17.5H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2Z"
      fill="white"
    />
    <circle cx="8.3" cy="11" r="1.35" fill={color.indigo} />
    <circle cx="12" cy="11" r="1.35" fill={color.indigo} />
    <circle cx="15.7" cy="11" r="1.35" fill={color.indigo} />
  </svg>
);

const CtaComentario: React.FC<{ modelo: string }> = ({ modelo }) => (
  <div
    style={{
      position: "absolute",
      right: 45,
      top: 310,
      maxWidth: 620,
      borderRadius: 87.319,
      padding: "14px 30px 14px 20px",
      display: "flex",
      alignItems: "center",
      gap: 12,
      // Sólido y violeta oscuro, no el degradado naranja de la fecha: si
      // comparten color se leen como el mismo tipo de dato, y este no lo es.
      background: color.indigo,
      boxShadow: shadow.glass,
      fontFamily: sans,
      fontWeight: 700,
      fontSize: 27,
      lineHeight: 1.3,
      color: color.inverse,
      textShadow: shadow.textHeader,
      whiteSpace: "nowrap",
    }}
  >
    <IconoComentario />
    Comenta "{modelo.toUpperCase()}" para más info
  </div>
);

export const AutoGancho: React.FC<{
  s: Subasta;
  /** 0 = gancho desenfocado; 1..N = las fotos de siempre (AutoSlide
      indice 0..N-1). */
  indice: number;
  gancho: string;
}> = ({ s, indice, gancho }) => {
  if (indice === 0) return <GanchoSlide s={s} texto={gancho} />;
  const fotoIndice = indice - 1;
  return (
    <AbsoluteFill>
      <AutoSlide s={s} indice={fotoIndice} />
      {/* Solo en la portada: es la revelación real, el resto ya es el
          carrusel clásico sin agregados. */}
      {fotoIndice === 0 && <CtaComentario modelo={s.modelo} />}
    </AbsoluteFill>
  );
};
