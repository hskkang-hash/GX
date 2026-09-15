# P-119 / SEC-20 — **읽기 전용 역할이 사건 상태를 바꿨다** [차선 S · 2026-09-10 턴 O]

- TARGET = `http://localhost:8500` (nginx `gx-nginx-e` → gunicorn `gx-gunicorn-e`)
  ⚠ 운영 프로필이 아니다 (`profile=dev` · `DEBUG=True`). 운영 *프로세스 모양*일 뿐이다.
  전수 377자리는 **gx-shell 안 Django 테스트 클라이언트**로 쟀다(아래 ③ 참조).
- AS = `gxseed_u4_official`(역할 `view_only_-_anyang`) · 대조 3계정
- SOURCE = 오늘 내가 직접 부른 응답과 내가 돌린 탐침의 산출물.

## ① 무엇이 있었나

읽기 전용 계정 `gxseed_u4_official` — 역할 코드가 **글자 그대로** `view_only_-_anyang` —
으로 사건 화면의 「조치 시작」을 눌렀다:

```
POST /api/dsm/events/4803/response?to_state=in_progress
  → 200 · 사건 상태가 실제로 바뀌었다 · 감사 #197207 · 확인 대화상자 없음
```

## ② 전 → 후 [실측 · TARGET=8500 · 같은 계정 · **실재하지 않는 id**]

| | 전 | 후 |
|---|---|---|
| `POST /api/dsm/events/999999999/response?to_state=in_progress` | **404** `{"detail":"그런 이벤트가 없습니다."}` | **403** `{"code":"read_only_role", …}` |
| `GET /api/dsm/events?limit=1` (읽기 대조) | 200 | **200** — 안 바뀌었다 |
| `POST /api/v1/auth/logout` (나가는 길 대조) | 200 | **200** — 안 바뀌었다 |

> ★ 404 는 관문이 아니다 — 핸들러가 돌아 조회까지 갔다는 뜻이다 (P-83 눈금).
> ⚠ **실재 사건 id 로는 다시 두드리지 않았다** — 그 한 번이 곧 두 번째 오염이다.

## ③ 전수 377자리 — 분모는 **살아 있는 라우터**다

`scripts/probe_role_write_surface.py` (이 턴에 만들었다). 등록된 `view_func` 를
**도달 표시만 남기는 대체물**로 잠시 바꾸고(D-334) 로그인한 사람으로 때린다 —
**본체는 한 줄도 안 돈다.** 그러므로 사건 상태도 감사 줄도 만들지 않는다.
관문(미들웨어)은 대체물과 무관하게 그대로 돈다 — 그것이 이 탐침이 재는 것이다.
분모는 `probe_write_surface.py` 와 **같은 열거**를 쓴다(갈리면 안 된다):
살아 있는 django-ninja 레지스트리 전수 중 **쓰기 메서드 377행**(경로×메서드).

| 계정 | 역할 | 전: 막힘/377 | 후: 막힘/377 | 새로 막힌 자리 | 새로 열린 자리 |
|---|---|---|---|---|---|
| **`gxseed_u4_official`** | `view_only_-_anyang` | **0** | **367** | 367 | 0 |
| `gxseed_u1_operator` | `fire_user` | 0 | **0** | **0** | 0 |
| `gxseed_u2_manager` | `fire_admin` | 0 | **0** | **0** | 0 |
| `gxseed_u5_sysop` | `admin` | 0 | **0** | **0** | 0 |

**대조 셋은 경로별로 대조했다 — 수만 센 것이 아니다.** 377자리를 (경로, 메서드) 열쇠로
전후 대조한 결과 세 계정 모두 **새로 막힌 자리 0 · 새로 열린 자리 0**.
전후에서 상태 코드가 바뀐 자리는 **네 계정 모두 딱 하나**,
`POST /api/v1/auth/otp/reset` 422 → 401 이고 그것은 **P-113 의 의도된 변화**다
(빈 본문에는 재인증 증거가 없다). P-119 가 만든 회귀는 **0건**이다.

산출물: `before_u4.json` · `after_u4.json` · `before_controls.json` · `after_controls.json`

### 통과한 10자리 — **손으로 적은 자리 그대로**

```
POST /api/token/refresh          POST /api/v1/auth/end-session
POST /api/token/verify           POST /api/v1/auth/login
POST /api/v1/auth/change-password POST /api/v1/auth/logout
POST /api/v1/auth/delete-session  POST /api/v1/auth/otp/reset
POST /api/v1/auth/otp/verify      POST /api/v1/auth/refresh-token
```

들어오는 길 · 나가는 길 · 자기 자신에 대한 최소 조작. 이 열을 막으면 읽기 전용 계정은
**로그아웃도 못 한다** — 관문이 문을 잠그고 열쇠를 삼킨다.

