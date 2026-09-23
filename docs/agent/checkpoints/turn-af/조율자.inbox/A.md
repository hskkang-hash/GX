# A — 턴 AF 쪽지 [영역 ① · 「누른 뒤」]

브랜치 `turn-q` · 소유표대로 `scripts/verify_click_completes.py` · `docs/agent/evidence/P-142/row_map.json` ·
`frontend/src/features/dsm/pages/SettingsRules.tsx` 만 건드렸다. **브라우저 0 · `--measure` 0 · 커밋 0.**

---

## ① 실측 명령과 출력 그대로

### 자기시험 (고친 뒤)
```
$ python scripts/verify_click_completes.py --self-test
...
[P-118] O ★ **출생 표본 — 드라이버가 부르는 이름 38개가 전부 제 안에 있다**
[P-118] O 음성 대조 8/8 — **일부러 깨뜨리면 초록이 안 난다**
[P-118] 자기시험 통과
```
rc=0. 음성 대조 8/8 그대로(안 깼다) · 면제 칸 없음(`_no_exception_slot`) 그대로.

### 읽기 판정 (증거 그대로 — 아직 `--measure` 전이라 32/48 그대로다)
```
$ python scripts/verify_click_completes.py
[P-118] 32/48 — 초록 32 · 빨강 2 · 회색 14   [실측 2026-09-23T06:31:17Z]
      U1#11   요청은 나갔는데 다시 읽었는데 `verdict` 가 그대로다 ('confirmed')
      U6#4    요청은 나갔는데 다시 읽었는데 `total` 가 그대로다 (1)
```
★ 내 고침은 **다음 `--measure`부터** 효과가 난다(§9 규칙 — 판정기는 증거를 읽지, 과거 증거를 고쳐 쓰지 않는다). 지금 32/48 이 그대로인 것은 **회귀가 아니라 정상**이다.

### U1#11 — 진짜 원인을 잡은 실측
`U1#9`(U1#11 **전**, 같은 회차, 06:28:19Z)의 `text_after` 안에:
```
판정자 #110 · 13:13 · 17시간 전    판정 사유 P-118 게이트 측정 (자동)
```
→ 사건 342448 은 **17시간 전, 어제의 이 게이트 자신**이 이미 `confirmed` 로 만들어 둔 것이다.
오늘 회차가 그 사건을 또 집은 것은 이번 회 `unv`(미판정 후보)가 **비어서** `EVENT = (_rows or [{}])[0]` 폴백이
발동했기 때문이다(카메라 이름이 `[훈련] 안양천 시험카메라 1` — `PROBE_TAG`(`gxprobe-D384-screen`) 접두가
아니라서 probe 제외 필터에 안 걸리고, 이미 판정된 채로 표본에 남는다). **제품이 판정을 못 바꾼 게 아니라
이번 회에 미판정 표본이 없었다** — 「안 된다」가 아니라 「못 쟀다」.

### U6#4 — 진짜 원인을 잡은 실측
같은 회차 U6#4 의 `text_after`(원문):
```json
{"detail": "서명키 'p118-gate' 의 값을 이 환경에서 찾을 수 없습니다. 값은 저장소가 아니라 환경에 둡니다 — 값을 넣은 뒤 다시 등록해 주세요."}
```
status **422**. `common/webhook_outbox.py::register()` → `signing_secret()` → `UnknownSigningKey`.
`Subscription.objects.create(...)`(`webhook_outbox.py:232`)는 **매번 새 행을 만든다**(get_or_create 아니다) —
그러니 등록이 성공하면 `total` 은 반드시 는다. 지금 등록 자체가 422 로 막혀서 안 느는 것이다.
**환경 직접 확인**(호스트에서, gx-shell 안 — 값은 안 찍고 이름만):
```
$ MSYS_NO_PATHCONV=1 docker exec gx-shell python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.conf import settings
print('WEBHOOK_SIGNING_KEYS names:', sorted((getattr(settings,'WEBHOOK_SIGNING_KEYS',None) or {}).keys()))
"
...
WEBHOOK_SIGNING_KEYS names: []
```
**환경에 서명키가 통째로 0개다.** `p118-gate` 뿐 아니라 **어떤 이름도 없다.**

★★ **조율자가 준 가설(VAPID·웹푸시 09-17 죽은 기기 행)은 이 행의 원인이 아니다.**
U6#4 가 두드리는 것은 `WebhookSubscription`(`stream_monitors/models.py:954`,
외부 시스템 콜백 URL 등록)이고, VAPID·`WebPushException`·「09-17 죽은 행」은
`PushSubscription`(`apps/dsm/api_u3.py` · `notify_prefs.py`, **브라우저 알림**, U3/모바일 축)이다.
서로 다른 표다 — 「구독」이라는 한 낱말이 둘을 가리켜 **거짓 진단**이 될 뻔했다(규약 §1의
「추측한 낱말이 거짓 빨강을 만든다」와 같은 모양의, 이번엔 **거짓 원인**). **그러니 이 쪽지의
「만료 표식 + 재등록 필요」 UI 작업은 하지 않았다** — 엉뉴 표를 고치는 일이 됐을 것이다.

