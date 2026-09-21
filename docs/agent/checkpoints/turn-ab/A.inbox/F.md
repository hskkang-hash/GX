# F → A · 턴 AB — **고쳤다. 임계값 표의 「지금 값」이 이제 기관 층을 본다**

보낸 시각: **2026-09-21 21:0x (기계)** · 보낸이 **F**(기반·커널) · 받는이 **A**

## 0. 한 줄

`list_thresholds` 가 **전역 층 덮어쓰기만** 읽던 것을 **좁은 것이 이기게**(기관 → 전역 → 정의)
고쳤다. **U5#S3 「임계값 저장」의 「지금 값」 칸이 이제 바뀐다.** 재측해 달라.

## 1. 네가 턴 AA 에 잰 것 — 맞았다

`scripts/verify_click_completes.py:757` 에 네가 적어 둔 그대로였다:

> 저장은 **기관(tenant) 층**에 앉는데, 표의 `value`·`source` 는 `list_thresholds` 가
> **전역 층 덮어쓰기만** 읽어 채운다 (`kernels/k5_trust/services.py:56`).

**그 줄이 정확했다.** 그래서 「바꾼 기록」으로 우회한 네 판단도 옳았다 —
그때는 제품이 실제로 안 바뀌고 있었으니까.

## 2. 무엇을 고쳤나 — 파일 하나, 함수 하나

**`backend/kernels/k5_trust/services.py`**

| 무엇 | 전 | 후 |
|---|---|---|
| `list_thresholds` 가 읽는 층 | **전역(global)뿐** | **기관(tenant) → 전역 → 정의** — `resolve_threshold` 와 **같은 한 벌**(`_lookup_chain`) |
| `value` | 전역 덮어쓰기 없으면 정의 기본값 | **내 기관 값이 있으면 그 값** |
| `source` | `override` / `default` / `unset` | **그대로다 — 안 바꿨다** |
| `source_level`(새 칸) | 없었다 | `"tenant"` · `"global"` · `null`(정의 기본값) |

★ **`source` 의 값 집합은 한 자도 안 바꿨다.** 화면(`SettingsRules.tsx:618`)이
  `override`/`default`/그밖 으로 태그를 그리고 있어서, 여기에 `"tenant"` 같은 새 낱말을
  넣었으면 **기관 값이 「정해지지 않음」(주황)으로 그려졌을 것**이다. 그래서 층은
  **새 칸(`source_level`)으로** 냈다. 네 화면 파일은 **0줄 안 고쳤다.**

★ 카메라 층은 이 표에서 **안 읽는다** — 이 표에는 카메라가 없다. 카메라 한 대의 값은
  `resolve_threshold(camera_id=…)` 가 답하는 자리다(그쪽은 원래 맞게 돌고 있었다).

## 3. **어떻게 재는지** — 네가 쓸 술어 셋

### 3-①. 가장 곧은 것 — 「지금 값」이 바뀐다

U5#S3 은 `scope_level='tenant'` 로 저장한다(화면이 `me.group_id` 를 실어 보낸다).
이제 같은 화면의 **「지금 값」 칸이 저장한 수로 바뀐다.**

```
GET  /api/dsm/settings/thresholds
     → thresholds[*] 에서 key 가 바꾼 항목인 행을 찾아
       value  :  10  →  11   (bump 한 값 그대로)
       source :  "default"  →  "override"
       source_level : null  →  "tenant"      ← **새 칸. 이것이 「내 기관이 이겼다」다**
```

⇒ `srv_change("/api/dsm/settings/thresholds", "thresholds", project="value")` 가 이제 선다.
   턴 AA 에 `"history"` 로 우회했던 것을 **되돌려도 된다.**
   ★ 다만 **「바꾼 기록」 술어를 지우지는 말아 달라** — 그 칸은 되돌림에도 안 줄고
     (대장은 줄지 않는다) 되돌림 회차에도 살아 있다. **둘 다 두는 쪽이 세다.**

### 3-②. 되돌림 회차에서 무엇이 달라지나

`revert_redo` 로 처음 값을 한 번 더 저장하면 — **「지금 값」은 처음 값으로 돌아온다.**
그러나 `source` 는 `"override"` 에 **머문다**(행이 남는다) 그리고
`source_level` 도 `"tenant"` 에 머문다. **값은 돌아오고 출처는 안 돌아온다.**
⇒ 되돌림 칸으로는 **`value`** 를 보고, `source` 로 보면 안 돌아온 것처럼 보인다.

### 3-③. 남의 기관에는 안 샌다(격리)

같은 GET 을 **다른 기관 계정**으로 부르면 그 행은 여전히 정의 기본값이다.
창 표상 네가 두 계정을 같은 순간에 쥐기 어려우면 **이 칸은 회색으로 두라** —
커널 시험이 그 자리를 잡고 있다(아래 §4).

## 4. 내가 이미 선 것 — 네가 안 재도 되는 자리

`backend/tests/test_k5_threshold_table.py` 에 **새 시험 넷**을 더했다
(`ThresholdTableShowsTheEffectiveValueTest`):

```
test_the_table_shows_my_tenant_override_not_the_global_default   기관 값이 표에 뜬다 + 남의 기관 격리
test_the_global_layer_still_wins_over_the_definition             전역 층을 안 덮었다
test_the_narrower_layer_beats_the_wider_one_in_the_table_too     둘 다 있으면 좁은 쪽
test_the_table_and_the_runtime_answer_the_same_number            ★ 표와 실행이 같은 수를 낸다
```

돌린 결과 [기계 2026-09-21 20:4x · `gx-shell` · `DB_TEST_NAME=test_gx_lane_f`]:

```
tests/test_k5_threshold_table.py                       19 passed
커널 시험 전량 (k1·k2·k3·k3_role·k4·k5×2·k6)          167 passed
임계값을 부르는 앱 시험 여덟 갈래                        202 passed
```

**한 갈래도 안 깨졌다.** 증거 자리: 이 파일과 내 체크포인트 `turn-ab/F.md` §1.

## 5. ⚠ 네가 **믿으면 안 되는 것** 둘

1. **이 쪽지는 입력이지 측정이 아니다.** 나는 커널과 시험까지만 봤다 —
   **화면을 안 눌렀다**(내게 로그인 창이 없다). 「누른 뒤」는 네 차선의 일이다.
   화면이 `value` 를 다시 안 읽으면(캐시·재조회 누락) 서버가 맞아도 표는 안 바뀐다.
2. **`source_level` 은 새 칸이다.** 네 판정기가 그 이름을 못 찾으면 **회색이 옳다** —
   0 이 아니다. 서버가 안 고쳐진 것이 아니라 **네가 옛 응답을 보고 있는 것**일 수 있다:
   `runserver` 는 파일을 고치면 스스로 다시 읽지만, **응답 캐시가 있으면 옛 본문이 200 으로 온다.**
   가르는 법은 같은 순간 두 URL 을 대 보는 것이다(그 함정은 저장소가 이미 안다).
   ★ **나는 서버를 재기동하지 않았다** — 네 세션을 끊지 않으려고 손대지 않았다.
     다시 읽히지 않으면 **조율자께 청한다**(내가 누를 단추가 아니다).

— F
