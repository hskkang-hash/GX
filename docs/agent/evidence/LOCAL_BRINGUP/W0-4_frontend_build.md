# W0-4 프론트 빌드 실측 — 2026-08-22 (RUNBOOK STEP 3)

## 환경
guardianx-frontend:latest 이미지의 node_modules(778패키지·rj-core·@gaion/gcs-fe 포함) 위에
저장소 frontend/ 소스를 덮어써서 빌드. node v18.20.8 / npm 10.8.2 / vite 5.4.21
NODE_OPTIONS=--max-old-space-size=6144 (기본 2GB 힙으로는 OOM — 최초 시도 FATAL ERROR: heap out of memory)

## 빌드 결과 (플래그 OFF = 프로덕션)
dist/index.html                                      1.43 kB │ gzip:     0.74 kB
dist/assets/index-CQL8V5xa.js                   16,138.30 kB │ gzip: 5,156.85 kB
✓ built in 50.81s

## W0-4 verify — 티켓 명령
$ npm run build && ! grep -rl "mockupDemoUi" dist/assets
build EXIT=0 / grep hits=0  →  PASS

## D-218 DoD — 게이트 유효성 (플래그 ON/OFF 대조)
$ VITE_ENABLE_DEMO=true npx vite build --outDir dist_demo

청크 수:  OFF=190  ON=196
ON 에서만 생기는 청크 (해시 제거 후):
  + DemoPage.js
  + DemoUrlPage.js
  + Panel.js
  + index.js
  + index.js
  + index.js
OFF 에서만 생기는 청크: (없음)

→ 게이트는 데모 6청크만 제거하고 다른 것은 건드리지 않는다. **유효하다.**

## ⚠ AUTHOR-ERROR (D-214) — 티켓의 verify 명령이 무력하다

식별자 grep 결과:
  식별자              OFF  ON
  mockupDemoUi           0    0
  MonitoringDashboard    0    0
  DisabillityDashborad   0    0

**플래그를 켠 빌드에서도 0건이다.** minify 가 식별자를 지우기 때문이다.
즉 `! grep -rl 'mockupDemoUi' dist/assets` 는 통과해도 아무것도 증명하지 않는다.
실효 검증은 **청크 이름 대조**다 (DemoPage.js / DemoUrlPage.js / Panel.js + index.js 3종).
정본 verify 를 이 방식으로 교체할 것을 요청한다.

## 부수 발견 1 — package-lock.json 회수 (W0-8)
이미지 /app/package-lock.json 을 금고로 회수: C:\GuardianX-vault\frontend-lockfile-20260210\
  lockfileVersion 3 / 2,384 패키지 / md5 9d919a08… (전체 값은 금고 파일에서 직접 확인 · 금지 #2)
  저장소 package.json 의 dependencies 80 + devDependencies 26 = **106건 전부 일치, 불일치 0**
→ W0-8 은 '사내망 필요' 가 아니다. 이 파일을 커밋하면 닫힌다. **커밋은 승인 대기.**

## 부수 발견 2 — 소스 결함 1건 (esbuild 경고)
  src/features/operationalNotice/pages/EditOperationalNotice.tsx:207
  Duplicate "disabled" attribute in JSX element  — 뒤엣것이 이깁니다. 고치지 않았다(FREEZE).

## 부수 발견 3 — 이미지에만 있던 잔재 파일
  src/assets/images/CheckIcon.svg — 저장소에 없다. 빌드 전 제거했다(빌드 결과에 영향 없음 확인).

---

# 부록 — W0-8 / W0-7 실측 (같은 컨테이너에서 이어서)

## W0-8 — 회수된 lockfile 로 `npm ci` 는 **그대로는 실패한다**

```
$ npm ci --dry-run
npm error code ERESOLVE
npm error Could not resolve dependency:
npm error peer react@"^0.14.0 || ^15.0.0 || ^16.0.0 || ^17.0.0 || ^18.0.0" from react-text-mask@5.5.0
npm error Conflicting peer dependency: react@18.3.1

$ npm ci --dry-run --legacy-peer-deps
added 108 packages in 4s          ← 통과
```

**W0-8 의 dod 는 "npm ci 가 성공한다" 이다. lockfile 만으로는 충족되지 않는다.**
`--legacy-peer-deps` 를 CI 명령에 넣거나, `react-text-mask` 를 걷어내야 한다 — 후자가 W0-7 이다.
**이미지의 `node_modules` 도 이 플래그(또는 `--force`)로 설치된 것**이라는 뜻이기도 하다.

## W0-7 — `react-text-mask` 는 react 19 를 지원하지 않는다 (선언상)

| 항목 | 실측 |
|---|---|
| 프로젝트 react | `^19.0.0` (실 설치 19.2.4) |
| `react-text-mask@5.5.0` peer 선언 | `^0.14 \|\| ^15 \|\| ^16 \|\| ^17 \|\| ^18` — **19 없음** |
| 사용처 | `src/components/Form/PhoneNumberInput.tsx:14` (`import MaskedInput from 'react-text-mask'`) |
| 대체 후보 존재 | `src/components/Form/PhoneNumberInputV2.tsx` — **react-text-mask 를 쓰지 않는다** |
| 빌드 통과 | **예** — 번들에 포함됨(`conformToMask`/`textMask` 검출 1건) |

> **빌드가 통과한다는 것이 동작한다는 뜻은 아니다.** react-text-mask 는 legacy ref/`findDOMNode`
> 계열 API 를 쓰는 것으로 알려져 있고, react 19 는 그중 일부를 제거했다. **런타임 확인이 W0-7 의 본체**이며
> 그것은 dev 서버를 띄우고 그 화면을 열어야 한다 — 이번 실행 범위 밖이다.
> 다만 **`PhoneNumberInputV2` 가 이미 있다**는 사실은 교체 경로가 이미 절반 열려 있음을 뜻한다.
