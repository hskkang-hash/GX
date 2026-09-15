# 턴 N · 조율자 30분 [영실 실측 · 2026-09-08 12:3x]

## ⓞ 밤사이 환경이 통째로 내려가 있었다 — 그리고 그것이 P-116 의 출생 표본이다

첫 명령이 이렇게 답했다:
```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```
Docker Desktop 프로세스 없음 · `com.docker.service` **Stopped**. 되살린 뒤 드러난 것:

| 스스로 돌아온 것 (재시작 정책 있음) | 내려간 채였던 것 (정책 **없음**) |
|---|---|
| `gx-celery-e` · `gx-beat-e` · `minio` · `mailpit` | **`postgres` · `redis` · `gx-shell` · `gx-gunicorn-e` · `gx-nginx-e` · `gx-fe-build`** |

여섯이 `Exited (255)`. **`docker start` 로 되살렸다 — 재생성 아님**(기존 컨테이너 그대로 · 대표 ③ 불필요).
→ 이 사건 자체를 P-116(낡은 프로세스) 과 재생성 창 목록(재시작 정책)에 넣었다. **DB 를 든 컨테이너가 재시작 정책 없이 떠 있다**는 사실은 백업 논의보다 앞선다.

## ① 보험 패치 갱신 — 171→173파일
`_patches/turnM_worktree_20260908_turnM.patch` **6.8M** · `Binary files` 0줄 · `GIT binary patch` **33줄** · 미추적 **166건**(11M tgz) · `git apply --check --reverse` **조용함**.
(턴 M 에서 배운 대로 `--binary` 로 뜨고 `--reverse` 로 건다.)

## ② ★ P-111 정본 판정 — **오늘 정본은 없다**

지시서는 「정본 = 8500 · 조건 셋 중 하나라도 아니면 그 사실을 첫 줄에 적고 회색」이라 했다. 쟀다:

| 조건 | 결과 [실측 · `gx-gunicorn-e` 안에서 django 를 실제로 띄워] |
|---|---|
| ⓐ **운영 profile 로 떠 있다** | **실패** — `profile=dev` · **`DEBUG=True`** · `ALLOWED_HOSTS=['*']` · `SESSION_COOKIE_SECURE=False` · `CSRF_COOKIE_SECURE=False` · `HSTS=0` |
| ⓑ 영실이 재기동할 수 있다 | **통과** — 방금 `docker start` 로 되살렸다 |
| ⓒ 자격이 vault 에서 · 자리표 0 | **부분** — MinIO 는 진짜(7자/28자 · 서로 다름 · `gx-shell` 의 5자/5자 동일과 대조) · 그러나 **DB 비밀번호 5자** |

**8500 은 프로세스 모양만 운영이고 보안 프로필은 개발이다.**
그러므로 이 환경에는 **운영 프로필로 뜬 서버가 하나도 없다**:

| | 프로세스 모양 | 보안 프로필 | MinIO 자격 |
|---|---|---|---|
| 8000 `gx-shell runserver` | 개발 | 개발 | **자리표(5자·동일)** |
| 8500 `nginx→gunicorn` | **운영** | **개발** | 진짜 |

→ **8500 을 「더 나은 대상」으로 쓰되 「정본」으로 승격하지 않는다.** 보고에 회색으로 적는다.
지난 턴의 정정(「MinIO 자리표는 제품이 아니라 잰 대상의 문제」)은 여기서 **한 겹 더** 내려간다:
잰 대상이 틀렸던 것을 고치려 보니 **고쳐 갈 곳 자체가 없었다.**

## ③ `DEBUG=True` 인 서버에서 턴 L 의 그 공격을 다시 쐈다 — 방어가 섰다

`Authorization: Bearer zzzgarbage` (8500 · `DEBUG=True`):

| 라우트 | status | bytes | 누출(`Traceback`·`pydantic`·`File "`·내부경로) |
|---|---|---|---|
| `/api/dsm/events` | 500 | **170** | **없음** |
| `/api/nonexistent-route-xyz` | 500 | **170** | **없음** |
| `/api/v1/user/list` | 500 | **170** | **없음** |
| `/api/dsm/events` (익명) | **401** | — | — |

턴 L 의 165,721B 장고 디버그 전문이 **DEBUG 가 켜진 서버에서도** 170B 다. 그 고침은 `DEBUG` 에 기대지 않는다 [실측].
**아직 열린 것**: 망가진 토큰이 **401 이 아니라 500** 이다(차선 B 가 이번 턴 닫는다).

## ④ P-90′ 운영 탐침 「보내라」 — **없음 · 대기(세 턴째)**. 운영계로 이번 턴에도 한 패킷도 나가지 않았다.
