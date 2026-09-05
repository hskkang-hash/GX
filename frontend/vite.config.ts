import react from '@vitejs/plugin-react-swc';
import autoprefixer from 'autoprefixer';
import { execFileSync } from 'node:child_process';
import path from 'path';
import { defineConfig, Plugin } from 'vite';
import svgr from 'vite-plugin-svgr';

/**
 * P-59 — **번들이 자기 커밋을 말한다.**
 *
 * 무엇이 이것을 만들었나 [사고 · 턴 D]
 * ------------------------------------
 * 프런트 빌드가 `exit 0` 을 냈고 그것을 「병합된 코드가 선다」로 읽었다. 그런데 빌드
 * 컨테이너의 `/app` 은 저장소를 물고 있지 않았고, 실제로 묶인 것은 **직전 턴의 사본**
 * 이었다. `exit 0` 은 **무엇이** 성공했는지 말하지 않는다 — 컴파일러가 통과시킨 것이
 * 우리가 고친 그 코드였는지는 종료 코드 밖의 사실이다.
 *
 * 그래서 답을 종료 코드가 아니라 **산출물 안**에 넣는다. 번들이 자기가 어느 커밋에서
 * 났는지 말하면, 낡은 사본은 사람 눈에도 게이트 눈에도 낡은 것으로 보인다.
 *
 * 어디서 커밋을 읽나 — **순서가 곧 판단이다**
 * -------------------------------------------
 *   ① `GX_COMMIT` / `VITE_GX_COMMIT` 환경 변수 — **명시가 추론을 이긴다.**
 *   ② `git rev-parse HEAD` — 저장소 위에서 도는 빌드(호스트)면 이것으로 충분하다.
 *   ③ 둘 다 없으면 **빈 값** → 화면과 머리표가 「알 수 없음」이라 적고,
 *      게이트 토큰은 **아예 안 나간다.**
 *
 * 무엇을 내보내나 — **읽는 사람이 둘이라 형태도 둘이다**
 * ---------------------------------------------------
 *   · 사람 — 화면 하단의 「버전 3d40cf6」. **짧은 형**이다. 전화로 불러 줄 수 있어야 한다.
 *   · 게이트 — 번들 안의 `GX_COMMIT:<40자리>` 리터럴. **온전한 형**이다.
 *     7자리는 다른 커밋과 부딪힐 수 있고, **부딪히는 신원은 신원이 아니다.**
 *
 * ★ ③ 이 이 파일의 요점이다. [실측 2026-09-05 · 빌드 컨테이너 안에서 두드림]
 *   `git` 실행 파일은 **있고**(`/usr/bin/git`) `.git` 이 **없다** — 우리가 넣는 것은
 *   `src` 와 이 파일뿐이기 때문이다. 즉 ②는 예외 없이 실패한다. 「git 이 깔려
 *   있으니 되겠지」는 이 자리에서 틀린 추측이다. 그 자리에서 **아무 해시나
 *   지어내면** 그것은 턴 D 의 거짓 초록을 판보다 더 나쁘게 되살린다: 그때는 아무도
 *   모른다고 했지만 이번에는 화면이 **틀린 것을 자신 있게** 말하게 된다.
 *   모르는 것은 모른다고 적는다.
 *
 * ⚠ 그러므로 컨테이너 빌드는 반드시 커밋을 **손으로 넣어야** 한다:
 *     docker exec -e GX_COMMIT=$(git rev-parse --short=7 HEAD) … npx vite build
 *   넣지 않으면 빌드는 서지만 「알 수 없음」이 뜨고, 번들 해시 게이트는 빨강이 된다.
 *   그것이 옳은 빨강이다 — 넣는 것을 잊은 빌드는 실제로 출처를 모르는 빌드다.
 */
function resolveCommitFull(): string {
  const fromEnv = (process.env.GX_COMMIT || process.env.VITE_GX_COMMIT || '').trim();
  // 환경 변수가 이긴다. 사람이 「이 커밋이다」라고 말한 것을 추론이 덮지 않는다.
  if (fromEnv) return fromEnv.toLowerCase();
  try {
    // ★ `execFileSync` 다 — 셸을 거치지 않는다. 셸을 거치면 이 한 줄이 주입 면이 된다.
    // ★ **온전한 40자리**를 받는다. 짧은 형은 여기서 잘라 쓴다 — 반대로는 못 한다.
    return execFileSync('git', ['rev-parse', 'HEAD'], {
      cwd: __dirname,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    })
      .trim()
      .toLowerCase();
  } catch {
    // git 이 없다 · .git 이 없다 · 이 자리가 저장소가 아니다 — 셋 다 「모른다」다.
    return '';
  }
}

