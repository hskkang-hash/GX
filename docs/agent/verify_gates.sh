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
FAILED=0; PASSED=0; SKIPPED=0; WAITING=0
TICKET_ID=""

pass()  { PASSED=$((PASSED+1));  printf '  %sPASS%s  %s\n' "$GRN" "$RST" "$1"; }
fail()  { FAILED=$((FAILED+1));  printf '  %sFAIL%s  %s\n' "$RED" "$RST" "$1"; }
skip()  { SKIPPED=$((SKIPPED+1)); printf '  %sSKIP%s  %s %s\n' "$YEL" "$RST" "$1" "${DIM}${2:-}${RST}"; }

# ★ [P-12 ④ · 2026-09-16 판정] **「못 잼」 안에 성격이 다른 둘이 섞여 있었다.**
#
#     못 잼 : 볼 것이 있는데 **못 봤다**   ← 자격증명이 없다 · 도구가 없다 · 서버가 없다
#     대기  : 볼 것이 **설계상 0건이다**   ← 이번 변경에 models.py 가 없다 · FE 파일이 없다
#
#   앞의 것은 **빚**이다. 갚아야 하고, 갚을 때까지 그 자리는 안 지켜진다.
#   뒤의 것은 빚이 아니다. 게이트는 멀쩡히 서 있고 다만 이번엔 지나갈 것이 없었다.
#   둘을 한 칸에 넣으면 「회색 5」 같은 수가 나오고, 그 수를 보는 사람은
#   **다섯 자리가 안 지켜지고 있다**고 읽는다. 실제로 그런 것은 셋이었다.
#
#   ⚠ 그렇다고 없애지 않는다 (P-12 ④). 대상이 0인 것과 게이트가 없는 것은 다르다 —
#     지우면 「안 해 본 것」과 「해 봤더니 볼 게 없던 것」이 같아진다 (D-301).
#     그래서 **자기 칸**을 준다. 종료 코드는 여전히 2다 — 재지 않은 것은 초록이 아니다.
waiting() { WAITING=$((WAITING+1)); printf '  %sWAIT%s  %s %s\n' "$YEL" "$RST" "$1" "${DIM}${2:-}${RST}"; }

# ★ [D-400] 종료 코드 **판정식은 여기 하나뿐이다.** 세 자리(단일 게이트·티켓 전체·
#   자기시험)가 각자 계산하면 반드시 어긋나고, 어긋난 판정식 복사본 하나가 D-212 였다.
#       0 = 쟀고 통과   1 = 쟀고 실패   2 = **못 쟀다**(판정 불가)
#   ★ 실패가 있으면 판정 불가가 함께 있어도 **1** 이다 — 실패가 「모른다」 뒤에 숨으면 안 된다.
summary_rc() {
  if [ "$FAILED" -ne 0 ]; then return 1; fi
  # 대기도 「재지 못한 것」이다 — 종료 코드에서는 회색과 같은 자리에 선다.
  # 둘이 갈리는 곳은 **집계 줄**이다: 무엇을 갚아야 하는지가 거기서 보여야 한다.
  if [ "$SKIPPED" -gt 0 ] || [ "$WAITING" -gt 0 ]; then return 2; fi
  return 0
}

