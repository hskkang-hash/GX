# OPS-26 · P-314 — **`kill -HUP 1` 은 이 서버에서 코드를 다시 읽지 않는다**

[조율자(영실) · 2026-09-24 · 턴 AH · **세종 P-314 ① 과 헤드리스 허용 목록에 대한 보고**]

## ① 세종 판정 P-314 ① 이 적은 것

> 조율자 병합 단계와 커밋 훅 뒤에 **gunicorn 우아한 재적재 1줄**
> (`docker exec gx-gunicorn-e kill -HUP 1` — 워커만 새로 뜬다 · 컨테이너 재생성 아님)
> · 세종 판정으로 헤드리스 허용 목록에 이 한 줄만 정확히 추가

그리고 `scripts/loop/headless.settings.json` 에 실제로 들어갔다(19:09):

```
허용  Bash(docker exec gx-gunicorn-e kill -HUP 1)
허용  Bash(docker exec gx-gunicorn-e kill -s HUP 1)
거부  Bash(docker kill*)
거부  Bash(docker restart*)
```

## ② 실측 — 이 서버는 `preload_app = True` 다

```
PID1 명령줄     python -m gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 ...
PID1 작업 디렉터리  /app
gunicorn 판      23.0.0          (작업 디렉터리의 gunicorn.conf.py 를 기본으로 읽는다)
/app/gunicorn.conf.py:101        preload_app = True
/app/gunicorn.conf.py            max_requests = 200 · max_requests_jitter = 50
```

`preload_app = True` 이면 앱(Django 전체)이 **마스터에** 올라가고 워커는 마스터를
**복제**(fork)한다. `HUP` 은 **워커만** 새로 띄우므로, 새 워커는 **마스터의 옛 모듈을
그대로 물려받는다.** 앱 코드는 다시 읽히지 않는다. `max_requests = 200` 으로 워커가
저절로 바뀌어도 마찬가지다 — 여전히 옛 마스터의 복제다.

## ③ 오늘 사고와 **정확히** 맞는다

오늘 `/api/dsm/cameras/pulse` 가 500 을 냈다:

```
ImportError: cannot import name 'exclude_not_counted' from 'common.billing_marks'
```

파일에는 그 이름이 있었다. **마스터가 부팅 때 올린 옛 `common.billing_marks`** 는 복제로
물려받고, 요청 때 늦게 import 된 `camera_pulse` 만 새 파일에서 읽혔다. preload 의 결과
그대로다. **이 사고는 HUP 으로 안 고쳐졌을 것이다** — 워커를 새로 띄워도 같은 옛
마스터를 복제하니까. 그리고 **고친 것처럼 보였을 것이다** — 워커 시작 시각은 방금이다.

실제로 고친 것은 `docker restart gx-gunicorn-e` 였다(마스터가 새로 떠 앱을 새로 읽는다).

## ④ 헤드리스에서 무슨 일이 생기나

지금 허용 목록대로면 헤드리스 영실은:

1. `backend/` 를 고친다
2. 허용된 `kill -HUP 1` 을 건다
3. **새 코드가 돈다고 믿는다**
4. 제품은 **옛 코드**(또는 오늘 같은 **반쪽**)로 돈다

그리고 실제로 고치는 수단(`docker restart`)은 **거부**돼 있다. **오늘 손으로 겪은 사고가
절차로 굳는다.**

## ⑤ 이 턴에 지은 것 — 거짓 초록을 막는 게이트

`scripts/verify_live_code.py` (OPS-26 · P-314 ②). 가장 늦게 고친 `backend/**/*.py` 가
**앱을 올린 프로세스**보다 뒤면 빨강. ★ **기준을 컨테이너 안의 `gunicorn.conf.py` 에서
읽는다** — preload 이면 **마스터**, preload 가 아니라고 확인되면 가장 오래된 워커,
모르면 마스터(엄한 쪽). 워커와 견주면 HUP 뒤 이 게이트가 **초록을 거짓말한다.**

지금 실물(19:03 에 다시 세운 뒤):
```
[LIVE] [입력] 가장 늦게 고친 backend 파일: .../camera_pulse.py (09-24 17:19:41)
[LIVE] [입력] gx-gunicorn-e 마스터 시작 09-24 19:03:30 · 워커 4개
[LIVE] [입력] preload_app = True → 기준: 마스터(preload_app=True — 워커는 마스터의 복제)
[LIVE] OK   신선하다 — 가장 늦게 고친 파일이 기준보다 6229초 앞
```

사고 때라면: 마스터는 15시대(「Up 2 hours」) · 파일은 17:19 → **2시간 뒤 · 빨강**이었다.

**헤드리스가 HUP 뒤 이 게이트를 돌리면** 빨강을 받고, 고칠 수단이 거부돼 있으니
`waiting_ceo` 로 넘어간다 — **적어도 옛 코드를 새 코드라고 믿지는 않는다.**

## ⑥ 세종·대표께 — 고를 길 셋 (조율자는 허용 목록을 안 고쳤다)

| 길 | 무엇 | 대가 |
|---|---|---|
| ㉠ | 허용을 `docker restart gx-gunicorn-e` **한 줄**로 바꾼다 | 10~30초 502. 재생성 아님 · 자료 0 · 되돌릴 것 없음 — P-314 가 HUP 에 붙인 성질 그대로다 |
| ㉡ | `kill -USR2 1` → 새 마스터가 앱을 새로 읽음 → 옛 마스터에 `TERM` | 무중단. 대신 **두 단계**이고 중간 상태(마스터 둘)가 있다 |
| ㉢ | `preload_app = False` 로 바꿔 HUP 이 듣게 한다 | 설정 파일에 긴 사유가 달린 값이고, 워커마다 앱을 올려 **기억 사용이 늘어난다**. 가장 넓은 변경 |

조율자 권고는 **㉠** — HUP 과 같은 성질(재생성 아님 · 자료 0)이면서 **실제로 코드를 다시
읽는** 가장 좁은 한 줄이다. 결정은 세종·대표 몫이다.

## ⑦ 남기는 한 줄

> **「우아한 재적재」가 무엇을 다시 읽는지는 설정이 정한다 — 이름이 아니라.**
> 도구를 허용하기 전에 그 도구가 **이 서버에서** 무엇을 하는지 한 번 잰다.
