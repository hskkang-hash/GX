# U5-BACKUP-404 — `/dsm/system` 이 부르던 404 를 **눌러서** 닫았다

발행: 2026-09-19 · 턴 W · 차선 U56 · 세종 §3 ㉠

## 0. 한 줄

`GET /api/dsm/ops/backup/declaration` 은 넉 달 동안 **404** 였다. 화면은 그것을
빨강이 아니라 회색(「백엔드 신호 대기」)으로 그렸고 — 그래서 아무도 안 고쳤다.
**읽기 문 하나**를 세워 닫았다. 쓰기 면은 나지 않았다.

## 1. 무엇이 404 였나 — 그리고 **하나였다**

조율자 선등록(`write_surfaces_v11.yaml` ㉡)은 「`backup`·`declaration` 404 —
**읽기 문 둘**」로 적었다. 실측한 404 **URL 은 하나**다:

    GET /api/dsm/ops/backup/declaration     ← `backup` 과 `declaration` 은 한 경로의 두 조각

옛 기록도 전부 이 한 줄이다:
`CR-USER/U5U6/evidence_index.json`(U5-BACKUP-404) · `P-74/README.md:199` ·
`P-122/reach_after_20260910.json:291` · `UX-WALK/runs/walk_20260919T062846.json:368` ·
`P-118/click_completes.json` · `onboarding_48.md:595`.

## 2. 닫기 전 — **같은 경로를 두 출처로** [실측 2026-09-19 17:3x]

| 출처 | `GET /api/dsm/ops/backup/declaration` | 읽는 법 |
|---|---|---|
| `nginx:8500` → `gx-gunicorn-e` (재기동 뒤) | **401** | 문이 **있다**(인증을 묻는다) |
| `gx-shell` 안 `runserver:8000` (pid 38479) | **404** | 문이 **없다** — **옛 코드다** |

⚠⚠ **이 두 줄이 갈린 이유가 이 문서에서 제일 중요한 사실이다.** 그 `runserver` 는
`--noreload` 로 손으로 띄운 프로세스다 — **백엔드를 고쳐도 그 프로세스에는 안 들어간다.**
그리고 **화면 번들이 부르는 곳이 바로 8000 이다**(`_fe_dist/assets/index-*.js` 에
`http://localhost:8000` 이 박혀 있다). 재기동하지 않고 화면을 눌렀다면 **고친 뒤에도
404 를 보고 「안 됐다」로 적었을 것**이다. `docker restart gx-gunicorn-e` 만으로는
모자라다. (조율자 대장 「손으로 띄운 프로세스」와 같은 뿌리 — P-183 후반.)

## 3. 닫은 뒤 — **브라우저로 눌렀다** [실측 2026-09-19 17:41 KST]

`gxseed_u5_sysop` 으로 로그인(앞선 세션 종료 확인창을 **사람이 하는 그대로** 눌렀다)
→ `/dsm/system` 으로 이동 → 네트워크를 **두 출처로** 적었다(playwright `response` 이벤트 ·
브라우저 자신의 `performance.getEntriesByType('resource')`). 둘 다 **11건**으로 같다.

    분모 11건 · 404 **0건**

| 화면이 부른 것 | 상태 |
|---|---|
| `GET /api/dsm/law/retention` | 200 |
| **`GET /api/dsm/ops/backup/declaration`** | **200** ← 이 줄이 이 문서의 전부다 |
| `GET /api/dsm/system/backup-receipts` | 200 |
| `GET /api/dsm/system/requests` | 200 |
| `GET /api/dsm/system/storage` | 200 |

⚠ **0 을 분모 없이 적지 않는다.** 첫 판에서 `response` 이벤트가 0건 잡혔고 그때의
「404 0건」은 **아무 뜻도 없는 0** 이었다(분모가 0이다). 그래서 출처를 하나 더 붙여
11건을 세운 뒤에 다시 적었다.

## 4. 화면이 무엇을 말하는가 — 회색이 사라졌다

`dsm_system_20260919_TW.png` (전체 화면 · 같은 판에서 찍었다):

    백업 목적지        /backup
    백업 일정          매일 03:00 (beat: common.ops_backup_beat)
    백업 보관 기간     14일
    복구 시험          주 1회 일요일 06:00 (beat: common.ops_restore_drill_beat)
    누가 정했나        개발·스테이징 선언 (세종 P-67 · config/retention_seed.py)
    어디서 선언하나    OPS_BACKUP_SCHEDULE_ENABLED · OPS_BACKUP_DIR ·
                       OPS_BACKUP_RETENTION_DAYS · OPS_RESTORE_DRILL_ENABLED

「이 값을 읽는 자리가 아직 없습니다」(회색) 는 **한 칸도 안 남았다.**

★ 일정 두 줄은 **beat 표에서 읽는다**(`ops_tasks._beat_schedule_text`). 문서의
  「매일 03:00」을 손으로 옮겨 적지 않았다 — 옮겨 적으면 beat 를 옮긴 날 화면만
  옛 시각을 말한다(「분모는 손으로 적지 않는다」).

## 5. **읽기 문인가 쓰기 문인가** — 읽기다

| | |
|---|---|
| `GET  /api/dsm/ops/backup/declaration` | **401**(익명) · **403**(역할 없음) · **200**(관리자) |
| `POST /api/dsm/ops/backup/declaration` | **405** [실측 · nginx:8500] |

선언하는 자리는 여전히 **환경**(`OPS_BACKUP_*`)이다. 이 문은 그 선언을 **보여 줄 뿐**
한 칸도 바꾸지 않는다. 선등록 ㉡ 의 「쓰기 문이 나면 적중」은 **안 났다.**
시험이 그 사실을 지킨다: `test_u56_backup_declaration.py::test_post_is_not_opened_on_this_path`.

## 6. 남은 것 / 산출물

- `probe_20260919_TW.json` — 누른 판의 원본(주소 · 상태 · 본문 전문)
- `dsm_system_20260919_TW.png` — 같은 판의 전체 화면
- 코드: `backend/common/ops_tasks.py::backup_declaration()` ·
  `backend/apps/dsm/api_u56.py::backup_declaration_view` ·
  시험 `backend/tests/test_u56_backup_declaration.py` (9건)
- ⚠ 회수증은 여전히 **0장**이다(`verdict: UNKNOWN`). 그것은 **다른 사실**이다 —
  「백업을 정했다」와 「백업이 남았다」를 이 화면은 두 칸으로 갈라 둔다.
