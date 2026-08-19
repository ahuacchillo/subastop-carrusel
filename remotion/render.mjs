/**
 * Renders every slide of one carousel from its `datos.json`.
 *
 *   node render.mjs <ruta/a/datos.json> <carpeta/de/salida>
 *
 * `ajustar.sh` calls this and nothing else does. It exists because the CLI
 * (`npx remotion still`) bundles the project and launches a browser on every
 * invocation, and a carousel is three of them: measured on this machine, 9.9 s
 * through the CLI against 5.4 s here, for byte-identical PNGs. Bundling and the
 * browser happen once, then the three slides only differ in their props.
 *
 * The output is the same as the CLI's because the props are: `{ s: datos,
 * indice: n }`, exactly what `--props` used to carry.
 */
import path from "path";
import { readFileSync } from "fs";
import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";
import { enableTailwind } from "@remotion/tailwind-v4";

const [rutaDatos, destino] = process.argv.slice(2);
if (!rutaDatos || !destino) {
  console.error("Uso: node render.mjs <datos.json> <carpeta-de-salida>");
  process.exit(1);
}

const raiz = import.meta.dirname;
const datos = JSON.parse(readFileSync(rutaDatos, "utf8"));

// The same override as `remotion.config.ts`: the config file only applies to
// the CLI, so the Node API has to repeat it. If Tailwind or the `@` alias ever
// change there, they change here too — otherwise the renders drift apart.
const serveUrl = await bundle({
  entryPoint: path.join(raiz, "src/index.ts"),
  webpackOverride: (c) => {
    const conf = enableTailwind(c);
    return {
      ...conf,
      resolve: { ...conf.resolve, alias: { ...conf.resolve?.alias, "@": raiz } },
    };
  },
});

const browser = await openBrowser("chrome");
const etiqueta = path.basename(path.resolve(destino));

for (let i = 0; i < datos.fotos.length; i++) {
  const inputProps = { s: datos, indice: i };
  // `selectComposition` runs once per slide on purpose. Hoisting it out of the
  // loop and passing `inputProps` to `renderStill` alone renders slide 0 three
  // times: the props that reach the component are the ones resolved here, and
  // `2.png` came out a byte-for-byte copy of `1.png`. It costs ~0.3 s a slide.
  const composition = await selectComposition({ serveUrl, id: "Auto", inputProps });
  const salida = path.join(destino, `${i + 1}.png`);
  await renderStill({
    composition,
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
