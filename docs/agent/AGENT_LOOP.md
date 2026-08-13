# GuardianX 자동 구현 루프 v2.0 — 최종 Phase 완주용 실행 프롬프트

> **v2.0 변경점 (v1.0에서 실제 실행 후 발견된 문제 반영)**
> 1. **STEP 0 무결성 검사 추가** — 티켓 레지스트리를 PDF에서 역복원하다 7건 누락된 사고 방지 (D-012)
> 2. **STEP 2.5 결정 조회 추가** — CLARIFY 직전에 `decisions.yaml`을 먼저 본다. 이미 답이 있으면 멈추지 않는다
> 3. **gate 이원화** — `evidence-review`는 증거 제출로 자동 통과, `human-required`만 STOP. **정지 지점 22 → 9**
> 4. **Phase 자동 승격** — R1→R2→R3를 조건 충족 시 에이전트가 스스로 넘어간다 (D-011)
> 5. **환경 문제와 코드 문제 분리** — 컨테이너 미가용은 FAIL이 아니라 `env-unavailable` (D-007)
>
> **사용법**: 이 파일 전체를 Claude Code에 붙여넣고 실행한다.

---

## 역할

당신은 GuardianX 코드베이스의 **구현 에이전트**다.
목표는 **최종 Phase(R3)까지 완주**하는 것이되, 티켓을 많이 처리하는 것이 아니라
**DoD를 실제로 재현할 수 있는 변경만 안전하게 누적**하는 것이다.

멈추는 것은 실패가 아니다. 그러나 **멈출 이유가 이미 답해져 있는데 멈추는 것**은 낭비다.
그래서 v2.0은 `decisions.yaml`을 먼저 본다.

## 입력 파일

| 파일 | 역할 | 당신의 권한 |
|---|---|---|
| `agent/tickets.yaml` | **티켓 정본** (58개) | `status` `blocker` `evidence` `updated_at` `meta.active_phase` `meta.baseline_sha` **만** 수정 |
| `agent/decisions.yaml` | **사전 결정 레지스트리** (20건) | 읽기 전용 — 제안만, 수정 금지 |
| `agent/tickets.sha256` | 정본 체크섬 | 읽기 전용 |
| `docs/GuardianX_개발작업지시서_v3.0.md` | 규칙·컨벤션·금지구역 | 읽기 전용 |
| 소스 루트 `./` | 구현 대상 | 티켓 PLAN에 적은 파일만 수정 |

## 전역 변수
```
ACTIVE_PHASE   = tickets.yaml meta.active_phase
MAX_ITERATIONS = 12          # 한 세션에서 처리할 최대 티켓 수
VERIFY_RETRY   = 3
AUTO_PROMOTE   = true        # D-011: 조건 충족 시 Phase 자동 승격
```

---

# STEP 0 — 무결성 검사 (세션 시작 시 1회, 필수)

```
0-1. agent/tickets.yaml 을 읽는다.
0-2. meta.manifest.total 과 실제 tickets 배열 길이를 비교한다.
0-3. meta.manifest.ids 와 실제 id 목록을 비교한다 (누락·추가 확인).
0-4. sha256sum agent/tickets.yaml 을 agent/tickets.sha256 과 비교한다.
     ※ 이전 세션에서 status를 수정했다면 SHA는 달라진다. 이때는 0-2/0-3만 통과하면 된다.
     ※ 0-2 또는 0-3이 불일치하면 → STOP(registry-mismatch)
0-5. agent/decisions.yaml 을 읽어 메모리에 올린다.
0-6. 현재 상태를 출력한다: ACTIVE_PHASE / phase별 done·ready·blocked 수 / baseline_sha
```

> ⚠️ **tickets.yaml 을 PDF·MD 문서에서 재구성하지 않는다 (D-012).**
> 실제로 v1.0 실행 시 PDF 역복원으로 R2 4건·R3 3건이 누락된 사고가 있었다.
> 파일이 없으면 만들지 말고 STOP(registry-missing) 하고 정본을 요청한다.

---

# 루프 본문 (STEP 1~7 반복)

## STEP 1 — SELECT

```
조건:  status == "ready"
       phase  == ACTIVE_PHASE
       depends_on 의 모든 티켓 status ∈ {done}
정렬:  priority(P0>P1>P2) → effort(S>M>L>XL) → id 오름차순
```
- 선택한 id와 이유 1줄 출력, `status = in_progress`
- 없으면 → **STEP 7의 Phase 승격 판정**으로 간다 (바로 STOP 하지 않는다)

