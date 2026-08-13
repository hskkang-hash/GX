#!/usr/bin/env bash
# verify_ticket.sh — GuardianX STEP 5 검증 러너
#
# 출처: GuardianX_개발작업지시서_v2.0.pdf §0.5 (STEP 5 공통 게이트 자동화)
#
#   ./docs/agent/verify_ticket.sh W1-3              # 공통 게이트 + 티켓 verify 전부
#   ./docs/agent/verify_ticket.sh W1-3 --gates-only # 공통 게이트만
#   ./docs/agent/verify_ticket.sh --gate secrets    # 단일 게이트만
#   ./docs/agent/verify_ticket.sh --list            # 게이트 목록
#
# 종료 코드: 0 통과 / 1 실패 / 2 사용법 오류 / 3 환경 미비
#
# ⚠ 이 스크립트 통과 = DoD 재현 아님. DoD는 사람이 재현하고 evidence 에 남긴다.

set -uo pipefail
export PYTHONIOENCODING=utf-8   # Windows 콘솔 cp949 → 한글 깨짐/인코딩 예외 방지

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TICKETS="$SCRIPT_DIR/tickets.yaml"
cd "$REPO_ROOT" || exit 3

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; DIM=$'\033[2m'; RST=$'\033[0m'
FAILED=0; PASSED=0; SKIPPED=0
TICKET_ID=""

pass()  { PASSED=$((PASSED+1));  printf '  %sPASS%s  %s\n' "$GRN" "$RST" "$1"; }
fail()  { FAILED=$((FAILED+1));  printf '  %sFAIL%s  %s\n' "$RED" "$RST" "$1"; }
skip()  { SKIPPED=$((SKIPPED+1)); printf '  %sSKIP%s  %s %s\n' "$YEL" "$RST" "$1" "${DIM}${2:-}${RST}"; }
head_() { printf '\n%s── %s%s\n' "$DIM" "$1" "$RST"; }

PY=""
for c in python python3 py; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
[ -z "$PY" ] && { echo "python 없음 — tickets.yaml 파싱 불가"; exit 3; }
$PY -c "import yaml" 2>/dev/null || { echo "PyYAML 없음 — pip install pyyaml"; exit 3; }

# ─────────────────────────────────────────────────────────────────────────────
# tickets.yaml 을 기동 시 1회만 파싱해 TSV 캐시로 굽는다.
#   형식: <id>\t<field>\t<base64(value)>
# 호출마다 heredoc를 만들면 Git Bash(MSYS)에서 임시파일 경합으로 간헐 실패한다.
# base64로 싸서 개행·UTF-8을 그대로 통과시킨다.
# ─────────────────────────────────────────────────────────────────────────────
CACHE="$(mktemp -t gxtickets.XXXXXX)"
trap 'rm -f "$CACHE"' EXIT

$PY - "$TICKETS" > "$CACHE" <<'PYEOF' || { echo "tickets.yaml 파싱 실패"; exit 3; }
import sys, yaml, base64
data = yaml.safe_load(open(sys.argv[1], encoding='utf-8')) or []
# v3 정본은 {meta, tickets} 딕셔너리, 구 스키마는 티켓 배열
tickets = data['tickets'] if isinstance(data, dict) else data
out = []
for t in tickets:
    tid = t.get('id')
    if not tid:
        continue
    for field, v in t.items():
        if isinstance(v, list):
            v = '\n'.join(str(x) for x in v)
        elif v is None:
            v = ''
        b = base64.b64encode(str(v).encode('utf-8')).decode('ascii')
        out.append(f"{tid}\t{field}\t{b}")
sys.stdout.write('\n'.join(out) + '\n')
PYEOF

# tq <id> <field>  — 없으면 rc=9
tq() {
  local line
  line=$(grep -m1 -F "$(printf '%s\t%s\t' "$1" "$2")" "$CACHE") || return 9
  printf '%s' "${line#*$'\t'*$'\t'}" | base64 -d
  echo
}

ticket_exists() { grep -q -F "$(printf '%s\tid\t' "$1")" "$CACHE"; }

