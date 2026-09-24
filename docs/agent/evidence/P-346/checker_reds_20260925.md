# P-346 — 게이트 머리글 검사기(`verify_gate_header.py`)가 낸 빨강 셋

**작성** 2026-09-25 · 대상 P-346 · 턴 AJ 차선 F · 근거 `python scripts/verify_gate_header.py` (호스트에서 직접 돌림)

---

## 0. 표부터 — 고치기 **전** 실측 (2026-09-25, 고치기 전)

```
[P-107] [입력] 게이트 84개 · 실제로 연 것 84개 · 파이프 자리 8건 · 다른 차선 2개
[P-107] 수 5
  O  HEADER_DECLARED  게이트 84개 중 84개가 머리글을 부른다 · 다른 차선 2개는 자기 칸
  X  HEADER_LIVE      84개를 실제로 열어 세 줄을 받았다 · 어긋남 1: ['verify_release_candidate.py(세 줄 중 0줄)']
  X  PIPE_EXIT        `| tail …`
                       `$?` 자리 8건 (복사해 쓰는 자리 4 · 회고문 인용 4) ·
                       ['scripts/verify_feature_reach.py:56', 'docs/agent/decisions.yaml:9864',
                        'docs/agent/checkpoints/turn-ab/Q.md:310',
                        'docs/agent/checkpoints/turn-af/조율자.inbox/K.md:99']
  X  MEASURED_LINE    게이트 84개 중 82개가 「무엇을 · 분모 N」을 말한다 · 빨강 2 ·
                       ['verify_perf_budget.py', 'verify_release_candidate.py'] ·
                       [기한] 결정문 D-511 의 기한 2026-09-23 가 왔다 — 이 칸은 이제 red 다
  O  SELF_TEST_CAN_FAIL 새 게이트 2개 중 짝 실재 2개 · 기준선 빚 82
[P-107] 실패 3/5
```