## STEP 2 — REVIEW (지시 검토) ⚠️ 건너뛰지 말 것

표로 출력한다.

| # | 점검 | 방법 |
|---|---|---|
| 2-1 | **재사용 대상 실독** | `reuse_targets` 전부 **실제로 읽는다** |
| 2-2 | **가정 검증** | spec이 전제한 모델·함수·라우트·필드가 실재하는가 |
| 2-3 | **금지구역** | 수정 대상이 §0.4 금지구역인가 |
| 2-4 | **스펙 완결성** | `dod` 재현에 필요한 정보가 다 있는가 |
| 2-5 | **부수효과** | 다른 티켓·기존 기능을 깨뜨릴 가능성 |

**2-1 없이 STEP 3으로 가는 것을 금지한다.** 읽지 않으면 반드시 중복 구현이 된다.

## STEP 2.5 — 결정 조회 (v2.0 신규) ⚠️ CLARIFY 전에 반드시

STEP 2에서 문제를 발견했다면, **CLARIFY를 선언하기 전에** 아래를 수행한다.

```
1) 티켓의 decisions: [D-xxx] 필드를 확인한다 → 해당 결정을 적용한다
2) decisions.yaml 전체를 문제 키워드로 검색한다
   (CI / 시크릿 / 키 분리 / 커밋 순서 / baseline / npm / 테스트 환경 /
    마이그레이션 / 브랜치 / 성능 / 기존 구현 충돌 / DoD 수치 / i18n / 라우트 네이밍)
3) status == decided 인 결정이 있으면 → **그 결정을 따르고 PROCEED** 한다.
   적용한 결정 id를 출력한다.  예: "D-102 적용 → 응답 p95 300ms 기준 채택"
4) 결정에 dod_override 가 있으면 티켓 DoD 대신 그것을 사용한다.
5) 해당 결정이 없을 때만 CLARIFY 한다.
   이때 질문을 **D-XXX 초안 형식**으로 제안한다 (사람이 그대로 붙여넣을 수 있게):
     - id: D-2xx
       title: "..."
       question: "..."
       options: [A안: ..., B안: ...]
       recommend: "A안 — 이유"
```

### 판정
- **`PROCEED`** → STEP 3
- **`CLARIFY`** → decisions.yaml에도 없는 진짜 새 질문. `status=blocked`, D-XXX 초안 기록, STOP
- **`BLOCKED`** → 금지구역·선행 미충족. `status=blocked`, 사유 기록, STOP

## STEP 3 — PLAN

```
변경/생성 파일: (경로 : 할 일 1줄)
추가 테스트:
적용한 결정:  D-xxx (있으면)
예상 위험 1~3
스코프 확인: 티켓 spec 범위 내인가 [예/아니오]
```
"아니오"면 STEP 2.5로 되돌아간다(스코프 크립 차단).

## STEP 4 — IMPLEMENT

PLAN에 적은 파일만 수정한다. 벗어나면 STEP 3으로 돌아가 계획을 갱신한다.

**구현 규칙**
1. 새 Django 모델 → `BaseModelWithGroup` 상속 **+** 격리 테스트 등록을 **같은 커밋**에 (D-108)
2. 신규 FE 화면 → **Ant Design만**. 지도는 `MapForRouteUnified` 경유. 상태관리는 Zustand
3. 신규 앱 생성 **금지** — 기존 45개 앱 중 적합한 곳에 추가
4. 무거운 작업 → Celery + Channels
5. **성능 문제를 권한 필터 우회로 해결 금지** (D-103: 인덱스→prefetch→분할→캐시 순, 5번은 금지)
6. `.env*`에 실제 값 기입 금지
7. 신규 화면 → i18n **ko/en/th 3종 동시** 추가 (D-106)
8. 기능 변경 → 사용자매뉴얼 항목 같은 커밋에 (D-108)
9. 브랜치 `w/<TICKET_ID>-<slug>`, 커밋은 Conventional Commits, **머지는 하지 않는다** (D-008)

## STEP 5 — VERIFY

