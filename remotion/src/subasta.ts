// ─────────────────────────────────────────────────────────────────────────────
// The auction being previewed right now.
//
// This is only an example for the Studio. Real carousels never edit it: the
// scripts and the studio feed Remotion through --props. No component carries
// hard-coded copy.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * One photo of the carousel.
 *
 * A bare string means centred with no zoom, which is what the scripts emit and
 * what every `datos.json` holds today. The long form is for when the crop to
 * 1080×1080 eats part of the car:
 *
 *   { src: "autos/x-1.jpeg", foco: "50% 35%", escala: 1.2 }
 *
 * `foco` is an `object-position` and moves the crop. `escala` zooms in, and it
 * does so around the focus point rather than the centre. Both are found by eye
 * in the studio (`./estudio.sh <slug>`); nobody guesses them blind.
 */
export type Foto = string | { src: string; foco?: string; escala?: number };

export type Subasta = {
  /** Make — the gradient title. Appears on the first photo only. */
  marca: string;
  /** Trim or model — sits above the make, in white. */
  modelo: string;
  /** Year in the card's short form: 19' */
  anio: string;
  transmision: string;
  /** Pre-formatted, currency included: the card computes nothing. */
  precioBase: string;
  fecha: string;
  hora: string;
  /** Official store selling it. Its initial goes in the avatar. */
  tienda: string;
  /**
   * Paths inside `public/`. Their order is the carousel order.
   * The first one is the cover: the only slide carrying make and model.
   */
  fotos: Foto[];
};

export const SUBASTA: Subasta = {
  marca: "Toyota",
  modelo: "Fortuner",
  anio: "25'",
  transmision: "Mecánica",
  precioBase: "US$ 34,999",
  fecha: "10/08",
  hora: "1:35 pm",
  tienda: "Maquisistema",
  fotos: ["autos/toyota1.png", "autos/toyota2.png", "autos/toyota3.png"],
};