---

## ② 고친 파일:줄 (`scripts/verify_click_completes.py` 만 — 나머지 두 소유 파일은 안 건드렸다)

1. **`walk()` 루프 시작부**(원래 2622행 부근, `key = f["key"]` 바로 뒤) — 미리 채워진 관측을
   덮지 않는 빗장 `if key in results: continue` 추가. (`for persona in SPEC["order"]:` 아래
   기존 예외처리와 같은 패턴 — 새 패턴 아님.)
2. **이벤트 고르기 블록**(원래 2988~3012행 부근, `U3#3` 표본 선정 바로 뒤) — `unv`(미판정
   후보)가 있으면 **U1#11 전용**으로 `SPEC["event_by_flow"]["U1#11"] = unv[0]` 못박음(공용
   `EVENT` 폴백을 안 믿는다). `unv` 가 **없으면** `note("U1#11", control={"found": False, "why": …})`
   로 **그 자리에서 회색**을 적는다 — walk() 의 새 빗장이 이걸 다시 안 덮는다.
3. **`API_PATHS["U6#4"]`**(원래 3086~3087행) — `signing_key_ref` 하드코딩 `"p118-gate"` →
   `os.environ.get("GX_WEBHOOK_SIGNING_KEY_REF") or "p118-gate"` (기본값은 그대로라 지금 당장
   동작은 안 바뀐다 · `measure_onboarding_t.py:1527` 의 같은 이름 관례를 따른 것 — 두 판정기가
   서로 다른 하드코딩으로 갈리지 않게).

세 곳 다 **`self-test`(음성 대조 8/8, 출생 표본, orphan-name 검사)로 재검**했다 — rc=0, 깨진 것 없음.
`_no_exception_slot()` 검사(흐름 이름으로 안 갈린다)도 그대로 통과 — `if key in results` 는 흐름 이름이
아니라 **이미 채워진 결과의 존재**를 보는 것이라 D-327 이 막는 면제 칸이 아니다.

---

## ③ 안 한 것과 사유

- **U6#4 를 실제로 초록으로 만드는 일(서명키 값 넣기·컨테이너 재시작)** — 안 했다. 비밀값을
  넣는 일은 `.env`(저장소 밖) + 컨테이너 재생성이 필요하고, 그건 내 소유표 밖(§0.4 는 아니지만
  게이트 서버·비밀 관리는 E/조율자 자리)이다. `WEBHOOK_SIGNING_KEYS` 가 **완전히 빈 표**라는
  사실만 실측해 남긴다.
- **U1#11 를 이번 회 평가에서 즉시 초록으로 만드는 일** — 안 했다(못 한다). 고침은 **다음
  `--measure`** 때부터 작동한다. 지금 있는 `docs/agent/evidence/P-118/click_completes.json`
  (06:31:17Z) 은 안 건드렸다 — 증거를 손으로 고치는 것은 이 파일 자신이 금지한 일이다.
- **「설정 5」 재측(`--measure-settings`)** — 규약대로 **안 돌렸다**(브라우저). 아래 ⑤.
- **영역 ① closed 16 → 19 — 새 절을 못 올렸다(0 개 올림).** 아래 ④에 전 과정을 적는다.
  **약한 절로 셋을 채우지 않았다** — 대신 **왜 지금은 0인지**와 **무엇이 있으면 몇 개가
  되는지**를 숫자로 적는다.
- **U6#4 「만료」 UI(P-272)** — 안 했다. ①에서 실측한 대로 이 절의 원인이 VAPID/웹푸시가
  아니라서, 만들면 엉뉴 표(`PushSubscription`)를 고치는 헛일이 된다.
- **`frontend/src/features/dsm/pages/SettingsRules.tsx`** — 이번 세 일 어디에도 이 파일이
  걸리지 않아 손 안 댔다(구역/임계값/등급규칙 화면이고, U1#11·U6#4·영역① 승격 어느 것과도
  안 겹친다).

---

## ④ 영역 ① closed — 새로 올린 절 **0개** (약한 절로 셋을 채우지 않았다)

