# P-58 — 「한글 IME 상태 재현 시험 1」 · **모형에 대한 재현이지 브라우저 실측이 아니다**

- 집행: 차선 S · **2026-09-05 턴 E** · 근거: 세종 판정 P-58
- 파일: `scripts/verify_wall_keys.py` (술어 **⑦** 추가) · `backend/tests/test_s_ime_keys.py`(새)

---

## 1. 무엇을 세웠나 — 정적 판정기로는 못 보는 자리가 있었다

턴 D 의 술어 ①은 「소스 어딘가에 `.code` 를 **읽는** 자리가 있는가」를 센다.
그것으로는 이 모양을 못 잡는다 — 그리고 이 모양이 **「물리 키로 고쳤다」는 보고가
남기는 가장 흔한 잔해**다:

```js
const slot = ev.code;                  // 읽기는 읽는다  → 술어 ① **초록**
trace('key pressed', slot);
switch (ev.key) { case 'j': ... }      // 그런데 고르는 것은 **글자** → 관제실에서 죽는다
```

**실측으로 보였다** — 같은 소스에 두 술어를 함께 돌렸다:

```
술어① : **PASS — 초록으로 본다**
술어⑦ : ★ 배선이 **글자(event.key)로 고른다** — 한글 입력기가 켜지는 순간 … (P-58)
술어⑦ : 한글 입력기가 켜지면 죽는 자리 4개: KeyJ · KeyK · KeyM · KeyR
          (영문 자판에서는 **전부 먹는다** — 그래서 아무도 재현하지 못한다)
```

★ **넷은 죽고 넷은 산다.** 입력기는 숫자열과 Enter 를 바꾸지 않는다 —
그래서 고장이 부분적이고, 그래서 「가끔 안 먹는다」로만 보고된다.
그 비대칭 자체를 `test_the_failure_is_partial_and_that_is_the_trap` 이 못박는다.

## 2. 브라우저 없이 **어떻게** 쟀나 — 세 단계

1. 소스에서 **배선**을 뽑는다 — `switch` 가 무엇을 받고(`extract_dispatch`), case 라벨이 무엇인가
2. 한글 입력기가 켜진 상태의 **키 이벤트 모형**을 만든다 (`KEY_WHEN_IME_ON`)
3. 그 이벤트를 배선에 흘려 보내 **먹는지** 본다 (`dispatch`)

모형의 근거는 `IME_MODEL_BASIS` 에 셋으로 적었다(두벌식 낱자 · `code` 는 자리 ·
숫자열은 안 바뀜). **모형이 틀리면 이 술어도 틀린다** — 그래서 다음 항이 있다.

## 3. **못 잰 것** — 다음 사람이 브라우저에서 확인할 것 3줄 (`BROWSER_TODO`)

1. 한글 입력기가 켜진 채 **입력칸 밖**에서 `j` 를 눌렀을 때 `ev.isComposing` 이 참인가.
   참이면 `useQueueKeys.ts` 의 `if (ev.isComposing) return;` **한 줄이 단축키를 전부
   삼킨다** — 물리 키로 바꾼 것과 **무관하게** 죽는다.
2. 그때 `ev.code` 가 정말 `'KeyJ'` 로 오는가 (일부 입력기는 keydown 을 keyCode 229 로만
   올린다고 알려져 있다).
3. 월 모드처럼 **초점이 아무 데도 없는** 화면에서 window 리스너가 그 keydown 을 받는가.

⚠ 1번은 **지금 제품 코드에 실제로 있는 줄**이다(`useQueueKeys.ts`). 이 판정기는 그 줄이
있다는 것까지만 알고, 브라우저가 `isComposing` 을 어떻게 세우는지는 **모른다.**
`frontend/` 는 차선 S 의 것이 아니므로 고치지도 않았다 — **조율자 배선/판정 필요.**

## 4. 이 컨테이너는 `frontend/` 를 못 읽는다 — 그것도 실측이다

```
[실측] gx-shell 마운트 넷:  /repo/scripts(ro) · /app(=backend) · /docs · /repo/backend(ro)
       frontend 는 **없다**
```

그래서 역할을 갈랐다:

| 어디서 | 무엇을 재나 |
|---|---|
| `scripts/verify_wall_keys.py` (호스트) | **제품 소스** `useQueueKeys.ts` 를 ⑦로 판정 |
| `backend/tests/test_s_ime_keys.py` (컨테이너) | 술어 ⑦이 옳은가(양성·음성) · ⑦이 게이트에 실려 있는가 |

시험은 제품 소스를 못 읽으면 **조용히 넘어가지 않는다** — ⑦이 `CHECKS` 에 실려
`keys`(=`useQueueKeys.ts`)를 보고 있다는 것을 확인하고서야 넘어간다. 실려 있지 않으면
빨개진다(`ProductSourceTest`).

## 5. 명령과 수

```
python scripts/verify_wall_keys.py --self-test   → 양성 7 · 음성 13 통과
python scripts/verify_wall_keys.py               → 술어 7/7 통과 (⑦ 포함)

docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  DB_TEST_NAME=test_gx_sec python -m pytest tests/test_s_ime_keys.py -q \
  --nomigrations -p no:randomly --tb=short 2>/dev/null'
→ 12 passed
```

★ 출생 표본(D-310)은 이미 `BAD_KEYS_IME_ONLY_KEY` 로 박혀 있었고, 이번에 **둘째
표본** `BAD_KEYS_READS_CODE_BUT_SWITCHES_ON_KEY` 를 더했다 — 주석에 「출생 표본」과
그 표본이 태어난 이유를 적었다.