# 집계 한 줄 — **총합만 적는 보고는 받지 않는다** (P-12).
tally() {
  printf '\n%s잼고 통과 %d · 잼고 실패 %d · 못 잼 %d (대기 %d)%s\n' \
    "$DIM" "$PASSED" "$FAILED" "$SKIPPED" "$WAITING" "$RST"
}
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

  # ★ [P-12 ② · 2026-09-17] 앞판은 `command -v gitleaks` 한 줄로 판단했고,
  #   스캐너가 없으면 **SKIP** 했다. 그 자리가 회색으로 남아 있던 다섯 중 하나다.
  #   이제 판정기가 따로 산다 — 스캐너를 어디서 찾는지(lock 이 고정한 `tools/`),
  #   무엇을 스캔 면으로 볼 것인지(저장소가 나르는 것 vs 디스크에 있는 것),
  #   심어 보고 잡는지(양성 1 · 음성 2)를 전부 그 파일이 말한다.
  local sout srrc
  sout=$($PY scripts/verify_secret_scan.py 2>&1); srrc=$?
  echo "$sout" | sed 's/^/        /'
  case $srrc in
    0) pass "시크릿 스캔 — 저장소가 나르는 자리 0건 · 이력 0건 (래칫 D-311)" ;;
    2) skip "시크릿 스캐너 미설치" "(python scripts/install_secret_scanner.py · 판·해시 고정 D-387)" ;;
    *) fail "시크릿 검출 — 저장소가 나르는 자리 또는 이력에 있다"; found=1 ;;
  esac
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
  # ★ [P-12 ③ · 2026-09-17] 여기는 **못 잰 자리가 아니었다.**
  #   게이트는 목록을 읽었고, 프레임워크 모델이 몇 개 남았는지 **알고 있었다.**
  #   그런데 SKIP 을 냈고, SKIP 은 「판정 불가」로 집계된다(D-400). 그래서 이 자리가
  #   회색 다섯 중 하나로 셈해졌다 — **아는 것을 모른다고 적은 것**이다.
  #   아는 빚에는 회색이 아니라 **래칫**이 맞다(D-311): 기존분은 세어 고정하고,
  #   하나라도 늘면 빨개진다. 그래야 「언젠가 없앤다」가 「오늘 안 늘었다」로 바뀐다.
  #   ⚠ 이 줄을 늘리려면 기준선을 함께 고쳐야 한다 — 그 수정이 곧 결재 요청이다.
  local FW_BASELINE="coreuser,group,multilanguagecontent,role,userprofile,userprofilelink,usergroup"
  if [ -n "$fw" ]; then
    local fw_sorted fw_n base_n
    fw_sorted=$(printf '%s' "$fw" | tr ',' '
' | tr 'A-Z' 'a-z' | sort | paste -sd, -)
    fw_n=$(printf '%s' "$fw_sorted" | tr ',' '
' | grep -c .)
    base_n=$(printf '%s' "$FW_BASELINE" | tr ',' '
' | grep -c .)
    local newcomers
    newcomers=$(comm -23 <(printf '%s' "$fw_sorted" | tr ',' '
' | sort -u)                          <(printf '%s' "$FW_BASELINE" | tr ',' '
' | sort -u) | paste -sd, -)
    if [ -n "$newcomers" ]; then
      fail "우회 목록에 **새 프레임워크 모델**이 들었다: $newcomers  ← 래칫 D-311"
      printf '        %s기준선 %d건에서 %d건으로 늘었다. 늘리려면 기준선을 함께 고친다%s
'         "$DIM" "$base_n" "$fw_n" "$RST"
      rc=1
    else
      pass "프레임워크 모델 잔존 ${fw_n}건 — 기준선 ${base_n}건 안 (새로 는 것 0건 · 래칫 D-311)"
      printf '        %s빚: %s — W0-2 작업2(뷰 레벨 필터). 대장: DA-05/blockers.yaml :: BYPASS_FRAMEWORK_MODELS%s
'         "$DIM" "$fw_sorted" "$RST"
    fi
  else
    pass "프레임워크 모델 잔존 0건 — 빚을 다 갚았다 (기준선을 0 으로 내릴 수 있다)"
  fi
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
  # ★ [P-12 ③④] 「못 잼」이 아니라 **대기**다 — 이 게이트는 멀쩡히 서 있고,
  #   이번 변경에 지나갈 것이 없었을 뿐이다. 자격증명이 없어 못 잰 것과 같은 칸에 두면
  #   갚아야 할 빚의 수가 부풀어 보인다. 없애지는 않는다: 대상 0과 게이트 부재는 다르다.
  [ "$nchanged" -eq 0 ] && { waiting "볼 대상 0건 — 대기" "(0건 사유는 위 [입력] 줄에 있다 · 빚이 아니다)"; return 0; }

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
  # ★ [P-12 ③④] 「못 잼」이 아니라 **대기**다 — 이 게이트는 멀쩡히 서 있고,
  #   이번 변경에 지나갈 것이 없었을 뿐이다. 자격증명이 없어 못 잰 것과 같은 칸에 두면
  #   갚아야 할 빚의 수가 부풀어 보인다. 없애지는 않는다: 대상 0과 게이트 부재는 다르다.
  [ "$nchanged" -eq 0 ] && { waiting "볼 대상 0건 — 대기" "(0건 사유는 위 [입력] 줄에 있다 · 빚이 아니다)"; return 0; }

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
  # ★ [P-12 ③④] 「못 잼」이 아니라 **대기**다 — 이 게이트는 멀쩡히 서 있고,
  #   이번 변경에 지나갈 것이 없었을 뿐이다. 자격증명이 없어 못 잰 것과 같은 칸에 두면
  #   갚아야 할 빚의 수가 부풀어 보인다. 없애지는 않는다: 대상 0과 게이트 부재는 다르다.
  [ "$nchanged" -eq 0 ] && { waiting "볼 대상 0건 — 대기" "(0건 사유는 위 [입력] 줄에 있다 · 빚이 아니다)"; return 0; }

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

# ─────────────────────────────────────────────────────────────────────────────
# GATE dormant — **「만들어진 것」과 「켜진 것」은 다르다** (D-377 · 착시 ⑨)
#
# 앞선 여덟 착시는 전부 "무엇을 세는가"의 문제였다. 아홉째는 한 단계 위다:
# **코드가 있으면 동작한다고 읽는 것.** 시험은 함수를 직접 불러 통과시키고,
# 운영은 그 함수를 부르지 않는다 — 둘 다 초록이다.
#
# 이 게이트는 오늘 자는 것을 이름으로 잠그고 **새로 자는 것만** 막는다(D-311 래칫).
# 즉 요구는 하나다: **새로 만드는 것은 「켜진 상태로 태어나야 한다.」**
#
# ★ 셋을 한 수로 합치지 않는다 — 고치는 방법이 다르다:
#     ㉠ 호출 없음 → 배선   ㉡ 주기 없음 → 등록   ㉢ 설정 빔 → 데이터
# ─────────────────────────────────────────────────────────────────────────────
gate_dormant() {
  head_ "GATE dormant — 잠자는 기능 래칫 (D-377 착시 ⑨)"
  local out rc

  # ★ 판정 전에 판정기부터 (D-277 · D-350 · D-310).
  #
  #   ★ **출생 표본** — 이 게이트가 태어난 사례는 셋이고 셋 다 합성이 아니다:
  #     ① K3 프레임 · 모니터링 · 백업 — 「구현하라」고 지시받은 셋이 **전부 이미 있었고**
  #        없던 것은 배선과 주기였다. 그것이 착시 ⑨ 의 이름이 된 자리다.
  #     ② 이 판정기 자신이 ㉢ 을 **0건으로 잘못 냈다** — 설정이 거의 전부 `env(...)` 라
  #        기본값이 접히지 않았다. 그 0을 실측으로 읽었으면 착시를 잡으려던 도구가
  #        착시를 하나 더 만들었다. 그 사례가 `verify_dormant.py` 의 자기시험에
  #        `BIRTH_ENV_SETTING` 으로 박혀 있다.
  #     ③ beat 표에 줄이 있는데 그 태스크를 **아무도 import 하지 않던** 자리 —
  #        D-373 이 「켰다」고 보고한 감시·백업이 실제로 그랬다.
  #        `backend/tests/test_dormant_wiring.py` 가 그 갈래를 본다.
  if out=$($PY scripts/verify_dormant.py --self-test 2>&1); then
    pass "탐지기 자기시험 통과 (양성 5갈래 · 음성 5갈래)"
  else
    fail "탐지기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_dormant.py 2>&1); rc=$?

  # D-301 — 무엇을 몇 건 보았는지 밖으로 말한다. 세 술어의 **모수 합**을 낸다.
  local nscanned
  nscanned=$(echo "$out" | grep -o "모수 *[0-9]*" | tr -dc "0-9
" | awk '{t+=$1} END {print t+0}')
  inputs "${nscanned:-0}" "함수 정의·celery 태스크·분기에 쓰이는 설정 (세 술어의 모수 합)"     "판정기가 모수를 말하지 않았다 — 출력 형식이 바뀌었거나 아무것도 못 봤다" || return 1

  echo "$out" | grep -E "^\[DORMANT\] ㉠|^\[DORMANT\] ㉡|^\[DORMANT\] ㉢|^\[DORMANT\] 합계"     | sed 's/^/        /'
  if [ $rc -eq 0 ]; then
    pass "$(echo "$out" | tail -1)"
    return 0
  fi
  fail "새로 잠든 것이 있다 — **켜진 상태로 태어나야 한다**"
  echo "$out" | sed 's/^/        /'
  return 1
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: route-alive — 화면이 쓰는 라우트를 **실제 HTTP 로 때린다** (D-386)
#
# ★ 이 게이트의 존재 이유는 **단위 시험이 전부 초록이어도 독립적으로 빨개지는 것**이다.
#   ★ **출생 표본** (D-310): 화면을 처음 띄운 순간 `/api/dsm/events` 가 **500** 이었다
#     [실측 2026-09-12]. 그 세 값(GET · /api/dsm/events · 500)이
#     `verify_route_alive.py::BIRTH_SAMPLE` 에 박혀 있고 자기시험이 그것을 판정한다.
#   단위 530건이 전부 초록인 채로 그 라우트는 운영에서 죽어 있었다 — 단위는 함수를 부르고
#   브라우저는 라우트를 때린다. 그 사이(URL 배선·스키마 해석·권한·미들웨어)를 아무도 안 봤다.
#
# ⚠ 서버가 안 떠 있거나 자격증명이 없으면 **SKIP(판정 불가)** 이다. 통과가 아니다 —
#   때려 보지 못한 것을 초록으로 적는 것이 이 게이트가 막으려는 바로 그 병이다(D-301).
# ─────────────────────────────────────────────────────────────────────────────
gate_route_alive() {
  head_ "GATE route-alive — 화면이 쓰는 라우트가 살아 있나 (D-386)"
  # ★ **출생 표본** (D-310) — `verify_route_alive.py::BIRTH_SAMPLE` 에 그날의 세 값이
  #   박혀 있다: GET · /api/dsm/events · **500** [실측 2026-09-12].
  #   아래 자기시험이 그 표본을 판정하고, 판정이 어긋나면 이 게이트는 시작하지 않는다.
  local out rc
  if out=$($PY scripts/verify_route_alive.py --self-test 2>&1); then
    pass "탐지기 자기시험 통과 (판정 규칙 8종 + 자기표본 /api/dsm/events)"
  else
    fail "탐지기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_route_alive.py 2>&1); rc=$?
  local nroutes
  nroutes=$(echo "$out" | grep -m1 -o '\[입력\] [0-9]*건' | tr -dc '0-9')
  inputs "${nroutes:-0}" "화면이 실제로 부른 GET 라우트 (캡처가 기록한 것)"          "캡처를 아직 한 번도 안 돌렸다 — 때릴 목록이 없다" || return 1
  echo "$out" | grep -E "^\[ALIVE\] ✗" | sed 's/^/        /'
  case $rc in
    # ★ 판정문을 **이름으로** 집는다. `tail -1` 은 마지막 줄이 판정문이라고
    #   가정했는데, 컨테이너 위임이 붙자 그 가정이 깨져 **초록이 안내 문구를 말했다**
    #   [실측 2026-09-18]. 초록은 자기가 무엇을 쟀는지 말해야 한다(D-301).
    0) pass "$(echo "$out" | grep -m1 -E '^\[ALIVE\] 통과 —' || echo '[ALIVE] 통과 (판정문을 못 찾았다)')"
       echo "$out" | grep -m1 -E '^\[ALIVE\] 토큰 대조' | sed 's/^/        /'
       return 0 ;;
    2) skip "판정 불가 — 서버 미기동이거나 자격증명이 없다"             "(GX_ROUTE_USER/GX_ROUTE_PASSWORD · 통과가 아니다)"; return 0 ;;
    *) fail "죽은 라우트가 있다 — 화면이 부르는 자리가 응답하지 않는다"
       echo "$out" | sed 's/^/        /'; return 1 ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: contract-route-reach — 계약 진입면이 **HTTP 로 닿는가**  (D-410)
#
# ★ **세 번째 눈이다.** 두 눈의 사각이 정확히 겹친 자리를 본다:
#     · 단위/계약 시험(verify_contract_ac) → **서비스 함수**를 부른다. 배선을 안 본다
#     · route-alive                        → **화면이 부른 GET** 만 때린다. 쓰기 면을 안 본다
#   그 사이에서 `POST /api/dsm/settings/{api-keys,thresholds,zones,grade-rules}` 넷이
#   **405 (Allow: GET)** 인 채로 며칠을 살았다 [실측 2026-09-18]. 로직도 시험도 있었고
#   틀린 것은 「구현되었다」가 아니라 **「외부 App 이 쓸 수 있다」**는 함의였다.
#   U6 는 HTTP 로만 들어온다 — **함수는 문이 아니다**(착시 ⑨ 배선형).
# ─────────────────────────────────────────────────────────────────────────────
gate_contract_route_reach() {
  head_ "GATE contract-route-reach — 계약 진입면이 HTTP 로 닿나 (D-410)"
  local out rc
  if out=$($PY scripts/verify_contract_route_reach.py --self-test 2>&1); then
    pass "탐지기 자기시험 통과 (판정 규칙 14종 + 출생 표본 405 넷)"
  else
    fail "탐지기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_contract_route_reach.py 2>&1); rc=$?
  local nroutes
  nroutes=$(echo "$out" | grep -m1 -o '\[입력\] [0-9]*건' | tr -dc '0-9')
  inputs "${nroutes:-0}" "선언된 계약 진입면 (EVENT_ENTRY_SURFACE · method+path)"     "등재부를 못 읽었다 — 무엇을 두드릴지 모르는 채로 통과할 수 없다" || return 1
  echo "$out" | grep -E "^\[REACH\] X " | sed 's/^/        /'
  case $rc in
    0) pass "$(echo "$out" | grep -m1 -E '^\[REACH\] 계약 진입면 전부 도달' || echo '[REACH] 통과')"
       echo "$out" | grep -m1 -E '^\[REACH\] \[대조\]' | sed 's/^/        /'
       return 0 ;;
    # ★ 못 잼은 **통과가 아니다**(P-12). 씨앗이 없어 못 잰 자리는 회색으로 선다.
    2) skip "판정 불가 — 서버 미기동·자격증명 없음·씨앗 없는 자리"                "(통과가 아니다 · D-301)"; return 0 ;;
    *) fail "계약이 선언한 문 중 열리지 않는 것이 있다 — 함수가 있어도 U6 은 못 쓴다"
       echo "$out" | sed 's/^/        /'; return 1 ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: ui-secrets — **화면이 우리 서랍을 열어 보여 주는가** (P-27 · SEC-17)
#
# ★ **출생 표본** (D-310): 2026-09-25, `preset=system` 화면의 「연계 상태」 상자가
#   상대사명·계약번호·조항·미이행 사실을 관제요원 앞에 문단으로 그리고 있었다.
#   화면은 정상으로 보였다 — 오류도, 빈 칸도, 느림도 없었다. **잘 도는 화면이 새고 있었다.**
#   그래서 이 게이트는 V 의 **첫 판정기**다: 다른 것이 다 초록이어도 여기서 멈춘다.
#
# ⚠ 두 면 중 프런트만 본다(호스트에서 도는 갈래). API 응답 갈래는 서버가 필요하고,
#   그것은 컨테이너에서 `--api` 로 잰다 — **못 잰 것을 초록으로 세지 않는다.**
gate_ui_secrets() {
  # ★ **출생 표본** (D-310) — `verify_ui_secrets.py::BIRTH_SAMPLE` 에 그날 화면에
  #   실제로 떠 있던 문단의 첫 줄이 박혀 있다(상대사명 · 계약번호 · 조항).
  #   자기시험이 그 문자열을 못 잡으면 이 게이트는 시작하지 못한다.
  local out rc nfiles
  if out=$($PY scripts/verify_ui_secrets.py --self-test 2>&1); then
    pass "판정기 자기시험 통과 (양성 1 · 음성 3 — 주석은 잡지 않는다)"
  else
    fail "판정기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_ui_secrets.py --list 2>&1); rc=$?
  nfiles=$(echo "$out" | grep -o "\[입력\] [0-9]*개 프런트 파일" | tr -dc "0-9")
  inputs "${nfiles:-0}" "프런트 렌더 문자열 (주석 걷어낸 뒤 · 패턴 6종)"     "프런트 파일을 한 개도 못 읽었다 — 0건 검사와 검사 못 함은 다르다" || return 1

  if [ $rc -eq 0 ]; then
    pass "렌더 문자열에 상대사명·계약번호·조항·내부 경로 0건"
    return 0
  fi
  fail "화면이 우리 서랍을 열었다 — 사용자 본문은 사용자 언어로만"
  echo "$out" | sed 's/^/        /'
  return 1
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: ui-copy — **화면이 우리 대장의 말로 말하는가** (P-29 · UX-20)
#
# ★ 래칫이다(D-311). 오늘의 빚 18건은 이름으로 잠겨 있고, 이 게이트가 막는 것은
#   **새로 생기는 것**이다. 처음부터 exit 1 로 두면 사람이 게이트를 끄고,
#   꺼진 게이트는 없는 게이트보다 나쁘다.
gate_ui_copy() {
  # ★ **출생 표본** (D-310) — `verify_ui_copy.py::BIRTH_SAMPLES` 셋이 그날 화면의
  #   제목과 문단 그대로다: 「UX-17 …」 · 「`response_state=occurred` 로 걸러 준 …」 ·
  #   「data_source = live」. 셋 중 하나라도 못 잡으면 자기시험이 빨개진다.
  local out rc nfiles
  if out=$($PY scripts/verify_ui_copy.py --self-test 2>&1); then
    pass "판정기 자기시험 통과 (양성 3 — 그날 화면의 제목·문단 그대로)"
  else
    fail "판정기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_ui_copy.py 2>&1); rc=$?
  nfiles=$(echo "$out" | grep -o "\[입력\] [0-9]*개 화면 파일" | tr -dc "0-9")
  inputs "${nfiles:-0}" "화면 파일의 사용자 본문 (문자열 몸통·JSX 본문)"     "화면 파일을 한 개도 못 읽었다" || return 1

  echo "$out" | grep -E "^\[COPY\] 잔여" | sed 's/^/        /'
  case $rc in
    0) pass "$(echo "$out" | tail -1)"; return 0 ;;
    2) skip "기준선이 없다" "(python scripts/verify_ui_copy.py --freeze)"; return 0 ;;
    *) fail "새로 생긴 대장 언어가 있다 — 사전에 없는 문구는 만들지 않는다"
       echo "$out" | sed 's/^/        /'; return 1 ;;
  esac
}

_dispatch_gate() {
  case "$1" in
    secrets)            gate_secrets ;;
    ui-secrets)         gate_ui_secrets ;;
    ui-copy)            gate_ui_copy ;;
    bypass)             gate_bypass ;;
    isolation)          gate_isolation ;;
    model-inheritance)  gate_model_inheritance ;;
    deprecated-base)    gate_deprecated_base ;;
    ui-library)         gate_ui_library ;;
    forbidden-zone)     gate_forbidden_zone ;;
    dormant)            gate_dormant ;;
    route-alive)        gate_route_alive ;;
    contract-route-reach) gate_contract_route_reach ;;
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