# ─────────────────────────────────────────────────────────────────────────────
# §0.4 리팩터링 금지 구역
# ─────────────────────────────────────────────────────────────────────────────
FORBIDDEN_PATHS=(
  "backend/delivery/" "backend/orders/" "backend/terminals/"
  "frontend/src/features/Delivery" "frontend/src/features/Orders" "frontend/src/features/Terminal"
  "rj-core" "dj-core"
  "MapForRoute" "MapForRouteGoogle"
  "FormRoute.tsx"
)

# ─────────────────────────────────────────────────────────────────────────────
# GATE: secrets — .env* 에 실값 0개  (절대금지 #5)
# ─────────────────────────────────────────────────────────────────────────────
gate_secrets() {
  head_ "GATE secrets — .env.example 실값 검사"
  local files found=0
  files=$(find . -name ".env.example" -not -path "*/node_modules/*" 2>/dev/null)
  [ -z "$files" ] && { skip ".env.example 없음"; return 0; }

  for f in $files; do
    local bad
    bad=$($PY - "$f" <<'PYEOF'
import sys, re
placeholder = re.compile(
    # W0-0 spec 이 정한 플레이스홀더 형식: your-...-here / CHANGE_ME_...
    r'^\s*$|^your[-_]|[-_]here$|^change[-_]?me|^xxx+$|^<.*>$|^\$\{.*\}$|^placeholder$|^dummy$|^example$|^\*+$',
    re.I)
sensitive = re.compile(r'(KEY|SECRET|PASSWORD|TOKEN|USERNAME|APIKEY|CREDENTIAL)', re.I)
out = []
for n, line in enumerate(open(sys.argv[1], encoding='utf-8', errors='replace'), 1):
    line = line.rstrip('\n')
    if not line.strip() or line.lstrip().startswith('#') or '=' not in line:
        continue
    k, _, v = line.partition('=')
    v = v.strip().strip('"').strip("'")
    if sensitive.search(k) and not placeholder.match(v):
        out.append(f"{n}: {k.strip()}={v[:6]}…({len(v)}자)")
print('\n'.join(out))
PYEOF
)
    if [ -n "$bad" ]; then
      fail "$f 에 실값 의심 $(echo "$bad" | wc -l)건"
      echo "$bad" | sed 's/^/        /'
      found=1
    else
      pass "$f 실값 0개"
    fi
  done

  if command -v gitleaks >/dev/null 2>&1; then
    if gitleaks detect --source . --no-banner --redact >/dev/null 2>&1; then
      pass "gitleaks 스캔 클린"
    else
      fail "gitleaks 검출 — gitleaks detect --source . 로 확인"
      found=1
    fi
  elif command -v trufflehog >/dev/null 2>&1; then
    pass "trufflehog 존재 (수동 실행 필요)"
  else
    skip "시크릿 스캐너 미설치" "(W0-1 작업 4: gitleaks 또는 trufflehog CI 추가)"
  fi
  return $found
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: bypass — performance_bypass_models 에 업무 모델 없음  (절대금지 #6)
# ─────────────────────────────────────────────────────────────────────────────
gate_bypass() {
  head_ "GATE bypass — 권한 우회 목록 검사"
  local f="backend/common/base_model.py"
  [ -f "$f" ] || { fail "$f 없음"; return 1; }

  local found
  found=$($PY - "$f" <<'PYEOF'
import sys, re
src = open(sys.argv[1], encoding='utf-8', errors='replace').read()
m = re.search(r'performance_bypass_models\s*=\s*\[(.*?)\]', src, re.S)
if not m:
    print("LIST_NOT_FOUND"); sys.exit(0)
items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
business = {'order','orderitem','orderhistory','payment','ordercomment',
            'orderassignment','terminal'}
framework = {'coreuser','usergroup','role','userprofilelink',
             'multilanguagecontent','userprofile','group'}
bad = [i for i in items if i.lower() in business]
fw  = [i for i in items if i.lower() in framework]
unknown = [i for i in items if i.lower() not in business | framework]
print("BUSINESS:" + ",".join(bad))
print("FRAMEWORK:" + ",".join(fw))
print("UNKNOWN:" + ",".join(unknown))
PYEOF
)
  if echo "$found" | grep -q "LIST_NOT_FOUND"; then
    pass "performance_bypass_models 목록 자체가 없음 (완전 제거됨)"
    return 0
  fi

  local biz fw unk rc=0
  biz=$(echo "$found" | sed -n 's/^BUSINESS://p')
  fw=$(echo  "$found" | sed -n 's/^FRAMEWORK://p')
  unk=$(echo "$found" | sed -n 's/^UNKNOWN://p')

  if [ -n "$biz" ]; then
    fail "업무 데이터 모델이 아직 우회 목록에 있음: $biz"
    printf '        %sW0-2 작업1 미완 — 테넌트 간 데이터 노출 경로%s\n' "$DIM" "$RST"
    rc=1
  else
    pass "업무 데이터 모델 우회 0건"
  fi
  [ -n "$fw" ] && skip "프레임워크 모델 잔존: $fw" "(W0-2 작업2 — 뷰 레벨 필터로 대응)"
  if [ -n "$unk" ]; then
    fail "미분류 모델이 우회 목록에 추가됨: $unk  ← 절대금지 #6"
    rc=1
  fi
  return $rc
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: isolation — 테넌트 격리 테스트 존재·모델 등록  (절대금지 #4)
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_ISOLATION_MODELS=(Order Terminal StreamMonitor Dashboard Device
                           ChecklistSetting SurveillanceProfile Handover ReportTemplate)

gate_isolation() {
  head_ "GATE isolation — 테넌트 격리 테스트"
  local f="backend/tests/test_tenant_isolation.py"
  if [ ! -f "$f" ]; then
    fail "$f 없음 — W0-3 미완"
    return 1
  fi
  local rc=0 missing=""
  for m in "${REQUIRED_ISOLATION_MODELS[@]}"; do
    grep -q "\b$m\b" "$f" || missing="$missing $m"
  done
  if [ -n "$missing" ]; then
    fail "격리 테스트에 미등록 모델:$missing"
    rc=1
  else
    pass "필수 9모델 전부 등록"
  fi
  for s in list detail update delete export; do
    grep -q "test_${s}" "$f" || { fail "test_${s}_* 시나리오 없음"; rc=1; }
  done
  [ $rc -eq 0 ] && pass "5시나리오 전부 존재"

  # 스킵·비활성화 탐지 (절대금지 #4)
  if grep -nE '@(unittest\.)?(skip|expectedFailure)|@pytest\.mark\.(skip|xfail)|return  *# *TODO' "$f" >/dev/null 2>&1; then
    fail "격리 테스트에 skip/xfail 발견 ← 절대금지 #4"
    grep -nE '@(unittest\.)?(skip|expectedFailure)|@pytest\.mark\.(skip|xfail)' "$f" | sed 's/^/        /'
    rc=1
  fi
  return $rc
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: model-inheritance — 신규 Django 모델 BaseModelWithGroup 상속  (부록 A)
# ─────────────────────────────────────────────────────────────────────────────
gate_model_inheritance() {
  head_ "GATE model-inheritance — 신규 모델 상속 검사"
  has_baseline || { skip "베이스라인 없음 — 신규/기존 구분 불가" "($(baseline_note))"; return 0; }
  local changed
  changed=$(changed_files | grep -E 'backend/.*/models\.py$' || true)
  [ -z "$changed" ] && { skip "변경된 models.py 없음"; return 0; }

  local rc=0
  for f in $changed; do
    [ -f "$f" ] || continue
    local bad
    bad=$($PY - "$f" <<'PYEOF'
import sys, re
src = open(sys.argv[1], encoding='utf-8', errors='replace').read()
ok = ('BaseModelWithGroup', 'BaseModel')
bad = []
for m in re.finditer(r'^class\s+(\w+)\s*\(([^)]*)\)\s*:', src, re.M):
    name, bases = m.group(1), m.group(2)
    if 'Meta' in name or 'Serializer' in name or 'Admin' in name:
        continue
    if 'models.Model' in bases and not any(o in bases for o in ok):
        bad.append(name)
print('\n'.join(bad))
PYEOF
)
    if [ -n "$bad" ]; then
      fail "$f — models.Model 직접 상속: $(echo "$bad" | tr '\n' ' ')"
      printf '        %s부록 A: 신규 Django 모델은 BaseModelWithGroup 상속 필수%s\n' "$DIM" "$RST"
      rc=1
    else
      pass "$f 상속 규칙 준수"
    fi
  done
  return $rc
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: ui-library — 신규 FE 파일에 MUI/Bootstrap 금지  (부록 A)
# ─────────────────────────────────────────────────────────────────────────────
gate_ui_library() {
  head_ "GATE ui-library — 신규 FE 화면 AntD 전용"
  has_baseline || { skip "베이스라인 없음 — 신규/기존 구분 불가" "($(baseline_note))"; return 0; }
  local changed
  changed=$(changed_files | grep -E '^frontend/src/.*\.(ts|tsx)$' || true)
  [ -z "$changed" ] && { skip "변경된 FE 파일 없음"; return 0; }

  local rc=0
  for f in $changed; do
    [ -f "$f" ] || continue
    if grep -nE "from ['\"](@mui/|@material-ui/|react-bootstrap|bootstrap)" "$f" >/dev/null 2>&1; then
      fail "$f — MUI/Bootstrap 신규 사용"
      grep -nE "from ['\"](@mui/|@material-ui/|react-bootstrap|bootstrap)" "$f" | sed 's/^/        /'
      rc=1
    fi
    if grep -nE "from ['\"](react-kakao-maps|@react-google-maps)" "$f" >/dev/null 2>&1; then
      fail "$f — 지도 직접 호출 (MapForRouteUnified 래퍼 경유 필수)"
      rc=1
    fi
  done
  [ $rc -eq 0 ] && pass "$(echo "$changed" | wc -l)개 FE 파일 컨벤션 준수"
  return $rc
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: forbidden-zone — §0.4 금지구역 변경 검사
# 티켓의 reuse_targets 에 명시된 경로는 예외 (spec이 지목한 경우)
# ─────────────────────────────────────────────────────────────────────────────
gate_forbidden_zone() {
  head_ "GATE forbidden-zone — §0.4 금지구역 변경 검사"
  has_baseline || { skip "베이스라인 없음 — 변경분 판별 불가" "($(baseline_note))"; return 0; }
  local changed
  changed=$(changed_files)
  [ -z "$changed" ] && { skip "변경 파일 없음"; return 0; }

  local allow=""
  if [ -n "$TICKET_ID" ]; then
    allow=$(tq "$TICKET_ID" reuse_targets 2>/dev/null || true)
  fi

  local rc=0
  for f in $changed; do
    for p in "${FORBIDDEN_PATHS[@]}"; do
      case "$f" in
        *"$p"*)
          if [ -n "$allow" ] && echo "$allow" | grep -qF "$f"; then
            skip "$f — 금지구역이나 티켓 spec이 명시적으로 지목 (허용)"
          else
            fail "$f — §0.4 금지구역 변경 ← STOP(blocked)"
            rc=1
          fi
          ;;
      esac
    done
  done
  [ $rc -eq 0 ] && pass "금지구역 변경 0건"
  return $rc
}

# ─────────────────────────────────────────────────────────────────────────────
# 변경 파일 집합.
#
# ⚠ 베이스라인(HEAD 커밋)이 없으면 추적되지 않은 전 파일이 "신규"로 잡힌다.
#   그 상태에서 model-inheritance / ui-library / forbidden-zone 게이트를 돌리면
#   기존 45개 앱·93파일 모듈이 통째로 위반으로 뜬다 — 신호가 아니라 잡음이다.
#   따라서 베이스라인이 없으면 해당 게이트는 실행하지 않고 SKIP한다.
#
#   GX_BASELINE=<ref> 로 비교 기준을 바꿀 수 있다 (기본 HEAD).
# ─────────────────────────────────────────────────────────────────────────────
BASELINE="${GX_BASELINE:-HEAD}"
has_baseline() {
  git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1 &&
  git -C "$REPO_ROOT" rev-parse --verify "$BASELINE" >/dev/null 2>&1
}

changed_files() {
  has_baseline || return 0
  { git -C "$REPO_ROOT" diff --name-only "$BASELINE"
    git -C "$REPO_ROOT" ls-files --others --exclude-standard; } | sort -u
}

# 진단용: 베이스라인 부재 사유 1줄
baseline_note() {
  if ! git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    echo "git 저장소 아님"
  else
    echo "베이스라인 커밋($BASELINE) 없음 — 최초 커밋 후 재실행"
  fi
}

run_gate() {
  case "$1" in
    secrets)            gate_secrets ;;
    bypass)             gate_bypass ;;
    isolation)          gate_isolation ;;
    model-inheritance)  gate_model_inheritance ;;
    ui-library)         gate_ui_library ;;
    forbidden-zone)     gate_forbidden_zone ;;
    *) echo "알 수 없는 게이트: $1"; exit 2 ;;
  esac
}

