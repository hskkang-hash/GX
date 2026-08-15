<!-- 승인 시 사람이 이 파일 첫 줄에 다음 한 줄을 넣는다. 에이전트는 절대 쓰지 않는다.
APPROVED: 2026-__-__ 강희석
-->
# WP-0 착수검토서 — 미결 정리 (verify-pending 해소 + 정본 동기화)

**작성** 에이전트 · 2026-08-14 · **정본** tickets v3.1 / WP 1/9
**목표(goal)** 떠 있는 verify-pending 을 전부 종결하고(사내망 1회 작업 포함) 정본을 v3.1 로 맞춘다
**티켓** W0-2 · W0-3 · W2-1 · W0-4 · W0-10 (5건 / 현재 verify-pending 4 + done 1)

> **이 WP 는 새 기능이 없다. 이미 쓴 코드를 실제로 실행해 보는 작업이다.**
> 그래서 이 검토서의 본체는 코드 계획이 아니라 **§10 사내망 1회 방문 실행계획서**다.

---

## 1. 이 목표가 참이 되려면 무엇이 있어야 하는가

goal 은 두 문장으로 쪼개진다 — **(A) verify-pending 4건이 종결된다 / (B) 정본이 v3.1 과 일치한다.**

| # | 있어야 하는 것 | 어느 티켓 | 증명 방법 | 사내망 |
|---|---|---|---|---|
| 1 | `npm install` 이 rj-core·@gaion/gcs-fe 를 받아 완료된다 | (전제) | `npm ls rj-core` 성공 | **필요** |
| 2 | 플래그 OFF 프로덕션 빌드 산출물에 데모 식별자 0건 | W0-4 | `grep -rlE 'mockupDemoUi\|setup-demo-(file\|url)' dist/assets` → 0 | **필요** |
| 3 | Django 앱이 기동되고 마이그레이션이 적용된다 | W2-1 | `migrate` 성공 + `makemigrations --check` exit 0 | **필요** |
| 4 | 격리 테스트가 실제로 돌고, 통과/실패가 분류되어 기록된다 | W0-3 | `manage.py test tests.test_tenant_isolation -v 2` 출력 | **필요** |
| 5 | 우회 목록에 업무 모델 0건 + 증가 금지 테스트 통과 | W0-2 | `BypassListTest` green | **필요** |
| 6 | 수집 모델 수·EXEMPT 사유가 `evidence/W0-3/coverage.md` 에 있다 | W0-3 | 파일 존재 + 내용 | 불필요 |
| 7 | 미수정 결함 3건이 `@expectedFailure` 로 **명시 등록**되어 있다 | W0-3 | 소스 grep + 테스트 출력의 expected failures 수 | 불필요 |
| 8 | `settings.py` 기본값에 사설 IP·내부 도메인 0건 | W0-10 | `grep -REn '192\.168\.' backend/config/settings.py` → 0 | 불필요 |
| 9 | 티켓 5건의 `status`·`evidence` 가 v3.1 정본에 기록되어 있다 | 전체 | `tickets.yaml` diff | 불필요 |

**즉 9개 중 4개는 지금 여기서 할 수 있고, 5개는 사내망 1회 방문에 묶인다.**
승인이 나면 **불필요 4건을 먼저 끝내 놓고**, 사내망 방문일에 §10 을 일괄 실행한다.

---

## 2. 대상 파일 실측 (전부 열어보고 적었다)

