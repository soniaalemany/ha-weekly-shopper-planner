// Empaqueta src/ en un único módulo para el panel (CSS incluido como texto).
import { build, context } from 'esbuild';

const options = {
  entryPoints: ['src/panel.js'],
  bundle: true,
  format: 'esm',
  target: 'es2022',
  minify: true,
  loader: { '.css': 'text' },
  outfile: '../custom_components/weekly_shopper/frontend/weekly-shopper-panel.js',
  legalComments: 'none',
  logLevel: 'info',
};

if (process.argv.includes('--watch')) {
  const ctx = await context(options);
  await ctx.watch();
} else {
  await build(options);
}
