import react from '@vitejs/plugin-react-swc';
import autoprefixer from 'autoprefixer';
import path from 'path';
import { defineConfig, Plugin } from 'vite';
import svgr from 'vite-plugin-svgr';

// Plugin to force react-dom/server to use browser version
const forceReactDomServerBrowser = (): Plugin => ({
  name: 'force-react-dom-server-browser',
  enforce: 'pre',
  resolveId(id) {
    if (id === 'react-dom/server' || id === 'react-dom/server.js') {
      return this.resolve('react-dom/server.browser', undefined, {
        skipSelf: true,
      });
    }
  },
});

export default defineConfig({
  plugins: [react(), svgr(), forceReactDomServerBrowser()],
  define: {
    // Polyfill Node.js globals for browser
    'process.env': {},
    global: 'globalThis',
    // W0-4 — 데모·목업 화면 격리 플래그.
    // 빌드 시점에 true/false 리터럴로 치환되므로, 프로덕션 빌드
    // (VITE_ENABLE_DEMO 미설정)에서는 데모 분기 전체가 dead code 로 제거된다.
    // 라우트 등록도, 번들 청크도 남지 않는다.
    __DEMO_ENABLED__: JSON.stringify(process.env.VITE_ENABLE_DEMO === 'true'),
  },
  ssr: {
    noExternal: ['react-dom'],
  },
  server: {
    host: '0.0.0.0',
    port: 3002,
    cors: true,
    allowedHosts: true,
    watch: {
      ignored: [
        '**/node_modules/**',
        '**/dist/**',
        '**/.git/**',
        '**/coverage/**',
        '**/.nyc_output/**',
        '**/tmp/**',
        '**/temp/**',
      ],
      usePolling: process.env.VITE_USE_POLLING === 'true',
      interval: process.env.VITE_USE_POLLING === 'true' ? 1000 : undefined,
      depth: process.env.VITE_USE_POLLING === 'true' ? 3 : undefined,
    },
    timeout: 120000,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      assets: path.resolve(__dirname, 'src/assets'),
      locale: path.resolve(__dirname, 'src/locale'),
      '@GCS': path.resolve(__dirname, 'node_modules/@gaion/gcs-fe/src'),
      '@GCS/styles': path.resolve(
        __dirname,
        'node_modules/@gaion/gcs-fe/src/pages/flight/styles',
      ),
      // Force GCS to use GuardianX's React instances
      react: path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
      'react-dom/server': path.resolve(
        __dirname,
        'node_modules/react-dom/server.browser',
      ),
      'react-dom/server.js': path.resolve(
        __dirname,
        'node_modules/react-dom/server.browser',
      ),
      'react/jsx-runtime': path.resolve(
        __dirname,
        'node_modules/react/jsx-runtime',
      ),
      'react/jsx-dev-runtime': path.resolve(
        __dirname,
        'node_modules/react/jsx-dev-runtime',
      ),
    },
    conditions: ['browser', 'default'],
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-dom/server.browser',
      'react-router-dom',
      '@yudiel/react-qr-scanner',
      'rj-core',
      'react-leaflet',
      'leaflet',
    ],
    // reduce file watching
    entries: ['src/main.tsx'],
    // force pre-bundling to reduce file watching
    force: false,
    // Exclude problematic dependencies
    exclude: ['@ckeditor/ckeditor5-build-classic', 'video.js', 'hls.js'],
    // Force deduplication of React
    dedupe: ['react', 'react-dom', 'react-leaflet'],
    // Node.js module polyfills for browser
    esbuildOptions: {
      define: {
        global: 'globalThis',
      },
    },
  },
  css: {
    postcss: {
      plugins: [autoprefixer],
    },
    preprocessorOptions: {
      scss: {
        // Use modern Sass API
        api: 'modern-compiler',
      },
    },
  },
  // build configuration to optimize for production
  build: {
    // reduce chunk size to avoid too many files
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
        },
      },
    },
  },
});
