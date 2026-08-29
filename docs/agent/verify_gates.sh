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

# ─────────────────────────────────────────────────────────────────────────────
# D-301 — **게이트는 "0건 검사했음"과 "검사하지 못했음"을 구분해야 한다.**
#
# 심어 보고 잡은 결함이 이 규칙을 만들었다: `$PY - <<'PYEOF'` 가 stdin 을 스크립트로
# 써서 앞의 파이프가 덮였고, 판정기는 **한 줄도 못 보면서 exit 0** 이었다.
# 아무것도 못 보면서 초록인 것은 게이트가 없는 것보다 나쁘다 — 있다는 착시를 준다.
#
# 그래서 모든 게이트는 **자기가 무엇을 몇 건 보았는지 말한다.** 말하지 않으면
# `run_gate` 가 그 게이트를 게이트로 인정하지 않는다(아래 GATE_INPUTS_MARK 판정).
#
#   inputs <건수> <무엇을 세었나> [0건일 때 사유]
#
# 0 건인데 사유가 없으면 그 자리에서 실패한다 — 0 건은 "볼 것이 없었다" 일 수도
# "보지 못했다" 일 수도 있고, 둘을 구별하는 유일한 것이 사유다 (D-264 의 게이트 판).
# ─────────────────────────────────────────────────────────────────────────────
GATE_INPUTS_MARK='[입력]'
inputs() {
  local n="${1:-}" what="${2:-}" why="${3:-}"
  case "$n" in (''|*[!0-9]*) fail "inputs: 건수가 수가 아니다: '${n}'"; return 1 ;; esac
  printf '  %s%s %s건 — %s%s
' "$DIM" "$GATE_INPUTS_MARK" "$n" "$what" "$RST"
  if [ "$n" -eq 0 ]; then
    if [ -z "$why" ]; then
      fail "입력 0건인데 사유가 없다 ← D-301 (검사 못함 ≠ 0건 검사)"
      return 1
    fi
    printf '  %s         0건 사유: %s%s
' "$DIM" "$why" "$RST"
  fi
  return 0
}

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
#
# .env.example 한 장을 훑는 판정기. **게이트와 자기시험이 같은 것을 쓴다** —
# 두 벌로 두면 자기시험만 통과하고 본 판정은 다른 규칙으로 도는 상태가 만들어진다.
# ─────────────────────────────────────────────────────────────────────────────
_secrets_scan() {
  $PY - "$1" <<'PYEOF'
import sys, re
placeholder = re.compile(
    # W0-0 spec 이 정한 플레이스홀더 형식: your-...-here / CHANGE_ME_...
    r'^\s*$|^your[-_]|[-_]here$|^change[-_]?me|^xxx+$|^<.*>$|^\$\{.*\}$|^placeholder$|^dummy$|^example$|^\*+$',
    re.I)
sensitive = re.compile(r'(KEY|SECRET|PASSWORD|TOKEN|USERNAME|APIKEY|CREDENTIAL)', re.I)

# ★ D-298 신규 키 형태 — **변수 이름에 KEY 가 없어도 값에 키가 들어올 수 있다.**
#   공공데이터포털·기상청 API 는 인증키를 질의문자열로 받는다. 그래서 실값을 붙여넣기
#   가장 쉬운 자리가 `..._URL=https://.../api?serviceKey=<실값>` 이고, 그 줄은
#   이름 필터(위 sensitive)를 **그냥 통과한다.** 이름이 아니라 **값의 모양**으로 한 겹 더 본다.
embedded = re.compile(
    r'(?:service_?key|auth_?key|api_?key|access_?key|apikey)\s*=\s*([^&\s"#]{8,})', re.I)
# 포털 인증키 두 형태 — 인코딩본(%2B·%3D%3D 포함)과 디코딩본(base64 60자+).
# .gitleaks.toml 의 gx-datago-service-key(-decoded) 와 **같은 것을 본다** —
# 두 눈이 같은 대상을 보는 것이지 다른 기준을 만드는 것이 아니다.
key_shape = (
    re.compile(r'[A-Za-z0-9]{20,}(?:%2B|%2F|%3D)[A-Za-z0-9%]{10,}(?:%3D%3D|%3D)'),
    re.compile(r'[A-Za-z0-9+/]{60,}={1,2}'),
)
out = []
for n, line in enumerate(open(sys.argv[1], encoding='utf-8', errors='replace'), 1):
    line = line.rstrip('\n')
    if not line.strip() or line.lstrip().startswith('#') or '=' not in line:
        continue
    k, _, v = line.partition('=')
    # 줄 끝 주석은 값이 아니다 — `KMA_WARNING_URL=   # 포털에서 실측` 을 실값으로 읽지 않는다.
    v = v.split('#', 1)[0].strip().strip('"').strip("'")
    if sensitive.search(k) and not placeholder.match(v):
        out.append(f"{n}: {k.strip()}={v[:6]}…({len(v)}자) [이름 규칙]")
        continue
    hit = embedded.search(v)
    if hit and not placeholder.match(hit.group(1)):
        out.append(f"{n}: {k.strip()} — URL 안에 인증키가 박혀 있다 "
                   f"({hit.group(1)[:6]}…{len(hit.group(1))}자) [D-298 신규 형태]")
        continue
    if any(shape.search(v) for shape in key_shape):
        out.append(f"{n}: {k.strip()} — 포털 인증키 형태의 값 [D-298 신규 형태]")
print('\n'.join(out))
PYEOF
}

