/**
 * Note: When using the Node.JS APIs, the config file
 * doesn't apply. Instead, pass options directly to the APIs.
 *
 * All configuration options: https://remotion.dev/docs/config
 */

import path from "path";
import { Config } from "@remotion/cli/config";
import { enableTailwind } from '@remotion/tailwind-v4';

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// `@/...` is what the Concorde CLI writes into the components it installs.
// The bundler does not read tsconfig paths, so the alias lives here too.
Config.overrideBundlerConfig((c) => {
  const conf = enableTailwind(c);
  return {
    ...conf,
    resolve: {
      ...conf.resolve,
      alias: { ...conf.resolve?.alias, "@": path.resolve(process.cwd()) },
    },
  };
});