ALL_GATES=(secrets bypass isolation model-inheritance ui-library forbidden-zone)

# ─────────────────────────────────────────────────────────────────────────────
usage() {
  sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 2
}

GATES_ONLY=0
case "${1:-}" in
  ""|-h|--help) usage ;;
  --list) printf '%s\n' "${ALL_GATES[@]}"; exit 0 ;;
  --gate)
    [ $# -ge 2 ] || usage
    run_gate "$2"; rc=$?
    printf '\n%s통과 %d · 실패 %d · 건너뜀 %d%s\n' "$DIM" "$PASSED" "$FAILED" "$SKIPPED" "$RST"
    exit $rc ;;
  -*) usage ;;
  *) TICKET_ID="$1"; [ "${2:-}" = "--gates-only" ] && GATES_ONLY=1 ;;
esac

# ── 티켓 로드 ────────────────────────────────────────────────────────────────
ticket_exists "$TICKET_ID" || { echo "${RED}티켓 없음: $TICKET_ID${RST}"; exit 2; }
TITLE=$(tq "$TICKET_ID" title)
PHASE=$(tq "$TICKET_ID" phase)
STATUS=$(tq "$TICKET_ID" status)
HGATE=$(tq "$TICKET_ID" human_gate)
DOD=$(tq "$TICKET_ID" dod)

