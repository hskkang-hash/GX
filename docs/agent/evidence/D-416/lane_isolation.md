# P-18 정정 — 차선을 가르는 것은 자원이 아니라 **이름** [실측 2026-09-21]

## 두 갈래를 같은 기계에서 쟀다

**(가) 이름을 가르면 — 동시 2차선 · 충돌 0**

    docker exec -e DB_TEST_NAME=test_gx_c gx-shell pytest tests/test_false_positive_coupling.py
    docker exec -e DB_TEST_NAME=test_gx_d gx-shell pytest tests/test_response_flow.py
    (두 명령을 **동시에** 띄웠다)

    → 13 passed  ‖  11 passed
    → DuplicateDatabase **0건** · ObjectInUse **0건**
    → psql: test_gx_c · test_gx_d **둘 다 생겼다**

**(나) 이름이 같으면 — 재현된다 (음성 대조)**

    DB_TEST_NAME=test_gx_same  ‖  DB_TEST_NAME=test_gx_same   (동시)

    → 13 passed  ‖  10 passed · **1 error**
    → psycopg2.errors.DuplicateDatabase: database "test_gx_same" already exists
      django.db.utils.ProgrammingError: database "test_gx_same" already exists
      psycopg2.errors.ObjectInUse: database "test_gx_same" is being accessed by other users

(나)가 이 정정의 **출생 표본**이다. 2026-09-10 에 같은 모양을 한 번 만났고, 그때는
「코드 결함처럼 보이지만 환경 충돌」로 읽는 데 시간이 걸렸다.

## 고친 것 — 세 줄

    backend/config/settings.py
        "TEST": {"NAME": env("DB_TEST_NAME", default=None) or None},
    backend/.env.example
        DB_TEST_NAME=            # 이름만 (D-204)

**컨테이너를 복제하지 않았다.** 안 주면 Django 기본(`test_` + DB_NAME)이라
차선을 안 쓰는 사람의 명령은 **한 글자도 바뀌지 않는다** — 이 정정의 조건이 그것이었다.

## 강제 도구

`scripts/verify_lane_isolation.py` — ① 이름이 환경에서 오는가 ② `.env.example` 에
이름만 있는가 ③ 기본값이 비어 있는가. 자기시험 3갈래(양성·음성 둘) + 출생 표본.
**상수로 박힌 시험 DB 이름은 통과시키지 않는다** — 그러면 차선이 다시 한 이름을 쓴다.

## 남은 세 이름

포트(8x00) · MinIO 버킷 접두(`<x>_`) · 시드 테넌트(`tenant_<x>`)는 **실행 명령**에서
정해지므로 코드가 강제할 자리가 없다. 도구는 그 셋을 이름으로 출력만 한다 —
「검사 못함」과 「해당 없음」을 가르기 위해서다(D-301).
