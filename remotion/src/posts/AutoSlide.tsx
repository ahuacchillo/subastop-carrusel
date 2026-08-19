import { AbsoluteFill, Img, staticFile } from "remotion";
import React from "react";
import {
  avatarFont,
  color,
  glassDenso,
  glassLigero,
  gradient,
  sans,
  shadow,
} from "../brand/vmc";
import type { Subasta } from "../subasta";

// ═════════════════════════════════════════════════════════════════════════════
// VMC Subastas carousel slide — 1080×1080
//
// One component for every photo of the car. The only things that change
// between the cover and the rest are the make+model block (`indice === 0`) and
// which arrows get drawn. Everything else repeats identically: that is what
// makes the carousel read as a single piece as you swipe.
//
// Coordinates are absolute against the 1080×1080 frame, exactly as the Figma
// spec gives them. No page-level flex: if Figma says x 45 / y 845, here it says
// left 45 / top 845, so render and design compare without translating a thing.
// ═════════════════════════════════════════════════════════════════════════════

/**
 * The 1.5px gradient border on any glass surface.
 *
 * Drawn as a separate layer with an `xor` mask: the gradient is painted across
 * the whole box and then the inside is punched out. It is the only way to get
 * a gradient border over a translucent fill without the gradient showing
 * through the middle.
 */
const BordeGlass: React.FC<{ radio: number | string }> = ({ radio }) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      borderRadius: radio,
      padding: 1.5,
      background: gradient.borde,
      WebkitMask:
        "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
      WebkitMaskComposite: "xor",
      maskComposite: "exclude",
      pointerEvents: "none",
    }}
  />
);

/** The arrows' chevron, cropped from the exported SVG (node 7340:30566). */
const Flecha: React.FC<{ hacia: "izq" | "der" }> = ({ hacia }) => (
  <div
    style={{
      position: "absolute",
      // The right one at x 942.42; the left is its mirror against the frame.
      left: hacia === "der" ? 942.42 : 1080 - 942.42 - 92.386,
      top: 515.22,
      width: 92.386,
      height: 92.386,
      borderRadius: "50%",
      ...glassLigero,
    }}
  >
    <BordeGlass radio="50%" />
    {/* The viewBox crops the original circle so the chevron lands centred. */}
    <svg
      viewBox="24 16 92.386 92.386"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
    >
      <path
        d={
          hacia === "der"
            ? "M59.5918 47.1344L80.122 62.5321L59.5918 77.9297"
            : "M80.7949 47.1344L60.2648 62.5321L80.7949 77.9297"
        }
        stroke="white"
        strokeWidth="5.13254"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  </div>
);

/** The price pin on the data card. */
const IconoPrecio: React.FC = () => (
  <svg width={46} height={66} viewBox="0 0 46 66" fill="none" style={{ flexShrink: 0 }}>
    <path
      d="M23 3C15.3 3 9 9.3 9 17c0 9 14 29 14 29s14-20 14-29c0-7.7-6.3-14-14-14z"
      stroke={color.naranja}
      strokeWidth="3.2"
      strokeLinejoin="round"
    />
    <text
      x="23"
      y="23"
      textAnchor="middle"
      fill={color.violeta}
      fontFamily={sans}
      fontWeight={800}
      fontSize="16"
    >
      $
    </text>
    <rect x="2" y="53" width="42" height="13" rx="6.5" fill={color.violeta} />
  </svg>
);

const Header: React.FC<{ tienda: string }> = ({ tienda }) => (
  <div
    style={{
      position: "absolute",
      left: 44.875,
      top: 49.02,
      width: 372,
      height: 104,
      borderRadius: 13.955,
      display: "flex",
      alignItems: "center",
      gap: 14,
      paddingLeft: 16.5,
      boxSizing: "border-box",
      ...glassLigero,
    }}
  >
    <BordeGlass radio={13.955} />
    <div
      style={{
        width: 67.307,
        height: 67.307,
        borderRadius: "50%",
        background: gradient.avatar,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: avatarFont,
        fontWeight: 700,
        // The spec says 65.44px, but that is the text layer's height, not the
        // body size: at 65 the letter bursts the circle. 42 is what you see.
        fontSize: 42,
        letterSpacing: "0.5235px",
        color: color.white,
        lineHeight: 1,
        paddingBottom: 3,
      }}
    >
      {tienda.charAt(0).toUpperCase()}
    </div>
    <div style={{ fontFamily: sans, color: color.white, textShadow: shadow.textHeader }}>
      <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: "0.2px" }}>
        Tienda oficial
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: "0.224px" }}>
        {tienda}
      </div>
    </div>
  </div>
);

/**
 * Make + model, anchored right at x 1009.56.
 *
 * The two blocks overlap on purpose: the model starts at y 42 and is 94 tall,
 * and the make starts at y 94. That ~42px overlap is the design, not a
 * positioning mistake — pulling them apart breaks the visual close.
 */