printf '%s\n' "════════════════════════════════════════════════════════════════"
printf '  [%s] %s\n' "$TICKET_ID" "$TITLE"
printf '  phase=%s  status=%s  human_gate=%s\n' "$PHASE" "$STATUS" "$HGATE"
printf '%s\n' "════════════════════════════════════════════════════════════════"

# ── 선행 티켓 ────────────────────────────────────────────────────────────────
head_ "선행 티켓 (depends_on)"
DEPS=$(tq "$TICKET_ID" depends_on)
if [ -z "$DEPS" ]; then
  pass "선행 없음"
else
  for d in $DEPS; do
    ds=$(tq "$d" status 2>/dev/null || echo "?")
    if [ "$ds" = "done" ]; then pass "$d done"; else fail "$d status=$ds (done 아님)"; fi
  done
fi

# ── 공통 게이트 ──────────────────────────────────────────────────────────────
for g in "${ALL_GATES[@]}"; do run_gate "$g"; done

# ── 티켓별 verify ────────────────────────────────────────────────────────────
if [ $GATES_ONLY -eq 0 ]; then
  head_ "티켓 verify 명령"
  VERIFY=$(tq "$TICKET_ID" verify)
  if [ -z "$VERIFY" ]; then
    skip "verify 명령 없음"
  else
    while IFS= read -r cmd; do
      [ -z "$cmd" ] && continue
      case "$cmd" in
        manual:*) skip "${cmd#manual:}" "(사람이 재현)" ; continue ;;
      esac
      printf '  %s$ %s%s\n' "$DIM" "$cmd" "$RST"
      if out=$(bash -c "$cmd" 2>&1); then
        pass "$cmd"
      else
        fail "$cmd"
        echo "$out" | tail -20 | sed 's/^/        /'
      fi
    done <<< "$VERIFY"
  fi
fi

# ── DoD 고지 ─────────────────────────────────────────────────────────────────
head_ "DoD — 스크립트가 판정하지 않는다"
printf '  %s%s%s\n' "$YEL" "$DOD" "$RST"
printf '  %s→ 실제로 재현하고 tickets.yaml 의 evidence 에 증거 경로를 남길 것%s\n' "$DIM" "$RST"

printf '\n════════════════════════════════════════════════════════════════\n'
if [ $FAILED -eq 0 ]; then
  printf '  %sGATES PASS%s  통과 %d · 건너뜀 %d — DoD 재현 후 done 처리\n' "$GRN" "$RST" "$PASSED" "$SKIPPED"
  exit 0
else
  printf '  %sFAIL%s  통과 %d · 실패 %d · 건너뜀 %d\n' "$RED" "$RST" "$PASSED" "$FAILED" "$SKIPPED"
  printf '  %s3회 연속 실패 시 STOP(verify-failed)%s\n' "$DIM" "$RST"
  exit 1
fi