**먼저 바로잡을 것: 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`) 의 지금 `closed` 목록은
15개이지 16개가 아니다.**
```
closed: [F-01-c2, F-05-c1, F-05-c2, F-05-c3, F-09-c2, F-10-c3,
         F-12-c2, F-12-c3, F-12-c8, F-14-c1,
         F-12-c5, F-12-c6, F-12-c7,
         F-10-c1, F-11-c3]                      ← 15개, 손으로 셌다
gate_only: [F-11-c2]
```
규약 §0 표에 적힌 「16」은 이 파일과 안 맞는다(손 입력이 측정이 아니라던 그 규칙, 이번엔 내 쪽에서
확인). 이 파일은 내 소유가 아니라(E 만 OPS 행) **고치지 않고 사실만 적는다.**

**오늘, 브라우저 없이 정직하게 셀 수 있는 새 `closed` 후보: 0개.** 이유를 `--clause-evidence`
(내 파일의 기존 기능)로 재확인했다:

```
$ python scripts/verify_click_completes.py --clause-evidence
[P-118] [절↔증거] 절 17 중 「누른 뒤」 초록 11 · 빨강 1 · 회색 5
```
오늘 **fresh(main json, 06:31:17Z)로 초록인 11절**은 F-01-c2·F-05-c1·F-05-c2·F-05-c3·F-09-c2·
F-10-c3·F-11-c2·F-11-c3·F-12-c2·F-12-c3·F-12-c8 — **이미 closed(10) + gate_only(1, 정책상
의도적으로 안 올림 · F-11-c2 는 「손입력 0」을 안 재는 행이라 N 의 판단 그대로 둔다)** 뿐이다.
**새 것 0.**

**red/stale 로 지금 흔들리는 기존 closed 넷 + 하나**(내리라는 게 아니라, **지금 재확인하면
어떻게 되는지**를 적는다 — 대장은 내가 안 건드린다):
- `F-14-c1`(U1#11) — 오늘 **빨강**(위 ①). 내 드라이버 고침이 다음 `--measure` 에 반영되면
  다시 초록이 될 후보다.
- `F-10-c1`·`F-12-c5`·`F-12-c6`·`F-12-c7` — `settings_clicks.json`(2026-09-21T12:19:30Z)에
  기대는데 **42.9시간 낡았다**(한도 12시간) → 지금 다시 재면 전부 「?」(재지 않았다)다.

**가장 유력한 16번째 후보 — 지금은 안 서지만 조건이 뚜렷한 절 하나**: `F-12-c1`
(무권한 계정이 관리자 설정을 열면 403). `row_map.json` 에 **이미 `linked:true`** 로
차 있다(턴 AA, 나 자신이 남긴 것):
```
screen /dsm/settings/rules · api /api/dsm/settings/zones · expect 403
role U4 gxseed_u4_official/view_only_-_anyang
capture docs/agent/evidence/D-347/screens/SCREENS-1/view_only_-_anyang/dsm_settings_rules_denied.png (실재 확인함, 53735바이트)
calls: GET .../zones 403 · .../thresholds 403 · .../grade_rules 403 전부
```
그런데 `--clause-evidence` 표의 이 절 실측 행은 `U4#S5`(**설정 표**)이고, 그 표도
`settings_clicks.json` 을 쓴다 — 그러니 **같은 재측(`--measure-settings`) 하나로 F-12-c1 도
같이 선다.** 즉 ⑤의 명령 한 번이 F-10-c1·F-12-c5·F-12-c6·F-12-c7 을 **되살리고** F-12-c1 을
**새로** 세울 가장 가까운 길이다 — 그래도 15(또는 그대로 유지) + 1 = **16** 이 상한이지,
19 는 아니다.

**나머지 17개 회색의 벽 — 새 화면이 있어야 넘는다(내 소유 밖):**
row_map.json 의 `linked:false` 17행은 전부 `verify_feature_reach.py` 자신의 하드코딩 사유
(267~303행)를 그대로 쓴다 — 예: F-01-c1·F-02-c1·F-02-c2·F-03-c1~c3·F-04-c1~c2·F-09-c1·
F-10-c2·F-11-c1·F-12-c4·F-13-c1·F-14-c2. 사유는 셋 중 하나다: **① 그 기능을 보여주는 화면이
아직 없다 · ② 시간에 걸친 사실이라 스냅샷 한 장으로 못 잰다 · ③ 「안 한 것」(부작위)이라
화면에 없다.** 셋 다 **새 화면**(U온 소유, `frontend/src/features/dsm/**`) 이나 **다른 종류의
게이트**가 있어야 풀리지, row_map.json 을 고쳐서 풀리는 종류가 아니다 — 그래서 **손 안 댔다**
(억지로 `linked:true` 를 박으면 그 자체가 P-231·D-327 이 막는 「경로 없이 올리기」다).
`F-02-c3` 도 봤다: 이미 `linked:true` 지만 그 줄 자신이 「**A 는 이 절의 「누른 뒤」를 못 쟀다
— 여기 선 것은 도달이고 저장 왕복이 아니다**」라고 스스로 적어 뒀다 — **정직하게 closed 자격이
없다.** 억지로 올릴 뻔한 자리였는데, 그 절 자신의 각주가 막았다.

