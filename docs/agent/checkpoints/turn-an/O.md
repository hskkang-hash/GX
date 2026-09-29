# 턴 AN · 차선 O(반쪽 검증 게이트) — P-392 「제목 ↔ 있는 것」 표 빈 칸 게이트 · 동음이의 잔여

## ① 바꾼/만든 파일
- `scripts/verify_spec_title_parts.py` — 새 파일. WO-17 §4 O(P-392) 게이트.
  대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)의 **영역 id=="7"** 에서
  DSM-/FWS-/O- 접두 절(annex 승격)을 뽑아(읽는 방식은 `verify_spec_coverage.py::
  promoted_ids()` 를 베낀 것 — import 는 안 했다, 판정기끼리 import 금지라 주석에
  출처를 적었다) 각 절의 `docs/agent/evidence/SPEC/<ID>.json` 의 `title_parts:
  [{part, where, status}]` 표를 재어 **빈 칸 수**·**status 가 닫힘이 아닌 행 수**를
  센다. 표 있고 빈칸/열린 행 1+ → RED(반쪽 승격). 표 자체가 없음(옛 승격 · 턴
  AK~AM) → RED 로 만들지 않고 「옛 승격·표 없음」GREY 로 별도 집계(대장은 안
  줄인다). 증거 파일이 없거나 JSON 이 표가 아니면 GREY(못 쟀다 —
  `verify_spec_fws_f6.py::judge_evidence` 의 `payload is None → EXIT_UNDECIDABLE`
  전례를 따름). `--self-test`(18건 · 빈 칸/표 없음/깨끗함/열린 부분/대장 구조
  표본) · `--list` · exit 0/1/2(D-400). **닫힘 상태 값 목록(`CLOSED_STATUS`)은
  실측이 아니라 관례 추정**이다 — 2026-09-29 SPEC 폴더 42건 전수 확인 결과
  `title_parts` 키를 쓰는 파일이 **0건**이라 값을 실측할 표본이 없었다. 그래서
  `O_promotions.md`/`N1_promotions.md` 의 표 머리글 낱말("있는 것")과 이 저장소
  산문이 섞어 쓰는 "완료"/"닫힘"을 근거로 `{있음, 완료, 닫힘, ok, present, done,
  closed}` 를 기본값으로 잡았다 — 주석에 이 사실을 정직하게 적어 두었다.
- `backend/tests/test_an_o_title_parts.py` — 새 파일. `TheSelfTestCanFail`
  (P-319·P-323, `test_verify_spec_fws_f6_gate_can_fail.py` 짝과 같은 절차) 3종
  망가뜨림(반쪽을 깨끗함으로 읽기 · 증거 없음을 깨끗함으로 읽기 · status 판정을
  전부 닫힘으로 만들기) + `RealRepoSnapshotTest`(지금 저장소의 실제 대장·SPEC 을
  읽어 구조 불변식과 반쪽 0건을 확인 · 대장 구조가 안 읽히면 grey 판정을 검증).
- `frontend/src/features/dsm/api.ts` · `frontend/src/features/dsm/pages/
  Integrations.tsx` · `frontend/src/features/dsm/routes.ts` — 동음이의 잔여 ②.
  주석 4곳의 방향 없는 "API 키"를 "인바운드 API 키"로(코드 식별자·라우트 문자열·
  화면 렌더 문구는 손대지 않음 — 아래 ②절 참조).
- `docs/agent/checkpoints/turn-an/O.md` — 이 파일.

## ② 시험 이름과 결과
- 호스트: `python scripts/verify_spec_title_parts.py --self-test` → **exit 0**
  (`[SPEC-TITLE] 자기시험 18건 통과`).
- 호스트: `python scripts/verify_spec_title_parts.py --list` → **exit 0**
  (`[SPEC-TITLE] [입력] 승격(영역 7 · DSM-/FWS-/O- 접두) 39건 · 표 있고
  빈칸/열린 행 1+(반쪽) 0 · 표 있고 깨끗함 0 · 옛 승격·표 없음(그레이) 39 ·
  증거 없음(그레이) 0 · 표 모양 이상(그레이) 0`).