| 티켓 | 파일 | 현재 상태 (실측) | 왜 이 파일인가 |
|---|---|---|---|
| W0-2 | `backend/common/base_model.py` | `performance_bypass_models` 에서 업무 7종 제거 완료(커밋 `c1b9825`). 남은 것은 프레임워크 7종 | 우회 목록의 실물 |
| W0-2 | `backend/common/tenant_filters.py` | 신규. `filter_users_by_group` / `filter_by_group_field` / `get_scoped_or_404` 3함수 | 목록에서 못 뺀 모델의 대체 통제 |
| W0-3 | `backend/tests/test_tenant_isolation.py` | 350줄. 클래스 3개(Registry / ORM / API), `MODELS` 10건, `KNOWN_UNISOLATED` 4건. **`@expectedFailure` 0건** | 이 WP 의 판정 도구 |
| W2-1 | `backend/stream_monitors/models.py:125` | `class DetectionEvent(BaseModelWithGroup)` 존재. 계약 19/19 일치, 인덱스 4종 선언 | 모델 실물 |
| W2-1 | `backend/stream_monitors/migrations/` | 최신 `0015_…`. **DetectionEvent 마이그레이션 파일 없음** | 이번 방문의 유일한 스키마 변경 지점 |
| W0-4 | `frontend/src/App.tsx:157-202` | `__DEMO_ENABLED__` 삼항 안에 dynamic import 5개. 정적 import 0 | 라우트 게이트 |
| W0-4 | `frontend/vite.config.ts:22-31` | `define.__DEMO_ENABLED__ = JSON.stringify(process.env.VITE_ENABLE_DEMO === 'true')` | 리터럴 치환 지점 |
| W0-4 | `frontend/package.json:34,97` | `@gaion/gcs-fe`·`rj-core` → `git+ssh://git@192.168.0.22` | 빌드가 사내망에 묶이는 이유 |
| W0-10 | `backend/config/settings.py` | **사설 IP·내부 도메인 리터럴 13곳** (L40-47 CORS, L197 DB_HOST, L471 MINIO, L646·653·657·659 스트림/AI) | v3.1 DoD 가 새로 지목한 파일 |
| 전체 | `docs/agent/evidence/{W0-2,W0-3,W2-1,W0-4}/README.md` | 4건 모두 존재 | 재부착할 증거 원본 |

환경 실측: **Docker 데몬 미기동**(`npipe:….dockerDesktopLinuxEngine` 없음, Compose CLI v5.1.0 은 설치됨) ·
**사내망 미도달**(`192.168.0.22:22` CLOSED) · `frontend/node_modules` 없음 · `frontend/package-lock.json` 없음 ·
compose 서비스는 `frontend / backend / celery / redis` 4개.

---

## 3. 전제 검증 — 티켓 spec 과 실측의 차이

> D-210: 지시서의 식별자는 근사치다. 다르면 실측이 우선이고, 차이를 여기 적는다.