### 5-0. 환경 확인 (v2.0 신규 — D-007)
```bash
docker compose ps backend >/dev/null 2>&1 || echo "ENV_UNAVAILABLE:backend"
node --version >/dev/null 2>&1 || echo "ENV_UNAVAILABLE:node"
```
환경 미가용 시 → **FAIL이 아니라 `BLOCKED(env-unavailable)`** 로 보고한다.
**코드 문제와 환경 문제를 절대 섞지 않는다.**

### 5-1. 공통 게이트
```bash
cd frontend && npm run lint && npm run type-check          # npm 확정 (D-006)
docker compose exec -T backend python manage.py makemigrations --check --dry-run
docker compose exec -T backend python manage.py test tests.test_tenant_isolation
```
※ baseline_sha 가 비어 있으면 컨벤션 검사는 **SKIP + 사유 출력** (D-005)

### 5-2. 티켓 게이트
티켓 `verify` 배열을 순서대로 실행.

### 5-3. DoD 게이트 (가장 중요)
`dod`(또는 결정의 `dod_override`)를 **실제로 재현**하고 증거를 남긴다.
- 화면 → 스크린샷 경로 / API → 요청·응답 로그 / 성능 → 측정값
- `tickets.yaml` 의 `evidence` 에 기록한다
- 정량 기준이 모호하면 **D-102 기본값**을 적용한다 (CLARIFY 하지 않는다)

**"코드는 다 짰다"는 완료가 아니다.**

### 실패 처리
STEP 4로 복귀 → 3회 연속 실패 시 `status=blocked`, 로그 기록, STOP(`verify-failed`)

## STEP 6 — REPORT & COMMIT

1. 브랜치에 커밋 (머지 금지)
2. `tickets.yaml` 갱신 — **gate에 따라 분기 (v2.0 핵심)**
   ```
   gate == "human-required"   → status = "review"  → STOP(awaiting-human)
   gate == "evidence-review"  → evidence 가 있으면 status = "done" → 계속
                                evidence 가 없으면 status = "review" → STOP
   ```
3. 3줄 요약: `변경: / DoD: (증거 경로) / 다음:`

## STEP 7 — GATE & PHASE 승격

```
if gate == "human-required" and status == "review":
        → STOP(awaiting-human-review)

if ACTIVE_PHASE 에 ready 티켓이 없다:
        → Phase 승격 판정 (아래)

if MAX_ITERATIONS 도달:  → STOP(iteration-limit)
else: → STEP 1
```

### Phase 자동 승격 판정 (D-011)
```
조건 A: ACTIVE_PHASE 의 P0 티켓이 전부 done
조건 B: 미완 티켓이 gate=="human-required" 뿐
조건 C: Phase Exit 체크리스트 중 '코드로 검증 가능한 항목' 전부 green

A∧B∧C 이면:
   1) meta.active_phase 를 다음 phase 로 변경 (R1→R2→R3)
   2) 해당 phase 티켓 status 를 backlog → ready 로 승격
   3) 승격 사실 + 미완 human-required 목록을 **명시적으로 보고**
   4) 계속 진행한다 (STOP 하지 않는다)

⚠️ R2 승격 예외: W6-0(H100 실측) 결과가 없으면
   W6-1(GPU 파이프라인)만 blocked 로 두고 나머지 R2 는 진행한다.

A∧B∧C 가 아니면 → STOP(phase-incomplete) + 미충족 항목 목록 출력
R3 까지 전부 완료되면 → STOP(all-phases-complete) + 최종 리포트
```

---

# STOP 조건 (11종)

| 코드 | 상황 | 보고 내용 |
|---|---|---|
| `registry-mismatch` | manifest와 실제 티켓 불일치 | 누락/추가 id 목록 |
| `registry-missing` | tickets.yaml 없음 | 정본 요청 |
| `no-ready-ticket` | 집을 티켓 없음 | 사유 (done/blocked/선행미완) |
| `clarify` | decisions.yaml에도 없는 새 질문 | **D-XXX 초안** (options + recommend) |
| `blocked` | 금지구역·선행 미충족 | 저촉 파일·사유 |
| `verify-failed` | 검증 3회 실패 | 실패 로그 전문 |
| `env-unavailable` | 컨테이너/Node 미가용 | 어떤 환경이 없는지 |
| `awaiting-human-review` | human-required 완료 | 사람이 할 일 |
| `phase-incomplete` | 승격 조건 미충족 | 미충족 항목 목록 |
| `all-phases-complete` | **R3까지 완주** | 최종 리포트 |
| `destructive-migration` | 데이터 파괴 가능 (D-009) | 영향 테이블·행 수 |

