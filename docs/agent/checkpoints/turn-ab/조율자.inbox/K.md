# K → 조율자 (턴 AB · Kick 온보딩 카드) · 2판

기계 시각: 2026-09-21 (호스트) · 보낸 차선 **K**
1판(도커 장애 신고)은 해소됐다 — 아래는 **그 뒤에 한 것**과 **아직 남은 것** 둘이다.

---

## ① 요청하신 두 줄 — 반영했다 (`Onboarding.tsx`)

```tsx
export function FirstCards({ chapter, kick }: { chapter?: string; kick?: KickView })
```

- **`export` 했다.** `KickView` · `KickCardView` 타입도 함께 내보낸다 — `Home.tsx` 에서
  `import { FirstCards, type KickView } from './Onboarding'` 로 쓰시면 된다.
- **두 번 두드리지 않는다.** `kick` 이 오면 제 요청을 **아예 안 건다**:
  `useDsmResource(..., { enabled: !kick })`. 「받아 놓고 버린다」가 아니라 요청 자체가 없다 —
  버리는 쪽으로 짜면 언젠가 누가 그 버린 값을 살려 쓰고, 그 순간 두 벌이 된다.
  `/start` 는 인자가 없으므로 지금처럼 제가 부른다.
- `chapter` 도 선택 인자로 바꿨다 — 홈에는 탭이 없다. 안 주면 페르소나 없이 제 역할 표다.
- **타입검사 통과**: `Onboarding.tsx` 걸린 줄 **0건** (§③).

## ② 시험 — **닫힘 3 이 섰다**

```
pytest tests/test_onboarding_progress.py::OnboardingKickCardsTest  → 13 passed (20.3s · rc=0)
pytest tests/test_onboarding_progress.py                           → 56 passed (68.4s · rc=0)
```
- **닫힘 시험 3** 전부 before/after 다(기록 없을 때 안 닫힘 → 심음 → 닫힘 + `source_ref` 대조).
  「언제나 None」 버그로는 뒤쪽 단언이 통과 못 한다.
- **음성 1** — 남에게 간 훈련 알림은 내 카드를 못 닫는다. **멱등 1** — 두 번 조회해도 행 하나.
- 기존 43건도 그대로 초록이다(파일 전체 56).

## ③ 덤으로 잰 것 둘 — **첫 진입 응답 3/3** · 타입검사

- **첫 진입**: `gxseed_u1_operator`·`u2_manager`·`u4_official` 로 **실제 로그인 200 →
  `GET /api/dsm/onboarding/progress` 200**(3/3). 세 역할 모두 기둥 셋이 오고 카드가 3장,
  U1 은 `event#231073`·U4 는 `report_run#1` 로 **이미 한 장씩 닫혀 있었다**.
  진행률은 안 흔들렸다(U1 3/3 · U2 1/3 · U4 1/1 — 전부 `CARDS` 만 센 수).
  자격은 `.env.gates` 의 `GX_SEED_ROLE_PASSWORD`(sha256[:12] `de08e1f17eb3`) —
  **argv 에도 셸 소싱에도 안 태웠다**(파일로 넣고 실행 뒤 지웠다). 로그인 3회 · 전환 61초.
- **타입검사**: 1651 → **1647**(정확히 −4) · `Onboarding.tsx` **0건**.

★ **타입검사에서 거짓 초록을 하나 밟았다 — 적어 두십시오.**
`npx tsc --noEmit` 만 부르면 `rc=0 · 오류 0` 이 나온다. `/app/tsconfig.json` 은 **107바이트
솔루션 파일**(`"files": []` + `references` 둘)이라 **아무것도 검사하지 않는다.** 기준선이
수천인데 0 이 나오는 것이 유일한 신호였다. **`-p tsconfig.app.json` 을 줘야** 실제로 돈다.
다른 차선이 같은 명령으로 「타입 오류 0」을 보고하면 그것은 잰 것이 아닙니다.

## ④ 아직 남은 것 하나 — **PNG 캡처 5장 전부 V 창** [회색 · 0 이 아니다]

3002 가 내주는 번들에 **이 턴의 프런트 변경이 없다** [실측]:
```
grep -rl "오늘 먼저 세 가지" /app/_fe_dist        → (없음)
grep -rl "첫 근무일에 혼자 시작하기" /app/_fe_dist → assets/Onboarding-CisVBX2j.js
```
지금 `/start` 를 찍으면 **첫 카드 셋이 없는 화면**이 찍힌다 — 그 장을 「첫 진입 캡처」라고
부르면 거짓 초록이다. **번들을 다시 굽지 않았다**: `gx-fe-build` 의 `/app/src` 를 통째로
덮으면 아홉 차선의 반쯤 된 코드를 함께 굽고, 공용 `_fe_dist` 를 갈면 다른 차선의 캡처가
바뀐다. 둘 다 제 소유 밖입니다.

⇒ **병합 뒤 번들을 새로 구운 다음** V 가 「첫 10분 화면 12」를 돌 때 다섯 장
(U1·U2·U4·U5·U6)을 함께 찍으면 됩니다. 문구 열쇠는 **`처음이세요 — 오늘 먼저 세 가지`**
(`KICK_HEADLINE`)와 `data-testid="onboarding-kick"` 입니다.

⚠ 타입검사를 하느라 **`gx-fe-build:/app/src/features/dsm/pages/Onboarding.tsx` 한 파일만**
제 판으로 덮어 두었습니다(다른 파일 0건). 병합 때 어차피 전체를 다시 넣으실 테니
문제 없겠지만, 알고 계시라고 적습니다.

## ⑤ 서버 상태 — 제가 세운 것 0 · 죽인 것 0

8000·3002 둘 다 그대로 살아 있습니다. 재기동도, 새로 세우기도 하지 않았습니다.
`v_lock.is_locked()` 가 False 인 것을 확인하고 로그인했습니다(V 세션을 끊지 않았습니다).
커밋 0.
