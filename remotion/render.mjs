/**
 * Renders every slide of one carousel from its `datos.json`.
 *
 *   node render.mjs <ruta/a/datos.json> <carpeta/de/salida> [indice]
 *
 * With `indice` it renders only that one slide (0-based) instead of the
 * whole carousel — `regenerar_gancho()` uses this for a new hook question
 * without re-rendering the photos.
 *
 * `ajustar.sh` calls this with no `indice`, for the whole carousel. It exists
 * because the CLI (`npx remotion still`) bundles the project and launches a
 * browser on every invocation, and a carousel is three of them: measured on
 * this machine, 9.9 s through the CLI against 5.4 s here, for byte-identical
 * PNGs. Bundling and the browser happen once, then the slides only differ in
 * their props.
 *
 * The output is the same as the CLI's because the props are: `{ s: datos,
 * indice: n }`, exactly what `--props` used to carry.
 */
import path from "path";
import { readFileSync } from "fs";
import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";
import { enableTailwind } from "@remotion/tailwind-v4";

const [rutaDatos, destino, soloIndiceArg] = process.argv.slice(2);
if (!rutaDatos || !destino) {
  console.error("Uso: node render.mjs <datos.json> <carpeta-de-salida> [indice]");
  process.exit(1);
}
const soloIndice = soloIndiceArg !== undefined ? Number(soloIndiceArg) : null;

const raiz = import.meta.dirname;
const datos = JSON.parse(readFileSync(rutaDatos, "utf8"));

// The same override as `remotion.config.ts`: the config file only applies to
// the CLI, so the Node API has to repeat it. If Tailwind or the `@` alias ever
// change there, they change here too — otherwise the renders drift apart.
//
// The filesystem cache is the other reason this is faster than the CLI: this
// process exits after every render (one per offer), so an in-memory cache
// would never survive to the next one. Webpack's own disk cache does --
// measured on this machine, 5.8 s cold, 1.3 s once the source hasn't changed
// since the last render. It lives in Cloud Run's instance disk, so it warms
// up after the first offer and stays warm for as long as that instance does.
const serveUrl = await bundle({
  entryPoint: path.join(raiz, "src/index.ts"),
  webpackOverride: (c) => {
    const conf = enableTailwind(c);
    return {
      ...conf,
      resolve: { ...conf.resolve, alias: { ...conf.resolve?.alias, "@": raiz } },
      cache: { type: "filesystem", cacheDirectory: path.join(raiz, ".webpack-cache") },
    };
  },
});

const browser = await openBrowser("chrome");
const etiqueta = path.basename(path.resolve(destino));

// `selectComposition` una sola vez, y no una por slide: medido en esta maquina
// cuesta ~1.1 s cada llamada, que en un carrusel de tres eran 3.4 s de los 7.7 s
// del render entero. Lo que hacia falta era resolver la composicion una vez y
// cambiarle `props` por slide: los props que llegan al componente son los de
// `composition.props`, y pasar solo `inputProps` a `renderStill` renderizaba el
// slide 0 tres veces —`2.png` salia copia byte a byte de `1.png`—, que es lo que
// habia hecho poner `selectComposition` dentro del bucle.
// "gancho" antepone un slide de intriga al carrusel clásico: un slide más
// que "Auto" (la misma cantidad de fotos, más el gancho). Cualquier otro
// valor, incluido faltante, es el carrusel clásico de siempre.
const esGancho = datos.formato === "gancho";
const id = esGancho ? "AutoGancho" : "Auto";
const total = esGancho ? 1 + datos.fotos.length : datos.fotos.length;

const base = await selectComposition({
  serveUrl,
  id,
  inputProps: { s: datos, indice: 0, gancho: datos.gancho ?? "" },
});

const rango = soloIndice !== null ? [soloIndice] : Array.from({ length: total }, (_, i) => i);

for (const i of rango) {
  const inputProps = esGancho
    ? { s: datos, indice: i, gancho: datos.gancho ?? "" }
    : { s: datos, indice: i };
  const salida = path.join(destino, `${i + 1}.png`);
  await renderStill({
    composition: { ...base, props: { ...base.props, ...inputProps } },
    serveUrl,
    inputProps,
    puppeteerInstance: browser,
    output: salida,
    overwrite: true,
    logLevel: "error",
  });
  console.log(`  ✓ Posts/${etiqueta}/${i + 1}.png`);
}

await browser.close({ silent: true });