gate_secrets() {
  head_ "GATE secrets — .env.example 실값 검사"
  local files found=0

  # ★ 판정 전에 판정기를 시험한다 (D-277 · D-289).
  #   ".env.example 에 실값 0개" 는 탐지기가 눈이 멀어도 나오는 문장이다.
  #   특히 D-298 로 **URL 안에 박힌 인증키**를 보게 넓혔는데, 그 눈이 실제로
  #   뜨였는지는 심어 봐야만 안다. 심는 값은 형태만 같은 **가짜**다.
  local plant hits
  plant=$(mktemp -d -t gxsecret.XXXXXX)
  {
    printf 'KMA_WARNING_URL=https://apis.data.go.kr/x/y?serviceKey=Ab3dEf9hIjKlMnOpQrStUvWxYz012345\n'
    printf 'DATA_GO_KR_KEY_ENCODED=8Fj2kLmNoPqRsTuVwXyZ0123456789ab%%2BcdEfGh%%3D%%3D\n'
    printf 'JUSO_API_KEY=\n'
    printf 'SCHOOL_LOCATION_URL=https://api.data.go.kr/openapi/tn_pubr_public_elesch_mskul_lc_api\n'
    printf 'KMA_APIHUB_KEY=            # 포털에서 실측\n'
  } > "$plant/.env.example"
  hits=$(_secrets_scan "$plant/.env.example" | grep -c . || true)
  rm -rf "$plant"
  if [ "$hits" = "2" ]; then
    pass "탐지기 자기시험 — 심은 실값 2건을 잡고, 빈 값·공개 URL·주석은 안 잡는다"
  else
    fail "탐지기 자기시험 실패 — 심은 2건 중 ${hits}건만 잡혔다. 이 게이트는 눈이 멀었다"
    return 1
  fi

  files=$(find . -name ".env.example" -not -path "*/node_modules/*" 2>/dev/null)
  local nfiles
  nfiles=$(printf '%s' "$files" | grep -c . || true)
  # ★ D-301 — 몇 장을 훑었는지 말한다. 0 장이면 "실값 0개"가 아니라 **아무것도 안 본 것**이다.
  inputs "$nfiles" ".env.example 파일"     "저장소에 .env.example 이 한 장도 없다 — W0-1a 산출물 자체가 사라졌다는 뜻이므로 통과로 읽지 않는다"     || return 1

  for f in $files; do
    local bad
    bad=$(_secrets_scan "$f")
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
print("COUNT:%d" % len(items))
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
    # ★ D-301 — 목록이 아예 없는 것과 목록이 비어 있는 것은 **다른 사실**이다.
    #   전자는 제거 완료(W0-2 목표), 후자는 정규식이 못 읽었을 수 있다.
    inputs 0 "우회 목록 항목"       "performance_bypass_models 목록 자체가 소스에 없다 — W0-2 로 완전 제거된 상태이며 셀 대상이 존재하지 않는다"       || return 1
    pass "performance_bypass_models 목록 자체가 없음 (완전 제거됨)"
    return 0
  fi
  local nitems
  nitems=$(echo "$found" | sed -n 's/^COUNT://p')
  inputs "${nitems:-0}" "우회 목록 항목"     "목록은 있는데 항목이 0개다 — 정규식이 못 읽었을 가능성을 배제하지 못하므로 사유로 남긴다"     || return 1

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
  # ★ D-301 — 무엇을 몇 건 대조했는가. 필수 모델 목록이 비면 이 게이트는
  #   "전부 등록됨"을 **아무것도 안 보고** 말하게 된다.
  inputs "${#REQUIRED_ISOLATION_MODELS[@]}" "대조할 필수 격리 모델"     "REQUIRED_ISOLATION_MODELS 가 비었다 — 목록이 지워지면 이 게이트는 늘 초록이다"     || return 1
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
  [ $rc -eq 0 ] && pass "읽기 5시나리오 전부 존재"

  # ── 쓰기 방향 (D-290) ──────────────────────────────────────────────────
  # 읽기 다섯은 전부 **남의 레코드를 지목해** 무슨 일이 나는가를 묻는다. 지목할 것이
  # 이미 있다는 전제다. D-290 이 잡은 구멍은 그 전제 밖 — 남의 id 를 적어 **남의 테넌트에
  # 새 행을 심는 것**이었다. 심긴 행은 그 테넌트의 정상 데이터처럼 보여 읽기 시험이
  # 영영 못 잡는다. 그래서 쓰기 시나리오를 **이름으로** 요구한다 (수가 아니다 — D-285 ②).
  local wrc=0
  for w in create_into_another_tenant_is_refused            update_of_another_tenant_row_is_refused            positive_control_own_tenant_succeeds            probe_registry_covers_kernel_writes; do
    grep -q "test_write_${w}" "$f" || { fail "test_write_${w} 없음 ← D-290"; wrc=1; }
  done
  [ $wrc -eq 0 ] && pass "쓰기 4시나리오 전부 존재 (양성 대조·래칫 포함)"
  [ $wrc -ne 0 ] && rc=1

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
  local changed nchanged
  changed=$(changed_files | grep -E 'backend/.*/models\.py$' || true)
  nchanged=$(printf '%s' "$changed" | grep -c . || true)
  # ★ D-301 — 변경된 models.py 가 0 건인 것은 정상이다(모델을 안 건드린 커밋).
  #   그러나 그 사실을 **말하지 않으면** 파이프가 끊겨 0 건이 된 경우와 구별되지 않는다.
  inputs "$nchanged" "변경된 models.py"     "베이스라인($BASELINE) 대비 변경된 models.py 가 없다 — 신규 모델이 태어나지 않은 커밋이다"     || return 1
  [ "$nchanged" -eq 0 ] && { skip "볼 대상 없음" "(0건 사유는 위 [입력] 줄에 있다)"; return 0; }

  local rc=0
  for f in $changed; do
    [ -f "$f" ] || continue
    local bad added
    # ★ **추가된 줄만** 본다 (2026-08-31 수정).
    #
    #   고치기 전에는 변경된 models.py 의 **모든** 클래스를 훑었다. 그래서 그 파일에
    #   한 글자만 고쳐도 이미 있던 위반(DrawingElement · DrawingParticipant ·
    #   StreamMonitorRecord — 전부 W0-0 베이스라인 이전 것)이 함께 빨개졌다.
    #   게이트의 이름은 "**신규** 모델 상속 검사" 인데 판정은 전수였던 것이다.
    #
    #   빨간불이 내가 한 일 때문인지 원래 그랬는지 구별되지 않으면 그 게이트는
    #   곧 꺼진다 — D-249 가 이름 붙인 실패 모양(부착률 착시)의 반대편이다.
    #   그래서 베이스라인 대비 **추가된 줄**의 class 선언만 판정한다.
    #   기존 빚은 그대로 두고 새 빚만 막는다 — deprecated-base 게이트와 같은 방식이다.
    added=$(git -C "$REPO_ROOT" diff -U0 "$BASELINE" -- "$f" 2>/dev/null \
              | grep -E '^\+' | grep -vE '^\+\+\+' | sed 's/^+//')
    # 추적되지 않는 새 파일은 diff 가 비어 있다 — 그때는 파일 전체가 신규다.
    if [ -z "$added" ] && ! git -C "$REPO_ROOT" ls-files --error-unmatch "$f" >/dev/null 2>&1; then
      added=$(cat "$f")
    fi
    local nadded
    nadded=$(printf '%s' "$added" | grep -c . || true)
    inputs "$nadded" "$f 의 추가된 줄"       "이 파일에서 베이스라인 대비 추가된 줄이 없다 — 삭제·이동만 있었다" || return 1
    if [ -z "$added" ]; then
      pass "$f — 추가된 class 선언 없음"
      continue
    fi
    # ★ 추가분을 **임시 파일로 넘긴다.** 파이프로 넘기려던 첫 판은 조용히 틀렸다:
    #   `$PY - <<'PYEOF'` 는 **stdin 을 스크립트로 쓴다.** 앞의 파이프는 그 heredoc 에
    #   덮여 사라지고, 파이썬은 심어 둔 위반을 한 줄도 못 본다 — 그런데도 exit 0 이라
    #   초록이 나온다. 양성 대조(심은 위반을 잡는가)를 돌리지 않았으면 못 봤을 결함이다.
    local addfile
    addfile="$(mktemp -t gxadded.XXXXXX)"
    printf '%s\n' "$added" > "$addfile"
    bad=$($PY - "$addfile" <<'PYEOF'
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
    rm -f "$addfile"
    if [ -n "$bad" ]; then
      fail "$f — 신규 모델이 models.Model 을 직접 상속: $(echo "$bad" | tr '\n' ' ')"
      printf '        %s부록 A: 신규 Django 모델은 group 격리를 받는 기저를 상속한다%s\n' "$DIM" "$RST"
      rc=1
    else
      pass "$f 신규 상속 규칙 준수"
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
  local nchanged
  nchanged=$(printf '%s' "$changed" | grep -c . || true)
  inputs "$nchanged" "변경된 FE 파일"     "베이스라인($BASELINE) 대비 변경된 frontend/src 파일이 없다 — 이번 변경은 BE 전용이다"     || return 1
  [ "$nchanged" -eq 0 ] && { skip "볼 대상 없음" "(0건 사유는 위 [입력] 줄에 있다)"; return 0; }

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
  local changed nchanged
  changed=$(changed_files)
  nchanged=$(printf '%s' "$changed" | grep -c . || true)
  inputs "$nchanged" "베이스라인 대비 변경 파일"     "변경 파일이 0건이다 — 작업 트리가 베이스라인과 같다. 금지구역 판정의 대상 자체가 없다"     || return 1
  [ "$nchanged" -eq 0 ] && { skip "볼 대상 없음" "(0건 사유는 위 [입력] 줄에 있다)"; return 0; }

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

# ─────────────────────────────────────────────────────────────────────────────
# GATE: deprecated-base — DEPRECATED 기저 클래스 상속 허용목록  (D-295)
# ─────────────────────────────────────────────────────────────────────────────
# `BaseModelWithGroup` 은 제거하지 **않기로** 판정했다(D-295) — 8개 앱이 상속 중이고
# dj-core 는 §0.4 금지구역이라 동시 수정은 이득 대비 위험이 크다. 제거하지 않기로 했으면
# 남는 일은 하나다: **새 상속이 늘지 않게 막는 것.**
#
# 위의 model-inheritance 게이트와 다른 것을 본다:
#   · model-inheritance : 신규 모델이 `models.Model` 을 **직접** 상속하는가 (격리 누락)
#   · deprecated-base   : 신규 모델이 **DEPRECATED 기저**를 상속하는가 (빚 증가)
# 둘을 한 함수에 넣지 않는 이유는 실패 사유가 다르기 때문이다 — 한 칸에 두면
# 빨간불의 뜻이 둘이 되고, 뜻이 둘인 빨간불은 읽히지 않는다.
gate_deprecated_base() {
  head_ "GATE deprecated-base — DEPRECATED 기저 클래스 상속 검사 (D-295)"
  local out rc

  # ★ 판정 전에 **판정기부터 시험한다** (D-277). 대상이 전부 허용목록 안이면
  #   이 게이트는 늘 초록이고, 늘 초록인 게이트는 초록의 뜻이 없다.
  if out=$($PY scripts/verify_model_inheritance.py --self-test 2>&1); then
    pass "탐지기 자기시험 통과"
  else
    fail "탐지기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_model_inheritance.py 2>&1); rc=$?
  # ★ D-301 — 판정기는 이미 전수를 센다("[INH] 상속 N건"). 그 수를 게이트가
  #   **밖으로 말하게** 한다. 전수가 0 이면 판정기 자신이 exit 1 하지만(D-271 ②),
  #   게이트를 읽는 사람에게도 "몇 건을 보고 한 말인가"가 보여야 한다.
  local nscanned
  nscanned=$(echo "$out" | grep -o "상속 [0-9]*건" | head -1 | tr -dc "0-9")
  inputs "${nscanned:-0}" "AST 로 훑은 기저클래스 상속"     "판정기가 상속 건수를 말하지 않았다 — 출력 형식이 바뀌었거나 판정기가 아무것도 못 봤다"     || return 1
  if [ $rc -eq 0 ]; then
    pass "$(echo "$out" | head -1)"
    return 0
  fi
  fail "허용목록 밖 신규 상속"
  echo "$out" | sed 's/^/        /'
  return 1
}

_dispatch_gate() {
  case "$1" in
    secrets)            gate_secrets ;;
    bypass)             gate_bypass ;;
    isolation)          gate_isolation ;;
    model-inheritance)  gate_model_inheritance ;;
    deprecated-base)    gate_deprecated_base ;;
    ui-library)         gate_ui_library ;;
    forbidden-zone)     gate_forbidden_zone ;;
    *) echo "알 수 없는 게이트: $1"; exit 2 ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# D-301 강제 도구 — **건수 출력이 없는 게이트는 게이트로 인정하지 않는다.**