# ★ ui-secrets 가 secrets 바로 뒤다 — **V 의 첫 판정기**(09-26 §6).
ALL_GATES=(secrets ui-secrets ui-copy bypass isolation model-inheritance deprecated-base ui-library forbidden-zone dormant route-alive contract-route-reach)

# ─────────────────────────────────────────────────────────────────────────────
usage() {
  sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 2
}

GATES_ONLY=0
case "${1:-}" in
  ""|-h|--help) usage ;;
  # ★ 출생 표본 (D-310 · D-400) — **이 도구가 틀렸던 그 사례**를 시험으로 박는다.
  #   2026-09-14 보고의 「게이트 9종 전부 exit 0」은 다섯 자리가 **아무것도 재지 않은 채**
  #   낸 초록이었다. 집계기가 SKIP(판정 불가)을 0 으로 셌기 때문이다.
  #   합성 예제만 보는 자기시험은 자기가 태어난 이유를 못 본다 — 그래서 실제 갈래 셋을 본다.
  --self-test)
    st_fail=0
    # ① 판정 불가 하나 → **2** 여야 한다 (이 도구가 틀렸던 바로 그 자리)
    PASSED=0; FAILED=0; SKIPPED=0; WAITING=0
    skip "자기시험 — 판정 불가 표본" "(출생 표본: route-alive 가 자격증명 없이 0 을 냈다)" >/dev/null
    summary_rc; st_rc=$?
    [ $st_rc -eq 2 ] || { echo "  자기시험 실패 ① 판정 불가가 $st_rc — 2 여야 한다"; st_fail=1; }
    # ② 전부 통과 → 0. 「판정 불가를 2 로」가 **모든 것을 2 로** 만들면 안 된다
    PASSED=0; FAILED=0; SKIPPED=0; WAITING=0
    pass "자기시험 — 통과 표본" >/dev/null
    summary_rc; st_rc=$?
    [ $st_rc -eq 0 ] || { echo "  자기시험 실패 ② 통과가 $st_rc — 0 이어야 한다"; st_fail=1; }
    # ③ 실패가 있으면 판정 불가가 함께 있어도 **1**. 실패가 「모른다」 뒤에 숨으면 안 된다
    PASSED=0; FAILED=0; SKIPPED=0; WAITING=0
    fail "자기시험 — 실패 표본" >/dev/null; skip "자기시험 — 함께 있는 판정 불가" "" >/dev/null
    summary_rc; st_rc=$?
    [ $st_rc -eq 1 ] || { echo "  자기시험 실패 ③ 실패+판정불가가 $st_rc — 1 이어야 한다"; st_fail=1; }
    if [ $st_fail -ne 0 ]; then
      echo "${RED}[GATES] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350)${RST}"; exit 1
    fi
    echo "[GATES] 자기시험 통과 — 종료 코드 세 갈래 (0 쟀고 통과 · 1 쟀고 실패 · 2 못 잼)"
    exit 0 ;;

  --list) printf '%s\n' "${ALL_GATES[@]}"; exit 0 ;;
  --gate)
    [ $# -ge 2 ] || usage
    run_gate "$2"; rc=$?
    tally
    # ★ [D-400 · 2026-09-16] **판정 불가는 통과가 아니다** — 그런데 종료 코드가 0 이었다.
    #   그 탓에 「게이트 9종 전부 exit 0」이라는 보고가 나갔고, 그때 route-alive 는
    #   자격증명이 없어 **아무것도 재지 않은 채** 0 을 내고 있었다.
    #   죽은 라우트 2건은 그대로였다 — **빨간 것을 재지 않고 낸 초록**이다 (P-10).
    #   이 저장소의 규약을 그대로 쓴다: `verify_migrations.py` 등이 이미 **exit 2 = 판정
    #   불가**를 쓴다. 집계기만 그것을 몰랐다. 이제 종료 코드가 스스로 말한다:
    #       0 = 쟀고 통과   1 = 쟀고 실패   2 = **못 쟀다**
    #   ★ 1(실패)로 하지 않는 이유: 서버 없는 환경에서 CI 를 빨갛게 만들면
    #     그 게이트는 결국 꺼진다(D-353). 꺼진 게이트는 아무것도 안 지킨다.
    #     「모른다」는 **자기 칸이 있어야 한다** — D-290 의 집계기 판이다.
    summary_rc; src=$?
    [ $rc -ne 0 ] && exit $rc
    exit $src ;;
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
summary_rc
case $? in
  2)
    # ★ [D-400] 못 잰 것이 있으면 **GATES PASS 라고 말하지 않는다** (P-10 · D-301).
    printf '  %sGATES UNDECIDABLE%s  통과 %d · **판정 불가 %d** — 못 잰 것을 통과로 세지 않는다
' "$YEL" "$RST" "$PASSED" "$SKIPPED"
    exit 2 ;;
  0)
    printf '  %sGATES PASS%s  잼고 통과 %d · 못 잼 %d (대기 %d) — DoD 재현 후 done 처리
' "$GRN" "$RST" "$PASSED" "$SKIPPED" "$WAITING"
    exit 0 ;;
  *)
    printf '  %sFAIL%s  잼고 통과 %d · 잼고 실패 %d · 못 잼 %d (대기 %d)
' "$RED" "$RST" "$PASSED" "$FAILED" "$SKIPPED" "$WAITING"
    printf '  %s3회 연속 실패 시 STOP(verify-failed)%s
' "$DIM" "$RST"
    exit 1 ;;
esac