/** 이 빌드가 난 커밋, 온전한 형. 빈 문자열은 **「모른다」이지 「없다」가 아니다.** */
const GX_COMMIT_FULL = resolveCommitFull();

/** 사람이 읽는 짧은 형. 화면은 이것으로 「버전 3d40cf6」이라 적는다. */
const GX_COMMIT_SHORT = GX_COMMIT_FULL.slice(0, 7);

/**
 * 게이트가 번들에서 찾는 **리터럴 토큰** (차선 Q 의 규약 ①).
 *
 * ★ 왜 접두어가 붙나 — [차선 Q 실측] 지금 번들에는 `[0-9a-f]{40}` 이 이미 두 군데
 *   걸린다. 둘 다 **긴 숫자 상수**다. 접두어 없이 40자리 16진을 찾는 게이트는
 *   남의 숫자를 커밋으로 읽고, 그 초록은 아무것도 맞추지 않는다.
 *
 * ★ 왜 **통째로 한 리터럴**인가 — 소스에서 `'GX_COMMIT:' + 해시` 로 이어 붙이면
 *   번들에 그 문장이 리터럴로 남는다는 보장이 없다(상수 접기·트리셰이킹). 그래서
 *   접두어까지 포함한 **완성된 글자**를 빌드가 넣는다. 화면 코드는 그것을 손대지 않는다.
 *
 * ★ 40자리가 아니면 **토큰을 아예 안 낸다.** 짧은 형으로 토큰을 내면 게이트가
 *   신원으로 삼을 수 없다 — 7자리는 다른 커밋과 부딪힐 수 있고, 부딪히는 신원은
 *   신원이 아니다. 그때 게이트는 「번들이 자기가 어느 커밋인지 말하지 않는다」로
 *   빨개진다. 그것이 옳은 빨강이다.
 *   ⚠ 그러므로 빌드에 넘기는 값은 **온전한 40자리**여야 한다:
 *       -e GX_COMMIT=$(git rev-parse HEAD)      ← `--short` 를 붙이지 말 것
 */
const GX_COMMIT_TOKEN = /^[0-9a-f]{40}$/.test(GX_COMMIT_FULL)
  ? `GX_COMMIT:${GX_COMMIT_FULL}`
  : '';

const stampCommit = (): Plugin => ({
  name: 'gx-stamp-commit',
  transformIndexHtml() {
    return [
      {
        tag: 'meta',
        attrs: { name: 'gx-commit', content: GX_COMMIT_FULL || 'unknown' },
        injectTo: 'head',
      },
    ];
  },
});

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
  plugins: [react(), svgr(), forceReactDomServerBrowser(), stampCommit()],
  define: {
    // Polyfill Node.js globals for browser
    'process.env': {},
    global: 'globalThis',
    // W0-4 — 데모·목업 화면 격리 플래그.
    // 빌드 시점에 true/false 리터럴로 치환되므로, 프로덕션 빌드
    // (VITE_ENABLE_DEMO 미설정)에서는 데모 분기 전체가 dead code 로 제거된다.
    // 라우트 등록도, 번들 청크도 남지 않는다.
    __DEMO_ENABLED__: JSON.stringify(process.env.VITE_ENABLE_DEMO === 'true'),
    // P-59 — 이 빌드가 난 커밋. 화면 하단 오른쪽이 짧은 형을 읽어 적는다.
    // 빈 문자열이면 화면은 「알 수 없음」이라 적는다 — 지어내지 않는다.
    __GX_COMMIT__: JSON.stringify(GX_COMMIT_SHORT),
    // 게이트가 번들 안에서 찾는 리터럴 토큰(차선 Q 규약 ①). 40자리가 아니면 빈 값이고,
    // 빈 값이면 `GX_COMMIT:` 이라는 글자가 번들에 **아예 안 남는다** — 말할 수 없는
    // 것을 말하지 않는 것이 이 자리의 정직이다.
    __GX_COMMIT_TOKEN__: JSON.stringify(GX_COMMIT_TOKEN),
    // UX-25 / P-61 — **지원 창구 한 줄.** 버전 옆에 선다.
    // 값은 배포하는 쪽이 준다(`GX_SUPPORT` 또는 `VITE_GX_SUPPORT`). 기본값을 두지
    // 않는 이유는 하나다: 여기에 전화번호를 적으면 그 번호가 곧 저장소에 적힌
    // 번호이고, 기관마다 다른 그 번호는 반드시 늙는다. 빈 값이면 화면은
    // 「지원 창구 미등록」이라 적는다 — 지어낸 번호보다 낫다(`버전 알 수 없음`과 같은 규약).
    __GX_SUPPORT__: JSON.stringify(
      (process.env.GX_SUPPORT || process.env.VITE_GX_SUPPORT || '').trim(),
    ),
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