---

# 절대 금지 (하나라도 어기면 그 작업 무효)

1. `reuse_targets`를 읽지 않고 구현
2. DoD 미재현 상태로 `done` 처리
3. 티켓에 없는 리팩터링
4. **테넌트 격리 테스트 비활성화·스킵·수정** (D-105: 테스트가 틀린 것 같아도 STOP하고 보고)
5. `.env*`에 실제 값 기입
6. **권한 우회 목록에 항목 추가** (D-103 — W0-2가 그 실수의 결과)
7. `CLARIFY`/`BLOCKED` 판정 후 그냥 진행
8. **tickets.yaml을 PDF/MD에서 재구성** (D-012)
9. 기존 구현과 **나란히 하나 더 만들기** (D-101 — 데이터 이원화)
10. 외부 AI 서비스(guardianx-ai / media-ai-svc / gx-ai-analysis-vn) 코드 수정 (D-104)

---

# 지금 당장 할 일 (2026-08-13 기준 실행 상태)

이전 세션은 **W0-1에서 STOP(clarify)** 했다. 그 CLARIFY는 **전부 해소되었다.**

| 이전 질문 | 해소 |
|---|---|
| CI 플랫폼이 없다 | **D-001** — GitHub Actions 파일 + 로컬 pre-commit 병행. DoD 재정의 완료 |
| 실키 백업 위치 | **D-002** — 저장소 밖 암호화 보관 |
| GCS/VITE_CGS 동일 UUID | **D-003** — 값 분리 + 도메인 제한 + W0-5로 proxy 전환 |
| 커밋이 없어 최초 커밋 시 실키 유입 | **D-004** — **W0-0 신설**, 치환 후 최초 커밋 |
| baseline 없어 전체가 '신규'로 오탐 | **D-005** — W0-0 커밋이 baseline. 없으면 SKIP |
| yarn 미설치 | **D-006** — npm 확정, yarn.lock 삭제 |
| celery 미설치 | **D-007** — 컨테이너에서 실행, 미가용은 env-unavailable |

**따라서 다음 순서로 재개한다.**
```
1. STEP 0 무결성 검사 (58개 티켓 확인)
2. W0-0 부터 시작한다  ← W0-1이 아니다. 순서가 바뀌었다 (D-004)
   ⚠️ W0-0의 실값 치환 전에 "백업 완료" 확인을 받아야 한다(D-002).
      확인이 없으면 STOP 한다.
3. W0-1a (에이전트) → W0-1b (사람, STOP) → 나머지
```

---

# 사람만 할 수 있는 일 — 9건 (gate: human-required)

| id | 내용 | 왜 |
|---|---|---|
| `W0-1b` | 실키 15개 폐기·재발급 | 외부 콘솔 접근 |
| `W0-6` | 원격 저장소 생성 + CI 최초 green | 저장소·권한 설정 |
| `W5-3` | 이노뎁 VURIX 연동 검증 | 파트너사 환경 |
| `W6-0` | H100 24시간 임대 실측 | 결제·프로비저닝 |
| `W11-1` | CSAP 신청 | 대외 행정 |
| `W13-1` | 에이전틱 임무 (에스엘즈) | 외부사 공동개발 |
| `W16-1` | 파일럿 앱 | 사업 판단 |
| `B-07` | AI 모델·데이터 소유권 실사 | 계약·경영 |
| `B-08` | 상표 출원 | 법무 |

**나머지 49건은 `evidence-review`** — 증거를 남기면 에이전트가 스스로 통과시킨다.

---

# 최종 완주 리포트 형식 (all-phases-complete 시)

```
=== GuardianX 전 Phase 완주 리포트 ===
기간: YYYY-MM-DD ~ YYYY-MM-DD
처리: R1 xx/28 · R2 xx/14 · R3 xx/8 · BACKLOG xx/8

[완료]      티켓 id 목록
[미완-사람] human-required 중 미처리 목록 + 각각 필요한 조치
[블로커]    blocked 티켓과 사유
[적용 결정] 사용한 D-xxx 목록
[신규 제안] 새로 필요해진 D-2xx 초안 목록
[백로그 승격 제안] promote_when 충족 항목

Phase Exit 체크리스트 최종 상태:
  R1: [x] ... [ ] ...
  R2: ...
  R3: ...
```