#
# 규칙을 주석으로만 적으면 다음에 추가되는 게이트가 조용히 그것을 빠뜨린다
# (D-286 이 이름 붙인 실패 모양). 그래서 러너가 판정한다: 게이트의 출력에
# `[입력]` 표시가 한 줄도 없으면 그 게이트는 **실패**다. 결과가 초록이어도 그렇다 —
# 무엇을 보고 한 말인지 모르는 초록은 초록이 아니다.
#
# ⚠ 출력을 `$(...)` 로 잡지 않고 임시 파일로 받는 이유: 명령 치환은 서브셸이라
#   PASSED/FAILED 증가가 **부모에 남지 않는다.** 그러면 집계가 조용히 0 이 되고,
#   그것이 바로 이 결정문이 금지한 "아무것도 못 보면서 초록" 이다.
# ─────────────────────────────────────────────────────────────────────────────
run_gate() {
  local log rc
  log="$(mktemp -t gxgate.XXXXXX)"
  _dispatch_gate "$1" > "$log" 2>&1
  rc=$?
  cat "$log"
  if ! grep -qF "$GATE_INPUTS_MARK" "$log"; then
    fail "게이트 '$1' 이 입력 건수를 말하지 않았다 ← D-301 (건수 없는 게이트는 게이트가 아니다)"
    rc=1
  fi
  rm -f "$log"
  return $rc
}

ALL_GATES=(secrets bypass isolation model-inheritance deprecated-base ui-library forbidden-zone)

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