| # | 티켓 | spec/정본이 말한 것 | 실측 | 어떻게 처리할 것인가 |
|---|---|---|---|---|
| 1 | **W0-4** | 정본 `dod` 가 아직 **"해당 URL 직접 접근 시 404"** | D-218 이 그 문구를 폐기하고 "플래그 OFF 청크에 데모 식별자 0건 + 라우터 테이블 부재(홈 폴백 허용)" 로 교체 결정 | **AUTHOR-ERROR (경미).** v3.1 tickets.yaml 에 `dod` 교체가 반영되지 않았다. `dod` 는 내 수정 권한 밖(금지 #11)이므로 **D-218 문구를 실효 DoD 로 삼아** 검증하고, 정본 반영은 작성자에게 요청한다 (§8) |
| 2 | **W0-3** | spec ③ 이 지목한 실패 예상 테스트 이름: `test_service_layer_does_not_pick_arbitrary_group`, `test_all_group_models_are_covered` | 그 이름의 테스트는 없다. 실재: `test_registry_covers_all_isolatable_models` · `test_unisolated_set_has_not_grown` · `test_null_created_by_is_not_globally_visible` | 실측 이름으로 `@expectedFailure` 를 건다. 대응은 spec 의도대로 유지 (W0-14 / W0-12 / W0-13) |
| 3 | **W0-3** | spec ① "대상 모델을 하드코딩하지 않는다 — `apps.get_models()` 자동 수집" | 구현은 `MODELS` 하드코딩 레지스트리 + `test_registry_covers_all_isolatable_models` 가 자동 스캔해 **누락을 실패로 만드는** 구조 | **의도는 충족(누락 구조적 불가), 형태는 다름.** 실행 결과를 보고 판단: 자동 스캔이 실제로 미등록 모델을 잡으면 현 구조 유지, 못 잡으면 수집 방식으로 전환. 사내망 실행 전에는 결론 낼 수 없다 |
| 4 | **W0-3** | dod ③ `evidence/W0-3/coverage.md` | **없다** (README.md 만 있음) | 사내망 테스트 출력으로 채워야 완성이므로, 골격을 먼저 만들고 실행 후 수치를 기입 |
| 5 | **W0-2** | dod ③ "W0-14 가 done 또는 verify-pending" | W0-14 는 **WP-1 소속이고 현재 `ready`** | **WP 경계를 넘는 DoD 다.** 규칙상 WP 순서는 고정(금지 #18)이므로 내가 W0-14 를 당겨올 수 없다 → §8 승인 요청 1번 |
| 6 | **W0-10** | v3.1 dod "…**settings.py 기본값**에 사설 IP·내부 도메인 0개" · 정본 status `done` | settings.py 에 **13곳 잔존**. 내 증거는 `.env.example` 2개뿐 | **done 이 아니다.** 새 DoD 기준으로 미충족 → WP-0 에서 실제 처리. 상태 되돌림은 status 권한 안이므로 `ready` 로 정정하고 사유를 blocker 에 기록 |
| 7 | **W2-1** | dod "마이그레이션 적용 성공 + 격리 테스트에 DetectionEvent 포함 통과" | 모델·테스트 등록은 되어 있으나 **마이그레이션 파일 자체가 없다** | 사내망에서 `makemigrations` 로 생성 → 파일을 커밋(되돌리기 가능) → `migrate` 적용(§5 롤백 절차 필수) |
| 8 | 전체 | v3.1 정본에 티켓 `evidence` 필드 | v3.0 에 내가 기록한 evidence·blocker 가 **교체로 전부 유실** (evidence 필드 0건) | 증거 파일은 디스크에 그대로 있다. 승인 후 `status`/`evidence`/`blocker` 재부착 (권한 안) |

**전제가 통째로 틀린 티켓이 있는가?** ☐ 없음 ☑ **있음 — W0-10 하나.**
`done` 으로 등재돼 있으나 v3.1 이 DoD 를 넓히면서(settings.py 기본값 포함) 미충족 상태가 됐다.
남은 4건은 부분 차이이며 실측대로 진행하면 된다.

---

## 4. 영향 범위

| 건드리는 것 | 의존하는 쪽 | 깨질 수 있는 것 | 확인 방법 |
|---|---|---|---|
| `stream_monitors` 스키마 (DetectionEvent 테이블 신설) | 없음 — **신규 테이블**이라 기존 참조 0 | 마이그레이션 충돌(다른 미적용 마이그레이션이 있을 때) | `makemigrations --check --dry-run` 을 **먼저** 돌려 미적용분 유무 확인 |
| `settings.py` 기본값 → 환경변수 필수화 | 백엔드 전 기동 경로 (DB·MinIO·스트림·AI·CORS) | **환경변수 미설정 시 기동 실패** — 가장 큰 위험 | 치환 전 현재 기본값을 `.env.example` 에 플레이스홀더로 대응 기재, `docker compose up` 기동 확인 |
| 테스트 파일에 `@expectedFailure` 추가 | CI(W0-6 이후) | 없음. 실패가 '예상된 실패'로 분류될 뿐 | 테스트 출력의 `expected failures=N` 수 |
| `tickets.yaml` status/evidence | 다음 WP 선택 로직 | WP-1 진입 판정 | `sha256sum -c` 는 **교체 직후 1회만** 유효 — 이후 내 status 수정으로 해시는 달라진다 (정상) |
| `package-lock.json` 생성(W0-8, WP-2 소속) | 빌드 재현성 | 없음 (신규 파일) | 방문 중 부수 산출물로만 확보, **커밋은 WP-2 에서** |

---

## 5. 되돌리기 계획

| 무엇이 잘못될 수 있나 | 어떻게 되돌리나 | 난이도 |
|---|---|---|
| DetectionEvent 마이그레이션 적용 후 문제 발견 | `python manage.py migrate stream_monitors 0015` → 파일 삭제 후 재작성. **신규 테이블 생성뿐이라 기존 데이터 손실 0** | 스키마 (되돌리기 가능) |
| `settings.py` 기본값 치환으로 기동 실패 | `git revert` 1커밋. 기본값을 되살리되 값은 `.env` 로 이동 | 코드 |
| `@expectedFailure` 로 실제 결함이 가려짐 | 표시 제거 1줄. W0-13/W0-12/W0-14 완료 시 **반드시 해제**(금지 #6 — 삭제 아님) | 코드 |
| 격리 테스트가 무더기로 실패해 원인 분리 불가 | 커밋 2단계 분리(조사·증거 → 변경)로 이미 분리돼 있다. `4afca2b`(baseline) 대조 | 없음 |
| `npm install` 이 lock 없이 다른 버전을 물어옴 | 방문 중 `npm install --package-lock-only` 로 lock 확보 → 재현성 고정 | 설정 |

**되돌릴 수 없는 변경이 포함되는가?** ☑ **있음 — 마이그레이션 1건(신규 테이블 생성).**
dry-run 계획: `makemigrations stream_monitors --dry-run -v 2` 출력을 **먼저 증거로 저장**하고,
생성 SQL 을 `sqlmigrate` 로 뽑아 `evidence/W2-1/migration.sql` 로 남긴 뒤 적용한다.
데이터 마이그레이션·컬럼 삭제는 **없다** (D-209 해당 없음).

---

## 6. 리스크 3개

| # | 리스크 | 발생하면 | 완화책 |
|---|---|---|---|
| 1 | **사내망 방문 1회로 안 끝난다** — `npm install` 이 SSH 키·브랜치 권한 문제로 실패하면 W0-4 검증이 통째로 밀린다 | W0-4 만 verify-pending 유지, 나머지 4건은 종결 가능 | §10 을 **의존성 → 백엔드 → 검증 → 빌드** 순으로 배치해 앞단 실패가 뒷단을 막지 않게 했다. 각 단계에 실패 분기를 명시 |
| 2 | **격리 테스트가 대량 실패**해 W0-3 판정이 애매해진다 (fixture·API 경로 불일치 가능성) | WP-0 이 길어지고 WP-1 전제가 흔들린다 | **실패 자체는 정상**임을 미리 못 박는다(§9). 3건(W0-13/W0-12/W0-14 대상)은 `@expectedFailure`. 그 외 실패는 원인만 분류해 WP-1 입력으로 넘기고 WP-0 은 닫는다 |
| 3 | **settings.py 치환이 기동을 깨뜨린다** — 13곳 중 하나라도 env 누락 시 부팅 실패 | 방문 당일 백엔드가 안 떠서 2·4·5 항목 전부 실패 | **순서를 바꾼다**: settings.py 치환은 방문 *이후* 오프라인 작업으로 미룬다. 방문 당일은 현재 코드 그대로 띄운다 |

---

## 7. KPI 측정 계획 (EXIT 에서 숫자로 채운다)

| 축 | 무엇으로 재나 | 측정 방법 | 착수 시점 값(baseline) |
|---|---|---|---|
| 편리성 | 이 WP 는 사용자 조작 경로를 바꾸지 않는다 | — | **측정 불가 — 사용자 화면 변경 0건** (그 사실을 EXIT 에 명시) |
| 완결성 | verify-pending 종결률 · DoD 항목 충족률 | 티켓 5건 × DoD 소항목 12개 중 충족 수 | 현재 **0/12 실행 검증** (전부 미실행) |
| 안정성 | 격리 테스트 통과율 / expected-failure 수 / 마이그레이션 성공 | `manage.py test … -v 2` 의 ok·fail·expected failures 수 | 현재 **실행 이력 없음** (Docker 미기동) |
| 참신성 | 이 WP 자체는 차별점을 만들지 않는다 | — | **해당 없음.** 단 W0-3 의 "미등록 모델을 테스트가 구조적으로 잡는다"는 구조는 EXIT 에서 경쟁 대비 항목으로 재평가 |
| 보안 | 시크릿 스캔 0건 / 우회 목록 미증가 / 신규 외부 통신 0 | gitleaks · `BypassListTest` · settings diff | 스캔 0건(마지막 커밋 기준) / 우회 목록 7종(프레임워크만) |
| 코드 | 컨벤션 위반 0건 (신규 모델 `BaseModelWithGroup` 상속·격리 등록) | `verify_gates.sh` 게이트 6종 | 미측정 (백엔드 게이트는 컨테이너 필요) |

---

## 8. 사람이 해야 할 것

| 무엇 | 왜 사람이어야 하나 | 언제까지 | 없으면 어떻게 되나 |
|---|---|---|---|
| **① W0-2 의 DoD ③ 판정** — W0-14(WP-1) 를 WP-0 으로 당길지, 아니면 ③을 WP-1 로 이월하고 W0-2 를 ①②로 닫을지 | WP 구성 변경은 대표 승인 사항(D-216) | ENTRY 승인 시 | W0-2 가 WP-0 에서 닫히지 못해 goal 이 미달로 남는다. **권고: 이월** — ③은 W0-14 의 존재 확인일 뿐이고 실질 통제는 WP-1 의 산출물이다 |
| **② 사내망 방문 일정 승인** — §10 계획의 실행 승인 | 물리적 접근(192.168.0.22 + SSH 키) | 가능한 빨리 | verify-pending 4건이 계속 떠 있고 WP-1~4 가 그 위에 쌓인다 |
| **③ Docker Desktop 기동/설치 권한** | 로컬 관리자 권한 | 방문일 이전 | 백엔드 3건(W0-2·W0-3·W2-1) 검증 불가 |
| **④ W0-1b 실키 재발급 동반 처리 (권고)** | 발급기관 콘솔 접근 | 사내망 방문일 **같은 날** | WP-2 착수가 별도 방문을 한 번 더 요구한다. 같은 날 처리하면 방문 1회를 아낀다 |
| **⑤ W0-4 DoD 문구 정본 반영** (D-218) | `dod` 는 작성자 소유 필드 | 다음 정본 갱신 시 | 실효 DoD 와 정본이 계속 어긋난다 (§3-1) |

---

## 9. 예상 산출물

- 커밋 **4~6개** / 신규 파일 3개(`coverage.md`, `migration.sql`, `0016_detectionevent.py`) / 변경 파일 4~5개
- 증거: `docs/agent/evidence/{W0-2,W0-3,W2-1,W0-4,W0-10}/` — 방문 당일 로그 전문 포함
- **격리 테스트가 전부 green 이 아니어도 WP-0 은 닫는다.** WP-0 의 goal 은 "verify-pending 종결"이고,
  "격리 완결"은 WP-1 의 goal 이다. 실패는 분류되어 WP-1 입력이 되면 그것으로 이 WP 의 임무는 끝난다.

---

## 10. ★ 사내망 1회 방문 실행계획서 (이 검토서의 본체)

> 사람이 사내망 자리를 **한 번** 잡으면 그 자리에서 4건이 전부 종결되도록 순서를 고정했다.
> 각 단계는 **앞 단계가 실패해도 다음 단계를 시도**할 수 있게 배치했다(단 ①은 W0-4 의, ②는 백엔드 3건의 선행).
> 모든 출력은 `docs/agent/evidence/<티켓>/onprem-YYYYMMDD.log` 로 저장한다 (`tee`).

```bash
cd <repo>
mkdir -p docs/agent/evidence/{W0-2,W0-3,W2-1,W0-4}

# ── ⓪ 사전 확인 (30초) ────────────────────────────────────────────────
nc -z -w3 192.168.0.22 22 && echo INTRANET=OK        # 실패 시 → ① 건너뛰고 ②로
docker version --format '{{.Server.Version}}'         # 실패 시 → ②③④ 전부 보류, ①만 수행

# ── ① 프런트 의존성 + 빌드 (W0-4 · 부수: W0-8) ────────────────────────
cd frontend
npm install 2>&1 | tee ../docs/agent/evidence/W0-4/onprem-npm-install.log
npm ls rj-core @gaion/gcs-fe                          # 두 패키지가 실제로 들어왔는지
npm install --package-lock-only                       # W0-8 겸사 — lock 확보(커밋은 WP-2)
npm run build 2>&1 | tee ../docs/agent/evidence/W0-4/onprem-build.log
# ★ W0-4 판정 (D-218 문구 기준)
grep -rlE 'mockupDemoUi|setup-demo-(file|url)' dist/assets || echo "PASS: 데모 식별자 0건"
ls -la dist/assets | tee ../docs/agent/evidence/W0-4/onprem-chunks.txt
# 대조군 — 플래그 ON 이면 청크가 나와야 한다 (게이트가 실제로 작동하는 증거)
VITE_ENABLE_DEMO=true npm run build >/dev/null 2>&1
grep -rlE 'mockupDemoUi' dist/assets && echo "OK: ON 일 때는 청크 존재 — 게이트 유효"
npm run build >/dev/null 2>&1                          # 다시 OFF 빌드로 되돌려 놓는다
cd ..
```

**① 실패 분기**
- `npm install` 실패(SSH 키/권한) → **W0-4 는 verify-pending 유지.** 실패 로그를 증거로 남기고,
  `blocker` 에 "사내망 도달했으나 패키지 인증 실패"로 갱신. 나머지 단계는 그대로 진행.
- 빌드는 되는데 `dist/assets` 에 데모 식별자가 **나오면** → 코드 결함이다. 3-8 분류상 "코드 결함" →
  내가 고친다(청크명 힌트·`manualChunks` 확인). W0-4 는 `in_progress` 로 되돌린다.

```bash
# ── ② 백엔드 기동 + 마이그레이션 (W2-1) ───────────────────────────────
docker compose up -d backend redis
docker compose exec -T backend python manage.py showmigrations stream_monitors | tail -5
# ★ 되돌릴 수 없는 작업 — dry-run 을 먼저 증거로 남긴다 (§5)
docker compose exec -T backend python manage.py makemigrations stream_monitors --dry-run -v 2 \
  | tee docs/agent/evidence/W2-1/onprem-makemigrations-dryrun.log
docker compose exec -T backend python manage.py makemigrations stream_monitors
docker compose exec -T backend python manage.py sqlmigrate stream_monitors 0016 \
  | tee docs/agent/evidence/W2-1/migration.sql          # 적용 전 SQL 보존
docker compose exec -T backend python manage.py migrate 2>&1 \
  | tee docs/agent/evidence/W2-1/onprem-migrate.log
docker compose exec -T backend python manage.py makemigrations --check --dry-run; echo "exit=$?"
```

**② 실패 분기**
- `makemigrations` 가 **DetectionEvent 외의 변경까지 잡으면** → 다른 앱에 미적용 변경이 있다는 뜻이다.
  **적용하지 않고 중단**하고 dry-run 출력만 증거로 남긴다(hard_stop `data-destructive` 예방).
- `migrate` 실패 → 롤백: `migrate stream_monitors 0015` + 생성 파일 삭제. W2-1 은 verify-pending 유지.
- 성공 시 마이그레이션 파일을 **단독 커밋**한다 (`feat(stream_monitors): DetectionEvent 마이그레이션 [W2-1]`).

```bash
# ── ③ 격리 테스트 (W0-3 → W0-2) ───────────────────────────────────────
docker compose exec -T backend python manage.py test tests.test_tenant_isolation -v 2 2>&1 \
  | tee docs/agent/evidence/W0-3/onprem-isolation.log
# W0-2 전용 — 우회 목록 증가 금지
docker compose exec -T backend python manage.py test \
  tests.test_tenant_isolation.BypassListTest -v 2 2>&1 \
  | tee docs/agent/evidence/W0-2/onprem-bypass.log
grep -Ec "'(order|orderitem|payment|terminal)'" backend/common/base_model.py   # 기대: 0
```

**③ 실패 분기 — 실패는 정상이다**
| 실패 테스트 | 의미 | 처리 |
|---|---|---|
| `test_null_created_by_is_not_globally_visible` | `created_by` 없는 레코드가 전 테넌트에 보인다 | **예상된 실패.** `@expectedFailure` 등록 → **W0-13(WP-1)** 로 이관 |
| `test_registry_covers_all_isolatable_models` | 미등록 격리대상 모델이 있다 | **예상된 실패.** → **W0-14(WP-1)** |
| `test_unisolated_set_has_not_grown` | 격리 없는 모델이 늘었다 | 늘었으면 **원인 조사 후 WP-1**. 줄었으면 집합 갱신 |
| 그 외 실패(fixture·API 404 등) | 테스트 자체의 환경 가정 문제 | 원인만 분류해 `coverage.md` 에 기록. **테스트를 고쳐 통과시키지 않는다**(금지 #5) |

> `UserGroup.objects.first()` 2곳(`handover/services/handover_document_service.py:608`,
> `handover_notice_service.py:96`)은 이번에 **고치지 않는다.** D-208 위반 사례로 확인만 하고
> **W0-12(WP-1)** 로 이관한다.

```bash
# ── ④ W0-2 성능 대조 (DoD 는 아니지만 "우회 제거 = 성능 저하" 우려의 실증) ──
docker compose exec -T backend python manage.py shell -c "
import time
from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext
from django.apps import apps
D = apps.get_model('dashboard','Dashboard'); P = apps.get_model('dashboard','DashboardPanel')
for label, qs in (('Dashboard', D.objects.all()), ('DashboardPanel', P.objects.all())):
    t0=time.perf_counter()
    with CaptureQueriesContext(connection) as ctx:
        n=len(list(qs[:200]))
    print(f'{label}: rows={n} queries={len(ctx)} ms={(time.perf_counter()-t0)*1000:.1f}')
" 2>&1 | tee docs/agent/evidence/W0-2/onprem-perf.log
```

**왜 이 측정인가 (설계 근거).** 제거한 7종(`order`·`terminal` 등)은 전부 **dj-core 의 베이스**를 쓰고,
`common.base_model` 의 우회 목록이 실제로 관여하는 모델은 **`Dashboard`·`DashboardPanel` 2개뿐**이다(§2 실측).
그 2개는 애초에 목록에 없었으므로 **이번 변경으로 쿼리 계획이 바뀔 수 있는 대상은 0개**다.
따라서 측정의 목적은 "느려졌나"가 아니라 **"이 저장소 안에서 영향받는 표면이 정말 없는가"의 실증**이다.
합격선: 쿼리 수가 baseline(`4afca2b`) 대비 증가 0, p95 지연 증가 10% 이내.
증가가 관측되면 인덱스 → `select_related`/`prefetch_related` 순으로 해결한다. **우회로 되돌리지 않는다**(D-103).

```bash
# ── ⑤ (권고) 같은 날 함께: W0-1b 실키 재발급 — WP-2 소속이지만 방문 1회를 아낀다
```

---

## 11. 승인 후 즉시 착수하는 오프라인 작업 (사내망 불필요)

| 순서 | 작업 | 티켓 | 산출물 |
|---|---|---|---|
| 1 | `settings.py` 사설 IP·내부 도메인 13곳 → `env(...)` 기본값 플레이스홀더화 + `.env.example` 대응 항목 추가 | W0-10 | 커밋 1 |
| 2 | 예상 실패 3건에 `@expectedFailure` 명시 등록 (해제 조건 주석 포함) | W0-3 | 커밋 1 |
| 3 | `evidence/W0-3/coverage.md` 골격 작성 (수집 모델·EXEMPT 사유 표) — 수치는 방문 후 기입 | W0-3 | 신규 파일 |
| 4 | v3.1 정본에 5건의 `status`·`evidence`·`blocker` 재부착 (교체 시 유실분 복원) | 전체 | tickets.yaml |
| 5 | 기존 W0-4 증거를 **D-218 새 DoD 기준으로 재대조**한 대조표 추가 | W0-4 | evidence 갱신 |

---

**승인 요청 사항**: **§3(전제 차이 — 특히 6번 W0-10 의 `done` 정정과 5번 W0-2 의 WP 경계 DoD)** 과
**§5(되돌리기 — 마이그레이션 dry-run 절차)**, 그리고 **§10 사내망 실행 순서**를 봐 주십시오.
§8 의 ①(W0-2 DoD ③ 이월 여부)과 ②(방문 일정)가 승인의 실질 내용입니다.