## ④ 어디서 막았나 — **길목 하나**

`backend/common/role_gate.py` (`RoleGateMiddleware`). 자리는 `AccessGateMiddleware`
바로 아래 · 응답 캐시(`UniversalCacheMiddleware`)보다 **바깥**. dj-core 는 한 줄도 안 고쳤다.

### 왜 `access_gate` 가 아니라 `role_gate` 인가 — **지시와 다른 파일을 골랐다**

지시는 `access_gate` 를 지목했다. 그 파일에 넣지 않은 이유를 그대로 적는다:

`access_gate.py` 머리말이 스스로 못박아 둔 규율이 있다 —
「이 관문이 답하는 질문은 하나다: **아무것도 없이 들어왔는가**」. 역할 판정을 그 안에
넣으면 그 규율이 깨지고 인증기와 권한기가 한 파일에서 섞인다. `role_gate.py` 는
**역할 관문**이고 이미 `user.roles` 를 본다 — 질의 한 벌로 끝난다.
**자리(미들웨어 순서)는 완전히 같고, 겹도 하나도 안 늘었다.**
「SEC-11a 기제 = 우리 층에서 길목을 막는다」는 지시의 뜻은 그대로 지켰다.

되돌리기 한 줄: `settings.READONLY_ROLE_GATE_ENABLED = False`
★ 역할 0 관문(`ROLE_GATE_ENABLED`)과 **스위치가 따로다.** 하나를 끄려다 둘이 꺼지면
그날 구멍이 하나 열린다 — 시험이 그것도 못박는다.

## ⑤ 판정 — 넓게 세지 않았다

`is_read_only(user)` 는 다섯을 모두 만족해야 참이다:
① 인증됨 ② `is_superuser` 아님 ③ `is_staff` 아님 ④ 역할이 하나 이상 ⑤ 가진 역할이
**전부** `view_only*`.

- ⑤ 가 「하나라도」가 아니라 「전부」인 이유: `view_only` **와 함께** `fire_admin` 을
  가진 계정은 관리자다. 넓게 세면 그런 계정의 쓰기가 전부 막히고 **그것은 내가 만든
  회귀**다. [실측] 지금 DB 에 그런 계정은 **0개**라 두 해석의 결과는 같다 — 그래도
  좁은 쪽을 적어 둔다. 넓은 쪽은 나중에 조용히 남을 잠근다.
- ②③ 는 잠금 방지. ④ 는 역할 0(P-105)과 **겹치지 않게** 한다.

### 반경 [실측 2026-09-10 · Role 전수 15건]

`view_only` 접두에 걸리는 역할은 **하나뿐**이다 — id=9 `view_only_-_anyang`
("View Only - Anyang"). 보유 계정 **3** (`anyang_sv`(55) · `gongju_sv01`(100) ·
`gxseed_u4_official`(109)). 셋 다 역할이 그 하나뿐이고 셋 다 staff·superuser 가 아니다.
**나머지 12역할 · 110계정은 안 건드린다.**

## ⑥ 남은 오염 한 줄 — **되돌리지 않았다**

사건 **4803** 의 상태는 읽기 전용 계정이 바꾼 그대로 있고, 감사 행 **#197207** 도 그대로다.
[실측 2026-09-10 후 확인] `id=197207 · logger_name=guardianx.dsm.response ·
username=gxseed_u4_official · api_name=dsm.events.response · status_http=200`.
**되돌림은 경영진의 결정**이고, 감사 행은 그 일이 있었다는 유일한 증거다 — 지우면
사고가 사라진다.

## ⑦ 아직 안 한 것

**화면의 버튼 숨김은 이 다음 일이고 차선 F 의 몫이다.** 지금은 읽기 전용 계정이
「조치 시작」을 눌러도 **서버가 403 을 낸다**. 화면부터 고치면 「서버는 열려 있는데
버튼만 없는」 상태가 되고, 그건 관문이 아니다.

## ⑧ 시험 — `backend/tests/test_p119_readonly_role.py` (**21건 통과**)

`ReadOnlyJudgeTest` · `IsReadOnlyTest` · `ReadOnlyOverHttpTest`.
못박은 것: 쓰기 403 · **다른 역할은 안 걸린다(음성 대조 · D-277)** · 읽기는 한 자도 안
만짐 · 네 쓰기 메서드 전부 · 로그아웃은 열려 있음 · 잠금 방지 · 섞인 역할은 읽기 전용이
아님 · 역할 0 과 겹치지 않음 · 플래그 OFF 되돌림 · **그 플래그를 꺼도 역할 0 관문은 산다**.