- gx-shell: `MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings
  -e DB_TEST_NAME=test_gx_lane_o -w /app gx-shell python -m pytest
  tests/test_an_o_title_parts.py -q -p no:randomly`
  → **5 passed, 2 skipped**. 스킵 사유: 이 컨테이너의 `/repo/docs` 는
  `backend`/`scripts`/`frontend` 와 달리 **살아 있는 마운트가 아니다**
  (`/repo/docs/agent/evidence/D-346/ga_readiness.yaml` 이 컨테이너 안에 없음 —
  호스트에는 있다). `RealRepoSnapshotTest` 의 실물 판독 2건은 그래서 grey(skip)
  로 정직하게 남기고 초록으로 숨기지 않았다 — `TheSelfTestCanFail` 4건과
  `test_no_area7_not_found_is_grey_not_zero`(합성 표본이라 파일 불필요) 5건은
  gx-shell 안에서도 실제로 통과했다. **호스트 실행이 실물 확인의 정본**이다(위
  `--list` 결과).

## ③ 닫은 절 · 못 닫은 절 — 지금 저장소 상태 실측 결과
- **승격 39건**(영역 7 · DSM-/FWS-/O- 접두, 2026-09-29 실측) — 전부 턴
  AK~AM(차선 N1~N3) 유산.
- **표 있음 0건 · 빈 칸/열린 행 있는 반쪽(RED) 0건.**
- **옛 승격·표 없음(GREY) 39건** 전부: `DSM-U3-03·U3-04·U5-02·U4-06·U2-03·
  U2-04·U2-05` · `FWS-F1-01,02,03,05,06,08,10,11,12,13` ·
  `FWS-F2-01,02,03,05,07,11,12,13,14,15` · `FWS-F5-01,02,03,08,10` ·
  `FWS-F6-01,02,03,05,06,08,10`.
- 이 게이트 자체는 **절을 닫거나 못 닫지 않는다** — 다른 차선이 닫은 절의
  증거 표를 검사할 뿐이다. 이번 턴에 이 게이트가 닫은 것은 「게이트 자신」이다.
- **청구(세종 판정 몫)**: 위 39건은 P-356 넷째 조건("표")을 아직 못 채웠다.
  이 게이트는 그것을 소급 RED 로 만들지 않았지만(대장이 이미 closed 로 적어
  둔 것을 이 턴이 되돌리면 다른 차선의 작업을 무단으로 뒤집는 셈이라), **사실
  자체는 여기 남긴다**: 세종이 "N턴 안에 표를 채운다" 는 기한을 걸 결정문
  (`docs/agent/decisions.yaml`, D-511 식)을 두면, 이 게이트가 그 기한을 읽어
  스스로 GREY→RED 로 올릴 수 있다(이번 턴은 그 배선까지는 안 했다 — 결정문
  파일도 우리 소유가 아니다).

## ④ 조율자에게 넘길 줄
1. **대장에 게이트 행 추가**(대장 이동은 조율자 몫). 영역 7 은 지금 `gate:`
  필드가 없다(영역 1 만 있음 · 그건 다른 뜻의 게이트라 키를 겹치지 않게 새
  이름을 썼다). 붙일 조각 제안:
  ```yaml
  - id: "7"
    # 기존 name · weight · clauses 는 그대로 두고 아래 셋만 더한다
    title_parts_gate: scripts/verify_spec_title_parts.py
    title_parts_gate_args: "--list"
    title_parts_gate_note: >
      P-392 · WO-17 §4 O — 영역 7 의 annex 승격 절(DSM-/FWS-/O- 접두)마다 증거
      title_parts 표의 빈 칸·열린 행을 센다. 2026-09-29 실측: 승격 39건 · 표 있고
      빈칸/열린 행 1+(반쪽) 0 · 표 있고 깨끗함 0 · 옛 승격·표 없음(회색) 39. exit 0.
  ```
2. **`scripts/_gate_header.py` 의 `SELF_TEST_LINKS`** (공용 파일 — 이 차선
  소유가 아니라 직접 안 고쳤다) 에 아래 한 줄이 필요하다(P-319 「새로 태어나는
  게이트는 짝이 있어야 한다」 — 안 넣으면 `verify_gate_header.py` 감사가 이
  게이트를 "짝 없음" 기준선 빚으로 잡을 것이다):
  ```python
  "verify_spec_title_parts.py": "backend/tests/test_an_o_title_parts.py",
  #: [P-392 · 2026-09-29 · 턴 AN 차선 O] 영역 7 승격 절의 title_parts 표 빈 칸
  #: 게이트 — 망가뜨림 = 반쪽/증거없음/열린-status 를 통과시키는 판정식.
  ```