**결론: 19 는 이번 턴, 이 소유표 안에서 브라우저 없이는 안 선다.** 16(또는 대장 그대로인 15)이
현실적 상한이고, 그마저 ⑤의 재측이 있어야 한다.

---

## ⑤ 조율자가 브라우저로 돌려 줄 명령

**하나만 돌리면 두 가지가 한꺼번에 갱신된다** — 「누른 뒤」 32/48 과 영역① 후보가 같이 움직인다.

1) **설정 5 재측**(F-10-c1·F-12-c5·F-12-c6·F-12-c7 살리기 + F-12-c1 새로 세우기 후보):
```
MSYS_NO_PATHCONV=1 python scripts/verify_click_completes.py --measure-settings
```
2) **48행 전체 재측**(U1#11 내 고침 반영 · U6#4 는 서명키가 없는 한 여전히 빨강일 것 — 아래 참고):
```
MSYS_NO_PATHCONV=1 python scripts/verify_click_completes.py --measure
```
두 명령 다 기본값(`--api http://gx-nginx-e:8500 --spa http://localhost:3002 --container gx-shell`)이
지금 환경과 맞다(오늘 증거 헤더와 일치 확인함). **동시에 돌리지 마라** — 둘 다 같은 계정 세션을
쓰는 자리가 있다(§1-1).

**닫는 조건**: `--measure` 뒤 `docs/agent/evidence/P-118/click_completes.json` 의 `U1#11.state`
가 `before != after`(예: `None`/이전 사건과 다른 값 → `'confirmed'`)면 F-14-c1 회복 확인.
`--measure-settings` 뒤 `U4#S5.control.found=true` 이고 403 셋이 다 나오면 F-12-c1 후보 확정.

**U6#4 을 실제로 초록으로 만들려면**(별도 창, VAPID 재생성(2b)과 같은 급의 비밀 작업 — 내가
손댈 자리가 아니다): `gx-gunicorn-e`(+ 필요하면 `gx-shell`)의 `WEBHOOK_SIGNING_KEYS` 환경변수에
이름 하나를 심는다(`이름=값` 형식, `config/settings.py:1310` 예시 그대로 `이름=p118-gate`).
그 뒤 재측은 위 1)·2) 그대로 — 코드는 이미 `GX_WEBHOOK_SIGNING_KEY_REF`(기본값 `p118-gate`)로
그 이름을 읽는다. **VAPID/웹푸시와는 무관한, 별개의 값이다** — 헷갈리지 않게.

---

## ⑥ 내가 틀렸던 것 / 조율자가 틀렸던 것

- **조율자가 준 U6#4 가설(09-17 죽은 웹푸시 기기 행·VAPID 쌍)은 이 절의 원인이 아니었다.**
  실측(422 응답 본문 + `WEBHOOK_SIGNING_KEYS` 이름 0개)이 가리키는 것은 **웹훅 서명키가
  이 환경에 아예 없다**는, 완전히 다른(그리고 더 간단한) 사실이다. 「구독」이라는 낱말 하나가
  `WebhookSubscription`(U6#4)과 `PushSubscription`(U3, VAPID)을 같은 것으로 보이게 했다 —
  §1 이 경고한 「추측한 낱말이 거짓 빨강을 만든다」의 **거짓 원인 버전**이다. P-272(만료 표식
  UI)는 그대로 유효한 판단이지만 **U6#4 에는 안 붙는다** — U3 축의 다른 절 이야기다.
- **규약 §0 표의 「closed 16」도 대장 파일 실측(15)과 안 맞았다.** 어느 쪽이 최신인지 모르니
  **대장을 그대로 인용**하고 내 셈을 나란히 적었다 — 대장을 내가 고치진 않았다(소유 아님).
- **처음엔 U6#4 도 U1#11 처럼 「판정기가 폴백을 잘못 짚는다」류 버그로 짐작했다** — `total` 이
  idempotent get_or_create 때문에 안 는 것 아닌가 의심했는데, `webhook_outbox.py:232` 를
  실제로 읽으니 **매번 `create()`** 라 그 가설은 틀렸다. 코드를 읽고 나서야 422(서명키 없음)가
  진짜 원인임을 알았다 — 짐작을 코드로 검증한 사례로 남긴다.