const Titulo: React.FC<{ marca: string; modelo: string }> = ({ marca, modelo }) => (
  <>
    <div
      style={{
        position: "absolute",
        right: 1080 - 1009.56,
        top: 42,
        fontFamily: sans,
        fontWeight: 700,
        fontSize: 70,
        lineHeight: 1.34,
        color: color.inverse,
        textShadow: shadow.textNombre,
        whiteSpace: "nowrap",
      }}
    >
      {modelo}
    </div>
    <div
      style={{
        position: "absolute",
        right: 1080 - 1009.56,
        top: 94,
        fontFamily: sans,
        fontWeight: 800,
        fontSize: 116,
        letterSpacing: "-3px",
        lineHeight: 1.26,
        whiteSpace: "nowrap",
        // The gradient goes over the type, not behind it: bg-clip-text.
        backgroundImage: gradient.titulo,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
        // With text-shadow the shadow would be clipped along with the fill.
        filter: "drop-shadow(0px 3px 12px rgba(0,0,0,0.4))",
      }}
    >
      {marca}
    </div>
  </>
);

const Fecha: React.FC<{ fecha: string; hora: string }> = ({ fecha, hora }) => (
  <div
    style={{
      position: "absolute",
      left: 45,
      top: 778.25,
      width: 353,
      height: 51,
      borderRadius: 87.319,
      overflow: "hidden",
      background: gradient.fecha,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      fontFamily: sans,
      fontWeight: 500,
      fontSize: 25.682,
      letterSpacing: "0.2568px",
      lineHeight: 1.44,
      color: color.inverse,
    }}
  >
    <span>Subasta {fecha}</span>
    <span style={{ opacity: 0.85 }}>|</span>
    <span>{hora}</span>
  </div>
);

const TarjetaDatos: React.FC<{ s: Subasta }> = ({ s }) => (
  <div
    style={{
      position: "absolute",
      left: 45,
      top: 845,
      width: 466,
      height: 176,
      borderRadius: 11.826,
      boxSizing: "border-box",
      padding: "15px 23px 19px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
      fontFamily: sans,
      color: color.white,
      textShadow: shadow.textCard,
      whiteSpace: "nowrap",
      // ponytail: line-height 1 across the block. With the browser's `normal`
      // the three large lines add up to a ~183px box inside a 176px card:
      // `space-between` runs out of air and "Precio base" ends up glued to the
      // bottom edge. With the box tight to the body size the card gets back the
      // ~20px of breathing room the spec asks for.
      lineHeight: 1,
      ...glassDenso,
    }}
  >
    <BordeGlass radio={11.826} />

    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
      <span style={{ fontSize: 43.665, fontWeight: 700, letterSpacing: "-0.3493px" }}>
        {s.marca} {s.anio}
      </span>
      <div style={{ width: 1.5, height: 36.387, background: "rgba(255,255,255,0.65)" }} />
      <span style={{ fontSize: 18.403, fontWeight: 700, letterSpacing: "-0.1472px" }}>
        {s.modelo}
      </span>
    </div>

    {/*
      `space-between`: transmission sits hard left and the price block hard
      right, with no magic numbers. That is what lets it take "Automática" or a
      five-figure price without anything needing a nudge.
    */}
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span style={{ fontSize: 22.742, fontWeight: 600, letterSpacing: "0.1819px" }}>
        {s.transmision}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <IconoPrecio />
        <div
          style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}
        >
          <span style={{ fontSize: 43.665, fontWeight: 700, letterSpacing: "-0.3493px" }}>
            {s.precioBase}
          </span>
          <span style={{ fontSize: 22.742, fontWeight: 600, letterSpacing: "-0.1819px" }}>
            Precio base
          </span>
        </div>
      </div>
    </div>
  </div>
);

export const AutoSlide: React.FC<{
  s: Subasta;
  /** 0-indexed. Slide 0 is the cover: the only one carrying make and model. */
  indice: number;
}> = ({ s, indice }) => {
  // The defaults are the long-standing behaviour: centred crop, no zoom.
  // That is why a photo may still be a bare string.
  const f = s.fotos[indice];
  const { src, foco = "50% 50%", escala = 1 } =
    typeof f === "string" ? { src: f } : f;

  return (
    <AbsoluteFill
      style={{
        background: color.white,
        overflow: "hidden"
      }}>
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: foco,
          // With no zoom, no `transform` is emitted: even a `scale(1)` promotes
          // the image to its own layer and Chrome rasterises it differently.
          // This way an unframed photo comes out byte for byte as it did before
          // any of this existed. Tying the origin to the focus makes the zoom
          // close in on the point you picked, not on the centre.
          ...(escala === 1
            ? {}
            : { transform: `scale(${escala})`, transformOrigin: foco }),
        }} />
      <Header tienda={s.tienda} />
      {indice === 0 && <Titulo marca={s.marca} modelo={s.modelo} />}
      {indice > 0 && <Flecha hacia="izq" />}
      {indice < s.fotos.length - 1 && <Flecha hacia="der" />}
      <Fecha fecha={s.fecha} hora={s.hora} />
      <TarjetaDatos s={s} />
      <Img
        src={staticFile("brand/vmc-logo.svg")}
        style={{
          position: "absolute",
          left: 855.29,
          top: 952.32,
          width: 179.51,
          height: 66.69,
        }}
      />
    </AbsoluteFill>
  );
};