3. **동음이의(D-337) 규칙 참고**: `scripts/verify_homonyms.py` 의 `api_key`
  패턴(`\bapi[_-]?keys?\b`)이 **밑줄 바로 앞의 `api_key`(예: `issue_api_key`)를
  못 잡는다** — 밑줄은 단어 문자라 `\b` 가 그 자리에서 안 선다. 실제로 그 이름을
  가진 함수가 `backend/apps/dsm/api.py:1093`(`def issue_api_key(...)`)에 실재
  하고, `backend/apps/fws/drone.py:265` 주석이 그 이름을 방향 없이 인용한다.
  둘 다 이번 턴 §2 지시(N1·N2·N3·L 파일 · api_u4.py·u4_regulations.py) 밖이라
  안 고쳤다(`api.py` 는 목록에 없고, `drone.py` 주석은 실재 이름을 인용하는
  것이라 이름 자체를 안 바꾸면 방향을 못 붙인다 — 바꾸면 거짓 인용이 된다).
  동음이의 대장(D-337) 소유 차선이 정규식을 좁히거나, `api.py::issue_api_key`
  이름 자체에 방향(`issue_inbound_api_key`)을 붙이는 것을 검토해 주길 청구한다.

## ⑤ 스스로 의심하는 점
- **`CLOSED_STATUS` 목록은 실측이 아니라 관례 추정**이다(위 ①·SPEC 폴더
  42건 전수 확인 — `title_parts` 사용례 0건). 다음 차선이 이 키를 실제로
  채울 때 여기 없는 낱말("충족"·"complete"·"✅" 등)을 쓰면 **진짜로 닫힌
  것이 열린 행으로 오판될 위험**이 있다. 이 게이트가 그런 그릇 RED 를 내면
  가장 먼저 `CLOSED_STATUS` 를 의심할 것 — 코드 주석에도 그렇게 적어 두었다.
- **영역 7 한 곳만 본다.** 2026-09-29 실측으로는 DSM-/FWS-/O- 접두가 다른
  일곱 영역에 0건이라 안전하지만, 다음 턴 조율자가 승격을 다른 영역(예:
  가중치 재편)으로 옮기면 이 게이트가 그 절을 조용히 놓칠 수 있다 — 완화책
  으로 "영역 7 밖에서 같은 접두가 보이면" 이상행 관측 줄을 출력에 넣었으나,
  그것은 판정에 안 들어간다(경고만 낸다).
- **gx-shell 안에서 실물(대장·SPEC 폴더)을 못 읽는다** — `/repo/docs` 가 그
  컨테이너의 살아 있는 마운트가 아니다(③·②절 참조). pytest 전량에서 이
  게이트의 "지금 저장소가 실제로 반쪽 0건인가"는 **호스트 실행으로만
  확인했다**(gx-shell 에서는 grey-skip). 이것이 참인지(다른 컨테이너 재기동
  뒤에도 그런지)는 확인 못 했다 — `guardianx-recreate-window-traps` 메모의
  "재생성 창 함정" 범주일 수 있다.
- **`verify_gate_header.py::SELF_TEST_LINKS` 를 직접 안 넣었다** — 공용 파일
  이라 §2 소유표 밖으로 판단했다. 그 결과 이 새 게이트는 조율자가 그 줄을
  넣기 전까지 "짝 없는 새 게이트"로 감사에 잡힐 수 있다(④-2 참조).
- **동음이의 ② 잔여**: `verify_homonyms.py --list` 가 잡는 45개 파일(단독
  사용 182건)은 전부 backend/common·partner·third_api·config·kernels·
  stream_monitors·tests·scripts 이고 이번 턴 §2 지시 범위(N1~N4·L 파일) 밖이라
  안 건드렸다 — 그 목록은 도구 출력 그대로다(스크립트 실행 로그 참조). 이번에
  고친 것은 프런트 `dsm` 3개 파일의 주석 4곳뿐이다(그 도구는 frontend 를 안
  스캔해 이 4곳은 애초에 `--list` 에 안 잡힌다 — WO 지시가 프런트 경로를
  범위로 지목해서 직접 grep 으로 찾아 고쳤다).
