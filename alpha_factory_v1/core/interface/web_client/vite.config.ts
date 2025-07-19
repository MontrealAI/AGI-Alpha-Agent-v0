// SPDX-License-Identifier: Apache-2.0
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [react(), vue()],
  root: '.',
  envPrefix: 'VITE_',
  appType: 'spa',
  server: {
    historyApiFallback: {
      index: '/index.html',
      disableDotRule: true,
    },
  },
  preview: {
    historyApiFallback: {
      index: '/index.html',
      disableDotRule: true,
    },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        assetFileNames: 'assets/[name].[hash].[ext]'
      }
    }
  }
});