| 항목 | 파일 | 왜 빨강인가 | 정직한 고침 |
|---|---|---|---|
| **HEADER_LIVE** | `scripts/verify_release_candidate.py` | `gate_header(...)` 호출이 `main()` **안, `--self-test` 조기 반환(566행) 뒤**에 있었다. `verify_gate_header.py` 는 게이트를 `--self-test` 로 열어 첫 세 줄만 읽는데, 이 파일은 그 경로에서 **머리글에 닿기 전에 return** 해 버려 세 줄 중 0줄이 찍혔다. | 머리글 호출을 다른 모든 게이트의 관례(`verify_perf_budget.py`·`verify_password_reset.py`)대로 **`if __name__ == "__main__":` 최상단, `main()` 을 부르기 전**으로 옮겼다. 판정 로직·분모(13)는 그대로 두고, 실행 시점만 「`--self-test` 도 반드시 지나가는 자리」로 옮겼다 — 판정을 봐주지 않았다. |
| **PIPE_EXIT** | ① `scripts/verify_feature_reach.py:56` (docstring 안 인용) · ② `docs/agent/decisions.yaml:9864` (D-512 결정문 인용) · ③ `docs/agent/checkpoints/turn-ab/Q.md:310` (펜스 안 인용) · ④ `docs/agent/checkpoints/turn-af/조율자.inbox/K.md:99` (실측 로그 + 주석 한 줄) | 네 곳 다 **실행되는 코드가 아니라 "이 패턴을 쓰면 안 된다"는 인용**인데, `pipe_scan` 의 인용 면제는 `#` 로 시작하거나(모든 파일) md 파일에서 **펜스(```) 밖**에 있어야만 걸린다. 넷 다 그 모양이 아니어서(코드처럼 안 가려진 docstring · 펜스 안 · 파이프+`$?` 가 한 줄에 같이 있는 주석) "코드"로 잡혔다. | 검사기의 인용 면제 규칙(이미 있는 것)에 **맞춰** 넷을 고쳤다 — 판정식은 한 글자도 안 건드렸다: ① `verify_feature_reach.py` 인용 줄 앞에 `# ` 을 붙였다(gate_run.sh:8 이 이미 쓰는 관례). ② `decisions.yaml` 은 같은 문장을 줄바꿈만 바꿔 `\| grep` 토큰과 `$?` 토큰이 **같은 물리 줄에 안 붙게** 했다(내용은 그대로, 줄바꿈 위치만). ③ `turn-ab/Q.md` 는 펜스(```)를 빼고 인용부호(`>`)로 바꿔 "펜스 밖 산문"으로 만들었다(turn-ab/A.md:85 가 이미 이 모양으로 통과한다). ④ `turn-af/…/K.md` 는 실측 로그(`REAL_EXIT=2`, 원래 fence 안)와 그 옆에 사람이 덧붙인 주석(`| tail 함정 피함`)을 **분리** — 로그는 펜스 안에 그대로, 주석은 펜스 밖 산문으로 뺐다(실측값은 안 건드렸다). |
| **MEASURED_LINE** | `scripts/verify_perf_budget.py` (그리고 고치기 전엔 `verify_release_candidate.py` 도) | `verify_release_candidate.py` 는 HEADER_LIVE 와 같은 원인(머리글이 `--self-test` 경로에 안 닿음)으로 MEASURED 줄도 안 찍혔다 — HEADER_LIVE 를 고치며 같이 없어졌다. `verify_perf_budget.py` 는 남는다 — 이 파일은 **정직하게** `deferred:RC-1 2026-09-25 · 무엇을: 응답시간 예산의 합격선` 이라고 적어 뒀다(합격선은 gunicorn+nginx 로 OPS-13 뒤 다시 잰다는 파일 머리말 그대로). `deferred:` 는 면제가 아니라 여전히 회색으로 세이고, 2026-09-23 에 D-511 기한이 왔으므로 회색이 **빨강**으로 올라간 것 — 결정문이 집행한 것이지 이 게이트가 새로 망가진 게 아니다. | **고치지 않았다 — 빨강인 채로 둔다.** D-511 의 `deadline:` 을 옮기려면 "무엇이 끝나면 기한이 서는가"를 한 줄로 댈 수 있어야 하는데, `verify_perf_budget.py` 의 합격선 재측정은 **OPS-13 뒤 gunicorn+nginx 에서** 하기로 이미 못 박혀 있고(파일 자신의 말) 그 재측정이 **오늘 끝났다는 실측**을 이 차선은 갖고 있지 않다(OPS-13/전단 배치는 다른 차선의 자리 — `docs/agent/decisions.yaml` 의 OPS-13 계열 항목들은 앞단 컨테이너 기동을 말할 뿐, `verify_perf_budget` 의 합격선 재배선이 끝났다는 실측은 없다). 실측 없이 기한만 미루면 그것이 바로 P-217 이 막으려던 「문서에만 적은 기한」이다. 그래서 **D-511 은 그대로 두고, MEASURED_LINE 빨강 1건(`verify_perf_budget.py`)을 정직하게 보고한다.** |

## 1. 고친 뒤 재실측 (2026-09-25)

```
[P-107] [입력] 게이트 84개 · 실제로 연 것 84개 · 파이프 자리 7건 · 다른 차선 2개
[P-107] 수 5
  O  HEADER_DECLARED  게이트 84개 중 84개가 머리글을 부른다 · 다른 차선 2개는 자기 칸
  O  HEADER_LIVE      84개를 실제로 열어 세 줄을 받았다
  O  PIPE_EXIT        `| tail …`
                       `$?` 자리 7건 (복사해 쓰는 자리 0 · 회고문 인용 7)
  X  MEASURED_LINE    게이트 84개 중 83개가 「무엇을 · 분모 N」을 말한다 · 빨강 1
                       (분모를 안 말하는 게이트는 그 exit 0 이 「이 호출이 통과」일 뿐이다 · P-204) ·
                       ['verify_perf_budget.py'] · [기한] 결정문 D-511 의 기한 2026-09-23 가 왔다 —
                       이 칸은 이제 red 다 (문서가 아니라 이 줄이 그것을 집행한다)
  O  SELF_TEST_CAN_FAIL 새 게이트 2개 중 짝 실재 2개 · 기준선 빚 82
[P-107] 실패 1/5
```

**5개 중 3개(HEADER_DECLARED · HEADER_LIVE · PIPE_EXIT)가 초록, SELF_TEST_CAN_FAIL 은 원래 초록이었다.**
**MEASURED_LINE 은 빨강 1건(`verify_perf_budget.py`)으로 남아 있다 — 초록을 강제로 만들지 않았다.**

★ 인용 건수가 6 → 7 로 하나 늘었다 — **이 보고서 자신**이 위 §0 블록 안에 체커의
「`| tail … $?`」 글자를 그대로 옮겨 적었더니 그 줄이 **자기 자신을 잡았다**(펜스 안 +
파이프+`$?` 한 줄). 코드가 아니라 인용이라 판정은 안 변했지만(복사해 쓰는 자리는
여전히 0), 그 줄도 `tail …` / `$?` 로 물리 줄을 갈라 검사기 그물에 안 걸리게 했다 —
이 문서를 쓰는 행위 자체가 P-346 이 다루는 바로 그 함정을 한 번 더 보여준 자리다.

바뀐 파일:
- `scripts/verify_release_candidate.py` — `gate_header(...)` 호출을 `main()` 안에서 `if __name__ == "__main__":` 최상단으로 옮김(분모 13은 그대로, 실행 시점만 이동). `main()` 안에는 옛 자리에 이유를 적은 주석만 남겼다.
- `scripts/verify_feature_reach.py` — docstring 인용 줄 앞에 `# ` 추가.
- `docs/agent/decisions.yaml` — D-512 결정문의 한 문장을 줄바꿈만 바꿔 재서술(내용 동일, YAML 파싱 확인됨).
- `docs/agent/checkpoints/turn-ab/Q.md` — 인용 펜스를 산문 인용부호로 교체.
- `docs/agent/checkpoints/turn-af/조율자.inbox/K.md` — 실측 로그와 주석을 분리.

**손대지 않은 것**: `scripts/_gate_header.py`·`scripts/verify_gate_header.py` 의 판정식(`judge_*`, `pipe_scan`, `escalation`)은 한 글자도 안 바꿨다. `docs/agent/decisions.yaml::D-511` 의 `deadline:` 도 안 바꿨다.

---

## 2. 기준선 빚 `BASELINE_GATES_SELF_TEST_DEBT` (82) — 갚는 순서

`scripts/_gate_header.py` 의 `BASELINE_GATES_SELF_TEST_DEBT` 는 82건(다른 차선 파일 2개를 뺀 수 —
frozenset 자체는 84개 이름을 담고 있고, 그중 `verify_read_auth.py`·`verify_front_line_502.py` 는
`OTHER_LANE` 이라 이 차선의 셈에서 빠진다). **이번 턴엔 실제 자기시험 짝을 새로 짓지 않았으므로
숫자를 건드리지 않았다** — 아래는 "다음에 갚을 때 어느 순서로 갚는가"의 제안이다(≥10건).

| 순서 | 게이트 | 왜 이 순서인가 |
|---|---|---|
| 1 | `verify_ui_copy.py` | **P-319/P-323 자체를 낳은 사건.** 턴 AH 에 이 게이트의 자기시험이 `ok=False` 일곱 번을 찍고도 "통과"로 끝났던 그 파일이다(위 규칙 문단 참고). 내부 버그는 이미 고쳤지만 `TheSelfTestCanFail` 정식 짝은 아직도 없다 — 이 요구를 만든 사건의 주인공이 아직 빚으로 남아 있는 것이 가장 눈에 띈다. |
| 2 | `verify_tenant_scope.py` | P-107 자체를 낳은 **출생 표본 ①**(8월 라우트 사진을 읽던 게이트). 테넌트 격리 게이트가 자기시험 없이 회귀하면 다음에 또 "사진을 초록으로 읽는" 사고가 재발한다. |
| 3 | `verify_write_auth.py` | 출생 표본 ②(손으로 적은 분모 30). 쓰기 권한 표면 — 판정식이 조용히 무뎌지면 실제 쓰기 경로가 빠져도 아무도 모른다. |
| 4 | `verify_screens.py` | 출생 표본 ③(역할 0 계정으로 걸음). 화면 가시성 게이트 — 다음 회귀가 「걷기는 끝났는데 아무 데도 안 갔다」모양일 확률이 가장 높은 자리다. |
| 5 | `verify_minio.py` | 출생 표본 ④(호스트 root 자격으로 잰 초록). 저장소 자격 경계 — 넷 중 마지막, 나머지 셋과 같이 묶어 갚으면 P-107 머리말의 "출생 표본 넷"이 전부 자기시험까지 갖춘다. |
| 6 | `verify_credential_store.py` | 자격 저장 경계. 판정식이 조용히 깨지면 실물 유출 경로가 회색도 빨강도 아닌 채로 지나간다 — 위 다섯 다음으로 보안 반경이 넓다. |
| 7 | `verify_secret_scan.py` | 비밀 스캐너 자체 — 이 게이트의 판정식이 무뎌지면 다른 모든 게이트의 "값 안 새김" 전제가 흔들린다. |
| 8 | `verify_no_secret_echo.py` | 위와 같은 계열(응답 본문에 비밀이 안 새는가) — 스캐너와 짝을 이뤄 같이 갚는 편이 싸다(회귀 표본을 공유할 수 있다). |
| 9 | `verify_settings_fail_closed.py` | 실패 시 열리는지 닫히는지 — 이름 그대로 "fail closed" 전제가 스스로는 안 깨지는지 자기시험 없이는 아무도 모른다. |
| 10 | `verify_authn_paths.py` | 인증 경로 목록 — 로그인 문이 새로 열려도 이 게이트가 못 잡으면 회귀가 조용하다. |
| 11 | `verify_admin_doors.py` | 관리자 문 — 위와 같은 반경, 다음으로 좁다(관리자만 닿는 자리). |
| 12 | `verify_wall_keys.py` | 키 경계벽 — 이름이 이미 "wall"이다. |
| 13 | `verify_release_candidate.py` | 이번에 머리글을 고친 그 파일 — RC-1 태그를 세우는 마지막 문(P-269). 판정식(`decide_tag`)이 자기시험 안에서 이미 강한 음성 대조를 갖고 있어(출생 표본 1개 포함) `TheSelfTestCanFail` 짝을 새로 짓는 비용이 상대적으로 낮다. |
| 14 | `verify_ga_readiness.py` | 여덟 영역을 다 모으는 "여덟째 눈" — 위 게이트들이 다 갚인 뒤에 갚아야 그 아래 자리들의 회귀가 여기서도 다시 안 새는지 함께 본다. |
| 15 | `verify_migrations.py` | DB 마이그레이션 안전 — 반경은 넓지만 판정식이 비교적 정적(스키마 diff)이라 자기시험 짓기가 쉬운 편, 뒤로 미뤄도 위험이 급하지 않다. |

나머지 67건(예: `verify_camera_*`·`verify_clip_extraction.py`·`verify_zone_polygon.py` 등 카메라/영상
계열, `verify_bundle_*`·`verify_route_*` 등 프런트 배선 계열, `verify_ui_secrets.py`·`verify_sidebar.py`
등 화면 계열)은 이번 표에 순서를 매기지 않았다 — 위 15건보다 반경이 좁거나(카메라 한 대·화면 한 칸)
이미 다른 게이트와 판정 로직을 공유해 회귀 가능성이 낮다고 판단했다. 다음 차선이 이 표를 이어
쓸 때는 **번호를 매기지 않은 목록에서 하나를 골라 왜 그 자리가 다음인지 한 줄을 더하는** 방식을
권한다 — 순서 자체를 지어내지 않는다.
