const { PHASE_DEVELOPMENT_SERVER } = require("next/constants");

/**
 * Keep dev and production build artifacts separate.
 * This prevents chunk/cache corruption when `next dev` and `next build/start`
 * are used in the same workspace.
 */
module.exports = (phase) => {
  const isDevServer = phase === PHASE_DEVELOPMENT_SERVER;

  /** @type {import('next').NextConfig} */
  const nextConfig = {
    distDir: isDevServer ? ".next-dev" : ".next",
    output: isDevServer ? undefined : "export",
  };

  return nextConfig;
};
