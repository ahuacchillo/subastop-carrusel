import { Composition } from "remotion";
import "./index.css";
import { POST } from "./brand/vmc";
import { AutoSlide } from "./posts/AutoSlide";
import { AutoGancho } from "./posts/GanchoSlide";
import { SUBASTA } from "./subasta";

/**
 * One composition for the whole carousel: `indice` decides which slide it is.
 *
 * The data arrives through props, not through the bundle. That is what lets
 * `nueva-subasta.sh` render a different auction without touching any code:
 *
 *   npx remotion still Auto --props=datos.json --output=…/2.png
 *
 * The Studio previews slide 0 with whatever `subasta.ts` holds; to see the
 * others, change `indice` in the props panel.
 *
 * The reels are a project of their own, in `reels/remotion/`.
 *
 * `AutoGancho` es una variación de 2 slides (gancho desenfocado → revelación
 * nítida), en paralelo a `Auto` — un experimento de engagement, no reemplaza
 * el flujo de 4 fotos.
 */
export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Auto"
      component={AutoSlide}
      defaultProps={{ s: SUBASTA, indice: 0 }}
      durationInFrames={1}
      {...POST}
    />
    <Composition
      id="AutoGancho"
      component={AutoGancho}
      defaultProps={{
        s: SUBASTA,
        indice: 0,
        gancho: "¿Reconoces qué auto se esconde aquí?",
      }}
      durationInFrames={1}
      {...POST}
    />
  </>
);
