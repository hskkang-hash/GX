# P-334 증거 — `gen-schema` 호출자 표 (422 ×37) (2026-09-25 · 차선 U)

## 0. 한 줄

`frontend/src` 를 아무리 뒤져도 **부르는 코드는 0건**이다 — 부르는 코드는
전부 **`rj-core`**(인수 자산 · §0.4 · 저장소 밖 git 의존)에 있고, `frontend/
src` 는 그 안의 훅·컴포넌트를 **가져다 마운트**할 뿐이다. `rj-core/dist` 번들
(`gx-fe-build` 컨테이너 `/app/node_modules/rj-core/dist/rj-core.es.js`)을
직접 읽어 실제 호출부 넷을 찾았다.

## 1. 엔드포인트 둘 — 이름이 같은 게 아니라 **둘 다 있다**

`rj-core` 가 스스로 쥔 API 표(우리 `frontend/src/services/API.ts` 와 같은
모양의 표가 번들 안에 한 벌 더 있다)에 이렇게 적혀 있다:

```
genConfig:      "/api/config-management/gen-schema"
genGroupConfig: "/api/user-groups/gen-schema"
```

우리 저장소(`frontend/src/services/API.ts:617`)에는 `genGroupConfig` 이름만
**정의**돼 있고 그것을 부르는 코드는 `frontend/src` 안에 없다 — 그 이름을
실제로 쓰는 쪽은 `rj-core` 자신의 번들이다(두 벌이 같은 문자열을 따로 들고
있다 · D-369 성격의 중복이지만, `rj-core` 는 §0.4 금지구역이라 이 차선이
합칠 수 없다).

## 2. 실제 호출부 넷 (`rj-core.es.js` 안)

| # | 부르는 함수(원문 그대로, 난독 이름) | 엔드포인트 | 무엇을 보내나 |
|---|---|---|---|
| ① | `C8().detailConfig` | `GET /api/config-management/gen-schema` | `{ id }` |
| ② | `C8().detailConfigGroup` | `GET /api/user-groups/gen-schema` | `{ group_id }` |
| ③ | `C8().listConfigGroup` | `GET /api/user-groups/gen-schema` | `{ group_id, raw: true }` |
| ④ | `Pe()`(= 내보낸 훅 `useConfigGroupSystem`) 의 `fetchFreshConfigGroup` | ③(`listConfigGroup`) 을 그대로 부른다 | 위와 같음 |

`C8` 은 파일 안의 서비스 팩토리(내보내지지 않음) — `detailConfig` ·
`detailConfigGroup` · `listConfigGroup` 등을 한 객체로 묶어 돌려준다.

## 3. 누가 ①~④ 를 켜는가 — 진짜 진입점은 **`ConfigSystemProvider`**

```js
QS0 = ({ children }) => {
  const [, , , e] = u5();                         // u5 = useConfigSystem
  const { configGroupSystem: i, fetchFreshConfigGroup: c } = Pe();  // Pe = useConfigGroupSystem
  useEffect(() => { e(); }, []);
  useEffect(() => {
    if (인증됨 && profile__group_id 있음 && !i) c(profile__group_id);
  }, [n, i, r]);
  ...
}
```

`QS0` 은 `rj-core` 가 내보내는 **`ConfigSystemProvider`** 다. 그리고 이
저장소 쪽에서:

```
frontend/src/App.tsx:21   ConfigSystemProvider,   ← 'rj-core' 에서 import
frontend/src/App.tsx:1326  <ConfigSystemProvider> … </ConfigSystemProvider>
```

**앱 전체를 이 프로바이더가 감싼다.** 로그인한 사용자가 있고 `profile__
group_id` 가 있고 아직 `configGroupSystem` 을 못 채웠으면(`!i`) 화면마다가
아니라 **세션당 한 번** `listConfigGroup(group_id)` → `GET /api/user-groups/
gen-schema?group_id=...&raw=true` 를 쏜다. 이것이 걷기·캡처 세션에서
「422 ×37」로 쌓인 진짜 발생원으로 가장 유력하다 — `group_id` 가 없거나
그 그룹에 대응하는 스키마가 없는 계정(시드·탐침 계정 다수가 여기 해당할
수 있다)마다 한 번씩 422 를 내고, 세션 수만큼(역할별 걷기 × 화면별 재마운트)
누적된다.

`EditConfig`(`rj-core` 의 내보낸 이름, 번들 안 `OS0`) 도 같은 `C8()` 의
`detailConfig`(①, `genConfig` 쪽)를 직접 부르고, 이 컴포넌트도
`frontend/src/App.tsx:24,865` 에서 라우트에 물려 있다 — ①의 두 번째
진입점이다. `②`(`detailConfigGroup`)는 번들 내부의 내보내지지 않은 컴포넌트
(`tD0`, 사용자관리류 그룹/부서 탭으로 보인다)에서 직접 불린다.

## 4. `frontend/src` 쪽 — 훅을 들여오지만 fetch 는 직접 안 부른다

| 파일 | 들여오는 것 | 실제로 하는 일 |
|---|---|---|
| `frontend/src/App.tsx` | `ConfigSystemProvider`, `ConfigManagement`, `EditConfig` | 루트를 감싸고(①·④의 실제 방아쇠) 라우트에 `EditConfig` 를 건다(①) |
| `frontend/src/components/maps/Map.tsx` | `useConfigGroupSystem` | `configGroupSystem` **읽기만** 한다(`use_map.select_map.google_map` 판독) — fetch 를 직접 트리거하지 않는다 |
| `frontend/src/components/maps/MapAnYang.tsx` | 위와 동일 | 위와 동일 |
| `frontend/src/components/HelperCellOperatingTime.tsx` | `useConfigSystem` | `configSystem` 상태만 읽는다(`u5()` 의 0번째 값) — gen-schema 가 아니라 `configManagementDev` 쪽 상태다 |

## 5. 결론 — 이 차선이 손댈 수 있는 자리인가

`gen-schema` 호출부 넷(§2)과 그 방아쇠(`ConfigSystemProvider`, §3)는 전부
**`rj-core`** 안이다 — §0.4 금지구역이고 이 차선의 편집 허용 목록
(`scripts/verify_onboarding_walk.py` 와 그 시험, `docs/agent/evidence/
P-350·P-334`)에도 없다. 이 표는 **누가 부르는지**만 확정한다 — 422 를
없애려면 (a) `rj-core` 쪽에서 `group_id` 없음/스키마 없음을 422 대신 다른
값으로 내려주게 고치거나, (b) 이 앱 쪽에서 `profile__group_id` 가 없는
계정(시드·탐침류)에는 `ConfigSystemProvider` 의 두 번째 effect 를 안 태우게
하는 조건을 앱 계층에 추가하는 두 갈래가 있고, 어느 쪽이든 이 차선의 범위
밖이라 다음 손(§0.4 담당 차선 또는 대표)에 넘긴다.
