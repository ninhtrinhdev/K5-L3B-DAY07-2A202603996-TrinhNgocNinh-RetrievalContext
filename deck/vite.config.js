import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

// One self-contained dist/index.html (JS, CSS, fonts and data inlined) that opens from the file system.
// Figure crops stay as plain files in dist/crops/ and are referenced with relative URLs.
export default defineConfig({
  base: './',
  plugins: [viteSingleFile()],
  build: { target: 'es2020', assetsInlineLimit: 100000000, chunkSizeWarningLimit: 4000 },
});
