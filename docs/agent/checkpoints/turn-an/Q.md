# 턴 AN · 차선 Q(계측·게이트) — P-393 SEC-05 자기시험 표본 고정

## ① 바꾼/만든 파일
- `scripts/verify_secret_scan.py` — 자기시험(`self_test`)의 양성 표본을 무작위 32자
  1개에서 **형식별 고정 표본 5개**(`FIXED_PLANT_SAMPLES` / `_fixed_plant_samples()`)로
  교체. 값은 전부 가짜이고 기존 코드처럼(`"".join([...])`) 조각을 런타임에 이어
  붙여 이 파일 자체가 자신을 스캔할 때 걸리지 않게 했다. 스캐너 판정 규칙
  (`.gitleaks.toml` 정규식·허용목록)은 손대지 않았다(P-203 예외 조건 준수) —
  표본 값을 기존 규칙 경계 안에 맞췄을 뿐이다. 5개 형식과 대응 RuleID(호스트
  gitleaks 8.21.2 실측):
  1. `generic-api-key`(기본 룰셋) — `outbound_api_key = "…32자…"`
  2. `gx-kma-auth-key` — `kma_auth_key = "…22자…"`
  3. `gx-datago-service-key` — URL 인코딩 base64 꼴(`%2B`…`%3D%3D`)
  4. `gx-datago-service-key-decoded` — base64 디코딩 꼴(60자+ `=`)
  5. `gx-env-example-placeholder` — `.env.example` 비-플레이스홀더 값
  각 표본에 `clean_content`(같은 형식의 플레이스홀더)를 짝지어 음성 시험도 함께 둠.
  기존 음성 ①(플레이스홀더·빈 값·공개 URL) · 음성 ②(큰 잠금 파일 4000줄)은 그대로 둠.
  이제 안 쓰는 `secrets`/`string` import 제거.
- `backend/tests/test_p393_secret_scan_selftest.py` — 새 파일. 두 클래스:
  - `FixedSampleDeterminismTest` — 스캐너 없이(파이썬 값 비교만) 표본이 형식별
    5개인지, 재호출해도 같은지, **스레드 8개 동시 호출도 전부 같은 값**을 내는지
    확인. gx-shell 안에서도 실제로 잰다(회색 아님).
  - `SecretScanSelfTestGateTest` — 실제 gitleaks 로 표본 5개가 전부 잡히는지 /
    깨끗한 표본은 안 잡히는지 / `self_test()` 자체가 통과하는지 / **`self_test()`
    를 스레드 4개로 동시에 돌려도 결과가 전부 같은지**(부하 재현) 확인. 스캐너·
    설정을 못 찾는 자리(gx-shell)에서는 스킵하고 사유를 남긴다.
- `docs/agent/checkpoints/turn-an/Q.md` — 이 파일.

## ② 시험 이름과 결과
- 호스트: `python -m pytest backend/tests/test_p393_secret_scan_selftest.py -q -p no:randomly`
  → **7 passed**(3회 반복 실행, 매번 7 passed — 자기시험 자체의 흔들림 없음 확인).
- gx-shell: `MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings
  -e DB_TEST_NAME=test_gx_lane_q -w /app gx-shell python -m pytest
  tests/test_p393_secret_scan_selftest.py -q -p no:randomly`
  → **3 passed, 4 skipped**(스캐너·`.gitleaks.toml` 이 컨테이너에 마운트되지 않아
  `SecretScanSelfTestGateTest` 전체가 스킵 — 사유를 각 시험이 stdout 에 남긴다.
  `FixedSampleDeterminismTest` 3개는 실제로 통과— 이번에 고친 결정성 자체는
  스캐너 없이도 컨테이너 안에서 실측했다).
- 호스트 `python scripts/verify_secret_scan.py --self-test` → **exit 0**
  (`[SECRETS] 자기시험 통과 — … 양성 5(고정 표본 · P-393) · 음성 7(…)`).
- 호스트 `python scripts/verify_secret_scan.py`(본 판정) → **exit 0**
  (`[SECRETS] 통과 — 저장소가 나르는 자리 0건 · 이력 0건 (래칫 적용)`).

## ③ 닫은 절 · 못 닫은 절
- 별표 절(P-356) 승격 대상 아님 — 이번 일은 게이트 자기시험 고정(P-393)이라
  「명세 절 닫기」 범주 밖. 해당 없음.

## ④ 조율자에게 넘길 줄
- 없음 — 이번 작업은 소유 파일(`scripts/verify_secret_scan.py` ·
  `backend/tests/test_p393_secret_scan_selftest.py` · 이 체크포인트)만 건드렸고
  공용 파일·EVENT_ENTRY_SURFACE·라우트 대장에 넣을 줄이 없다.
- 세종/조율자 확인 요청: GA 판정기(`verify_ga_readiness.py`)가 SEC-05 를 다시 돌릴
  때 이번 고정 표본판 `verify_secret_scan.py` 를 쓰는지(캐시된 옛 판이 아닌지)
  한 번 확인 바람.

## ⑤ 스스로 의심하는 점
- **원인 추정, 재현 못함**: 턴 AM 의 실제 실패(부하 중 두 번 못 잡음)를 이번
  작업에서 재현하지 못했다. 코드를 읽고 짚은 것은 「무작위 32자 표본이 극히
  드물게 엔트로피가 낮은 조합이 되면 기본 gitleaks 엔트로피 임계를 못 넘겨
  그 회차만 못 잡을 수 있다」는 **추정**이다. `run_scan` 의 900초 타임아웃이나
  `tempfile.mkdtemp` 경합은 코드를 봐도 원인으로 짚이지 않는다(호출마다 새
  디렉터리·새 프로세스). 다른 근본 원인(예: 부하로 인한 gitleaks 프로세스
  자체의 자원 부족·킬)이 있었을 가능성을 배제하지 못한다 — 그랬다면 이번
  고정 표본 교체가 그 원인 자체를 없애지는 않는다(다만 최소한 "표본값의
  우연"이라는 갈래는 확정적으로 제거했다).
- `SecretScanSelfTestGateTest.test_self_test_is_stable_under_concurrent_load`
  는 스레드 4개로 재현했다 — 요청한 "스레드/프로세스 4개" 중 스레드를 골랐다
  (I/O 바운드라 GIL 영향이 작다고 봤다). 프로세스 기반 재현(`multiprocessing`
  또는 실제 `docker exec` 4개 동시)은 시도하지 않았다 — 규약이 "동시 docker exec
  을 여러 개 띄우지 않는다"고 못 박아서, 컨테이너 다중 실행으로 재현하는 것은
  이번 차선 권한 밖이라고 판단했다.
- 형식 5개 중 `gx-agent-docs-hex`(docs/agent 안 32자+ hex) · `gx-hardcoded-env-default`
  (env 기본값 하드코딩) · `gx-kma-auth-key-env`(따옴표 없는 env 줄)는 고정 표본에
  넣지 않았다 — "형식별 하나씩"을 5개로 못 박은 지시를 따르려 5개만 골랐다.
  더 넓히려면 표본을 늘리면 된다(스캐너 규칙은 그대로 두고).
