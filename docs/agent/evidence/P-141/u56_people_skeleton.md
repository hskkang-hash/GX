# U56 ④ — `apps/dsm/people.py` 골격 (턴 Q · 시간이 남아 착수)

`backend/apps/dsm/people.py` 신설 — dj-core 의 **실제 생성·비활성화 경로**
(`core.api.v1.user.create_user` / `deactivate_user`)를 `django.test.Client` 로
소켓 없이 타는 두 함수. §0.4 — dj-core 는 부르기만 하고 고치지 않았다.

## 부수 발견 — `seed_role_users.py` 의 전제가 이미 깨져 있다

`create_person()` 을 익명으로 짜서 처음 돌렸더니 **401**(`{"detail": "Unauthorized",
"reason": "authentication required"}`)이 났다. dj-core 의 `create_user` 뷰 선언에는
`auth=` 가 없지만, `backend/common/access_gate.py::AUTHN_REQUIRED_PATHS`
(140행)가 `/api/v1/user/create-user` 를 **이미 막고 있다** — D-348·P-83
(2026-09-06, 이 라우트에 권한 검사가 한 줄도 없어서 우리 층에서 길목을 막은 보안
수정). 그 관문은 `_has_credentials()`(321행) — **자격증명의 있음**만 보고 유효성은
안 본다 — 이므로 아무 로그인 사용자의 `Authorization` 헤더만 있으면 지나간다.

`backend/stream_monitors/management/commands/seed_role_users.py` 의 머리말(72~81행)은
"떠 있는 서버에 **익명으로** HTTP 를 보낸다"고 적혀 있다 — 그 문서는 access_gate.py
가 서기 **전**의 사실이다. 이 관문이 선 뒤로 그 명령이 실제로 익명 POST 를 계속
보내고 있다면, 그 명령의 시드도 **지금은 401 로 실패하고 있을 가능성**이 있다
(이 차선은 `seed_role_users.py` 를 소유하지 않으므로 직접 고치지 않았다 — 이름만
등록 요청으로 남긴다). `people.py::create_person()` 은 이 사실을 반영해
`actor_bearer_header` 를 필수 인자로 두었다 — 새 인증 경로를 만들지 않고 **이미
있는** 로그인 자격을 그대로 싣는다.

## 시험 (`test_u56_people_deactivate_401.py`, 2 passed)

1. `create_person` 이 실제 생성 경로를 타는가 — 행 생성·역할 부착 확인, 반환값에
   비밀번호 칸 없음.
2. `deactivate_person` 뒤 **이미 발급돼 있던** 그 계정의 토큰이 401 을 받는가 —
   dj-core `CustomJWTAuth.authenticate()`(`core/api/v1/auth.py:181`)의
   `if not user.is_active: raise ...` 가 하는 일이고, `people.py` 는 그 판정을
   다시 하지 않는다(새 인증 경로 없음).

## 등록 요청

- `seed_role_users.py` 가 여전히 익명으로 `create-user` 를 두드리는지, 실제로
  401 로 막혀 있는지 재확인 필요 — 이 명령의 소유 차선이 확인할 것.
