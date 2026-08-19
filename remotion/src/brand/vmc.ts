// ─────────────────────────────────────────────────────────────────────────────
// VMC Subastas brand kit — VOYAGER Design System.
//
// A literal transcription of the pixel-perfect spec for frame 51 (node
// 7340:30564). Every number here came out of Figma. When Figma changes, this
// changes: components carry no constants of their own.
//
// The carousel's half of the kit. The reel's lives in
// `reels/remotion/src/brand/vmc.ts` and holds the tokens the reel needs.
// A few definitions are in both files by necessity — `sans`, `gradient.borde`,
// `shadow.glassInset`. Change one of those and change the other in the same
// commit, or the two products drift apart.
// ─────────────────────────────────────────────────────────────────────────────

import { loadFont as loadJakarta } from "@remotion/google-fonts/PlusJakartaSans";
import { loadFont as loadRoboto } from "@remotion/google-fonts/Roboto";

export const { fontFamily: sans } = loadJakarta("normal", {
  weights: ["500", "600", "700", "800"],
  subsets: ["latin"],
});

/** Only for the letter inside the seller's avatar. */
export const { fontFamily: avatarFont } = loadRoboto("normal", {
  weights: ["700"],
  subsets: ["latin"],
});

export const color = {
  /** text/neutral-inverse — type over photos. Not pure white. */
  inverse: "#FCFAFA",
  white: "#FFFFFF",
  naranja: "#ED8936",
  violeta: "#8460E5",
  violetaClaro: "#AE8EFF",
  indigo: "#5A35C2",
  indigoProfundo: "#2E0F70",
} as const;

export const shadow = {
  /** Glass elevation — every surface shares it. */
  glass: "0px 8px 24px rgba(0,0,0,0.1)",
  /** The glass's inner light edge. */
  glassInset: "inset 0px 1px 6px rgba(255,255,255,0.45)",
  /** TextW3C — type inside a card. */
  textCard: "0px 1px 3px rgba(0,0,0,0.25)",
  textHeader: "0px 1px 3px rgba(0,0,0,0.5)",
  /** Trim name over a photo (Glory). */
  textNombre: "0px 3px 12px rgba(0,0,0,0.8)",
  /** Make title over a photo (DFSK). */
  textMarca: "0px 3px 12px rgba(0,0,0,0.4)",
} as const;

export const gradient = {
  /** VYPrimaryDefault2 applied to the make title (bg-clip-text). */
  titulo:
    "linear-gradient(123.41deg, #FFFFFF 0%, #ED8936 22%, #8460E5 75%, #FFFFFF 100%)",
  /** The auction-date pill. */
  fecha:
    "linear-gradient(149.88deg, #ED8936 0%, #ED8936 40%, #8460E5 100%)",
  /**
   * The border on glass surfaces. The spec calls it VYStrokes1, "white 1.5px",
   * but the exported SVGs (the arrows) carry this gradient and that is what the
   * render shows: white top-left, orange, violet, white.
   */
  borde:
    "linear-gradient(135deg, #FFFFFF 0%, #F4AC59 22%, #8460E5 74.5%, #FFFFFF 100%)",
  /** The seller avatar's surface. */
  avatar: "linear-gradient(149.88deg, #ED8936 0%, #8460E5 100%)",
} as const;

/**
 * The glass recipe: the spec's two stacked fills.
 *
 * The gradient border does NOT belong here. A third `background` with
 * `border-box` would show through the fills, which are translucent, and tint
 * the whole card orange and violet. It goes separately, in `<BordeGlass>`,
 * clipped with a mask.
 *
 * `tail` is the only thing that differs between the system's two variants:
 *   - header and arrows → transparent (blur 5)
 *   - data card → #717171 grey at 50% (blur 20), more opaque so it reads on
 *     top of any photo.
 */
export const glass = (blur: number, tail: string) =>
  ({
    backdropFilter: `blur(${blur}px)`,
    WebkitBackdropFilter: `blur(${blur}px)`,
    background: [
      `linear-gradient(180deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.08) 45%, ${tail} 100%)`,
      "linear-gradient(180deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.08) 45%, rgba(255,255,255,0.03) 100%)",
    ].join(", "),
    boxShadow: `${shadow.glass}, ${shadow.glassInset}`,
  }) as const;

/** Light glass — the seller header and the carousel arrows. */
export const glassLigero = glass(5, "rgba(255,255,255,0)");
/** Dense glass — the car's data card. */
export const glassDenso = glass(20, "rgba(113,113,113,0.5)");

export const POST = { width: 1080, height: 1080, fps: 30 } as const;
