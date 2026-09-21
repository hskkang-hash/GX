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
# env: — **판정 전에 환경을 먼저 잰다** (세종 판정 P-70 · 2026-09-06 · 턴 G)
#
# ★ 무엇을 막는가 — **게이트 여섯이 유령 파일 953개를 훑고 있었다**
#   [실측 2026-09-05 · docs/agent/evidence/P-55/window_20260905_2247.md]
#   `gx-shell` 의 `/repo/frontend` 가 마운트가 아니라 **사본**이었다. 그 사본에는
#   파일이 1,956개, 호스트 저장소에는 1,003개 — **953개가 유령**이었고 컨테이너
#   안에서 도는 게이트 여섯이 그것을 훑으며 색을 내고 있었다.
#   그때 나온 색은 제품의 색이 아니었다. **환경이 어긋난 것이 제품 결함처럼 보였다.**
#
#   그래서 모든 게이트는 **자기가 무엇을 딛고 서는지 먼저 말한다.**
#
#       env_require mount session     ← 이 환경이 없으면 잴 수 없다
#       env_none "사유"               ← 딛는 환경이 없다(호스트 저장소 파일만 본다)
#
#   환경이 빠지면 **회색(exit 2) + 사유 = 환경 이름**. 빨강과 절대 섞지 않는다 —
#   섞으면 「환경을 세우면 사라지는 빨강」이 쌓이고, 그런 빨강을 몇 번 본 사람은
#   게이트를 끈다(D-353). 꺼진 게이트는 아무것도 안 지킨다.
#
# ★ 재는 몸통은 **`scripts/gate_env.py` 한 곳**이다. 열두 게이트에 복붙하면 열두 벌이
#   서로 달라지고, 달라진 판정식 복사본 하나가 D-212 였다. 여기 있는 것은 부르는 줄뿐이다.
#
# 환경 이름 넷 (`scripts/gate_env.py`):
#   minio   MinIO 도달(컨테이너 · 9000 health) · smtp  SMTP 수신함(mailpit) 도달
#   mount   **마운트 일치**(호스트가 세는 파일 수 = 컨테이너가 보는 파일 수)
#   session 세션 점유자 — 동시 접속 1(UX-24 · §0.4)에서 **누가 잡고 있는가**
# ─────────────────────────────────────────────────────────────────────────────
GATE_ENV_MARK='[환경]'

# 차선 이름 다섯 중 **탐침 계정** — 차선마다 다른 사람이라야 세션 빼앗김이 없다.
#   `GX_LANE=s` → `gxprobe_s`. `.env.gates`(저장소 밖 · .gitignore)가 비밀번호를 준다.
export GX_LANE="${GX_LANE:-}"
if [ -z "${GX_PROBE_PASSWORD:-}" ] && [ -f "$REPO_ROOT/.env.gates" ]; then
  # ⚠ 값을 출력하지 않는다. 이름만 저장소에 남는다 (D-204).
  set -a; . "$REPO_ROOT/.env.gates" >/dev/null 2>&1 || true; set +a
fi

# env_require <환경 이름…> — 빠지면 **회색**을 내고 rc=2. 게이트는 `|| return 2`.
env_require() {
  local out rc miss
  out=$($PY "$REPO_ROOT/scripts/gate_env.py" --require "$@" --quiet 2>&1); rc=$?
  if [ $rc -eq 0 ]; then
    printf '  %s%s 딛는 환경: %s — 다 있다%s\n' "$DIM" "$GATE_ENV_MARK" "$*" "$RST"
    return 0
  fi
  printf '  %s%s 미비 — 딛는 환경: %s%s\n' "$DIM" "$GATE_ENV_MARK" "$*" "$RST"
  echo "$out" | sed 's/^/        /'
  miss=$(printf '%s' "$out" | sed -n 's/.*환경 미비: \([^*]*\)\*\*.*/\1/p' | head -1)
  # ★ 회색의 사유는 **환경 이름**이다. 「못 잼」이라고만 적으면 무엇을 세워야 하는지
  #   아무도 모르고, 모르는 빚은 갚히지 않는다 (P-12 ①).
  skip "환경 미비 — ${miss:-판정 불가}" "(환경의 사실이다 · 제품의 빨강이 아니다 · P-70)"
  return 2
}

# env_none <사유> — 딛는 환경이 없다고 **명시**한다. 적지 않은 것과 없는 것은 다르다.
env_none() {
  printf '  %s%s 딛는 환경 없음 — %s%s\n' "$DIM" "$GATE_ENV_MARK" "${1:-호스트 저장소 파일만 본다}" "$RST"
}

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
  env_none "호스트 저장소의 .env.example · 스캐너 · git 이력만 본다"
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
  env_require mount || return 2   # backend/common/base_model.py 를 읽는다
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
  env_require mount || return 2   # backend/tests 를 읽는다
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
  env_require mount || return 2   # backend/**/models.py 를 읽는다
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
  env_require mount || return 2   # frontend/src 를 읽는다 — 유령 953의 자리
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
  env_none "베이스라인 대비 git diff — 저장소 자체가 대상이다"
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

  # ★ [D-480 ㉡ · 2026-09-17 턴 T · 차선 U56] **반경 좁은 것 하나를 좁혔다.**
  #   종전은 `grep -qF "$f"` — 부분 문자열이라 `reuse_targets` 에 `backend/delivery/`(디렉터리
  #   한 줄)만 있어도 그 아래 **모든** 파일이 허용되고, `api.py` 한 글자가 `delivery/api.py`
  #   와 `orders/api.py` 를 함께 열었다. 이제는 **경로 전체가 한 낱말로** 있어야 한다
  #   (앞뒤가 경로 글자가 아닌 자리 · 디렉터리 이름으로는 못 연다).
  #   허용으로 지나간 건수는 **통과 줄에 같이 찍는다** — 「변경 0건」이 「허용 N건」을 덮지 않게.
  #   ㉠(베이스라인 없으면 SKIP·0) · ㉢(WO 산문 대조)은 이 줄이 손대지 않는다 — 넘김.
  local rc=0 allowed_n=0 f_re
  for f in $changed; do
    for p in "${FORBIDDEN_PATHS[@]}"; do
      case "$f" in
        *"$p"*)
          f_re=$(printf '%s' "$f" | sed 's/[][\.*^$/]/\\&/g')
          if [ -n "$allow" ] && printf '%s\n' "$allow" | grep -qE "(^|[^A-Za-z0-9_./-])${f_re}([^A-Za-z0-9_./-]|$)"; then
            skip "$f — 금지구역이나 티켓 reuse_targets 가 **경로 전체를** 지목 (허용)"
            allowed_n=$((allowed_n+1))
          else
            fail "$f — §0.4 금지구역 변경 ← STOP(blocked)"
            rc=1
          fi
          ;;
      esac
    done
  done
  [ $rc -eq 0 ] && pass "금지구역 변경 0건 (티켓 허용으로 지나간 것 ${allowed_n}건)"
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
  env_require mount || return 2   # backend 소스를 읽는다
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
# GATE: post-arg-style — 화면이 본문으로 보내는데 서버는 질의를 기다리는가 (2026-09-05 TC)
#
# ★ **출생 표본 셋** — 그날 실제로 422 를 내던 자리들이다:
#   카메라 일괄 등록 · 훈련 모드 · 「지금 처리할 것」의 처리 단계 넘기기.
#   셋 다 **화면은 멀쩡히 떠 있었다** — 캡처가 제목만 단언하므로 초록이 났다.
#   단추를 누르는 사람만 아는 고장이고, 그 사람이 첫 근무일의 관제요원이다.
gate_post_arg_style() {
  env_require mount || return 2   # frontend/src 를 읽는다 — 유령 953의 자리
  local out rc nposts
  if out=$($PY scripts/verify_post_arg_style.py --self-test 2>&1); then
    pass "판정기 자기시험 통과 (양성 6 · 음성 5 — 출생 표본 셋 포함)"
  else
    fail "판정기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_post_arg_style.py 2>&1); rc=$?
  nposts=$(echo "$out" | grep -o "POST [0-9]*건" | head -1 | tr -dc "0-9")
  inputs "${nposts:-0}" "dsm 진입면의 POST 라우트 (술어=Python AST · route.post 데코레이터)" \
         "POST 라우트를 한 건도 못 읽었다" || return 1

  echo "$out" | grep -E "^\[POSTARG\] (POST 인자 방식|\[입력\] 화면 면|잇지 못한)" | sed 's/^/        /'
  case $rc in
    0) pass "$(echo "$out" | tail -1)"; return 0 ;;
    2) fail "판정 불가 — 잴 것을 못 찾았다 (회색은 초록이 아니다)"
       echo "$out" | sed 's/^/        /'; return 1 ;;
    *) fail "본문/질의가 어긋난 자리가 있다 — 그 단추는 눌러도 422 다"
       echo "$out" | sed 's/^/        /'; return 1 ;;
  esac
}

gate_dormant() {
  env_require mount || return 2   # backend 설정·celery 표를 읽는다
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
# ★ P-82 (2026-09-06 · 턴 I) — **게이트가 때리는 서버가 지금 코드를 무는가.**
#   턴 H 에 게이트 12종이 이틀 동안 초록이었고, 그 초록은 이틀 전 코드에 대한 것이었다.
#   V 가 첫째로 부른다: 이 게이트가 회색이면 **아래 게이트들의 색은 어제의 색**이다.
gate_live_freshness() {
  head_ "GATE live-freshness — 대상 서버 · 기동 시각 · 커밋 (P-82)"
  # ★ **출생 표본** (D-310) — `verify_live_freshness.py::BIRTH_SAMPLE` 에 턴 H 의 그 사례가
  #   박혀 있다: 8000 이 문 프로세스가 **2026-09-05 14:41** 에 떴고 `backend/` 는 그 뒤
  #   여러 번 바뀌었으며 `GX_COMMIT` 은 없었다 → **회색**. 아래 자기시험이 그 표본을
  #   판정하고, 판정이 어긋나면 이 게이트는 시작하지 않는다.
  local out rc
  if out=$($PY scripts/verify_live_freshness.py --self-test 2>&1); then
    pass "탐지기 자기시험 통과 (판정 규칙 6종 · 빨강이 회색을 이긴다)"
  else
    fail "탐지기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_live_freshness.py 2>&1); rc=$?
  # 입력 = **때린 서버 1대**. 못 찾으면 0 이고, 그 0 의 사유는 판정문이 말한다.
  local n=1
  echo "$out" | grep -q '기동 모름' && n=0
  inputs "$n" "게이트가 때리는 서버 (GX_API)" "그 포트를 문 프로세스를 못 찾았다 — 서버가 안 떴다" || return 1
  echo "$out" | grep -m1 -E '^\[FRESH\] 대상 서버' | sed 's/^/        /'
  case $rc in
    0) pass "$(echo "$out" | grep -m1 -E '^\[FRESH\] 통과 —' || echo '[FRESH] 통과')" ;;
    1) fail "$(echo "$out" | grep -m1 -E '^\[FRESH\] \*\*빨강\*\*' || echo '[FRESH] 서버가 다른 커밋을 문다')" ;;
    *) skip "$(echo "$out" | grep -m1 -E '^\[FRESH\] \*\*판정 불가' || echo '[FRESH] 판정 불가')" "(회색은 초록이 아니다 · D-301)" ;;
  esac
  return $rc
}

gate_route_alive() {
  env_require mount session minio || return 2   # HTTP 로 때린다 · 컨테이너 위임 · 저장소
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
  env_require mount session || return 2   # HTTP 로 때린다 · 컨테이너 위임
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
# GATE: click-completes — **누른 뒤를 본다** (P-118 · 턴 O)
#
# ★ **출생 표본** (D-310): 2026-09-08, 제품의 핵심 동작 「실제로 판정」이 여러 턴 동안
#   **0.5 「구현」**으로 채점됐다. 근거는 「상세 화면에 판정 칸이 그려졌다」였다.
#   사람이 그것을 눌렀더니 — **네트워크 요청 0 · 확인창 0 · 토스트 0 · 오류 0**,
#   판정은 그대로 「미판정」이었다. `react 19` + `antd 5` 가 요구하는
#   `@ant-design/v5-patch-for-react-19` 가 **선언만 되고 import 되지 않아** 제품의
#   `Modal.confirm` 과 `message.*` 가 한 번도 뜬 적이 없었다.
#
#   왜 아무 게이트도 못 잡았나 — 그것이 이 게이트의 전부다:
#     `capture_screens.py` 는 **화면을 열어 찍는다.** 확인창은 **누른 뒤에** 뜬다.
#     그러므로 촬영 경로에 없었다. 이 저장소의 어떤 게이트도 **누른 뒤**를 보지 않았다.
#
#   그래서 이 게이트는 48행마다 네 칸을 본다: ① 누를 것 ② 기대 호출 ③ **새 GET 으로**
#   확인한 상태 변화 ④ 기대 화면 문구. 넷이 다 서야 초록이다.
#
# ⚠ 색을 섞지 않는다 — 누를 자리를 **못 찾았으면 회색**(못 쟀다)이고, 찾아서 눌렀는데
#   안 끝나면 **빨강**(안 된다)이다. 그 둘을 한 칸에 넣으면 이 도구가 태어난 사유가 지워진다.
# ⚠ 실측은 브라우저가 필요하다(gx-shell · Playwright). 게이트는 **커밋된 증거를 읽는다** —
#   게이트가 매번 브라우저를 띄우면 환경이 죽을 때 게이트가 **초록으로** 죽는다.
#   증거가 낡으면 판정기가 스스로 회색을 낸다(MAX_AGE_HOURS).
gate_click_completes() {
  env_none "판정은 저장소의 실측 증거를 읽는다 (실측은 python scripts/verify_click_completes.py --measure)"
  local out rc n
  # ★ [턴 X · 차선 Q] **분모를 손으로 적지 않는다.** 종전 문안은 「양성 38 · 식 자기수용 38」
  #   이라 적혀 있었는데 도구가 실제로 내는 수는 **34** 였다 — 흐름 표가 줄었는데 게이트의
  #   칭찬만 옛 수를 들고 있었다. 사람이 적은 수는 갈리고, 갈린 쪽이 조용히 이긴다.
  #   그래서 **도구가 낸 줄을 그대로 옮긴다**(O = 선 칸 · ⚠ = 도구가 제 입으로 단 단서).
  if out=$($PY scripts/verify_click_completes.py --self-test 2>&1); then
    pass "판정기 자기시험 통과 — 수는 도구가 말한다(아래)"
    echo "$out" | grep -E '^\[P-118\] (O|⚠)' | sed 's/^/        /'
  else
    fail "판정기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_click_completes.py 2>&1); rc=$?
  n=$(echo "$out" | grep -m1 -o '\[입력\] [0-9]*건' | tr -dc '0-9')
  inputs "${n:-0}" "온보딩 48행 — 누른 뒤 네 칸(누를 것·기대 호출·상태 변화·화면 문구)"   "48행 표를 못 읽었다" || return 1
  echo "$out" | grep -m1 -E '^\[P-118\] \*\*[0-9]+/48\*\*' | sed 's/^/        /'
  echo "$out" | grep -E '^\[P-118\] ★' | sed 's/^/        /'
  case $rc in
    0) pass "$(echo "$out" | grep -m1 -E '^\[P-118\] 48/48' || echo '[P-118] 48/48')"
       return 0 ;;
    2) skip "판정 불가 — 실측 증거가 없거나 낡았다"                    "(python scripts/verify_click_completes.py --measure · 통과가 아니다 · D-301)"; return 0 ;;
    *) fail "누른 뒤가 안 끝나는 자리가 있다 — **그려진 것으로 점수를 주지 않는다**"
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
  env_require mount || return 2   # frontend/src 를 읽는다 — 유령 953의 자리
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
  # ★★ [P-206 · 2026-09-20 · 턴 Y · 차선 Q] **2 를 빨강으로 읽지 않는다.**
  #   그 판정기는 면이 둘이다(프런트 정적 · 살아 있는 API). 여기서는 `--list` 로 부르므로
  #   **API 면을 안 잰다** — 판정기가 이제 그것을 회색(2)으로 말한다. 종전 이 갈래는
  #   비영을 전부 `fail` 로 읽어서 **「안 잰 면」이 「화면이 서랍을 열었다」로 적혔다.**
  #   그 빨강을 몇 번 본 사람은 게이트를 끈다(D-353). 색을 가른다 — 회색은 초록도 아니다.
  if [ $rc -eq 2 ]; then
    # ⚠ 겹따옴표 안의 역따옴표는 **명령으로 실행된다** — 처음 이 줄이 「--api: command not
    #   found」를 냈다(실측). 회색 사유를 적으려다 셸을 돌린 것이다. 역따옴표를 쓰지 않는다.
    skip "ui-secrets" "못 쟀다 (exit 2) — API 면을 안 때렸다. --api 를 주는 실행이 그 면을 잰다"
    echo "$out" | grep -E "판정 불가|못 잰 면" | sed 's/^/        /'
    return 2
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
  env_require mount || return 2   # frontend/src 를 읽는다 — 유령 953의 자리
  # ★ **출생 표본** (D-310) — `verify_ui_copy.py::BIRTH_SAMPLES` 셋이 그날 화면의
  #   제목과 문단 그대로다: 「UX-17 …」 · 「`response_state=occurred` 로 걸러 준 …」 ·
  #   「data_source = live」. 셋 중 하나라도 못 잡으면 자기시험이 빨개진다.
  #   ★ **출생 표본 ②** (P-77) — `BIRTH_JSX` 둘은 낡은 정규식 파서가 통째로 못 보던
  #   JSX 본문이다(보간이 낀 자리). 파서가 다시 눈이 멀면 여기서 빨개진다.
  local out rc nfiles
  if out=$($PY scripts/verify_ui_copy.py --self-test 2>&1); then
    pass "판정기 자기시험 통과 (양성 3 문구 + 2 JSX 파서 — 그날 화면 그대로)"
  else
    fail "판정기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_ui_copy.py 2>&1); rc=$?
  nfiles=$(echo "$out" | grep -o "\[입력\] [0-9]*개 화면 파일" | tr -dc "0-9")
  inputs "${nfiles:-0}" "화면 파일의 사용자 본문 (문자열 몸통·JSX 본문)"     "화면 파일을 한 개도 못 읽었다" || return 1

  # ★ [P-77 · 2026-09-06 · 턴 H] **첫 줄이 본 비율이다.** 커버리지를 모르는 게이트는
  #   판정한 것이 아니다 — 화면 글자의 42%를 못 보던 그날의 파서도 「잔여 0 · 통과」였다.
  echo "$out" | grep -E "^\[COPY\] (\*\*본 비율|잔여)" | sed 's/^/        /'
  case $rc in
    0) pass "$(echo "$out" | tail -1)"; return 0 ;;
    2) if echo "$out" | grep -q "본 비율.*기준.*아래"; then
         skip "본 비율이 기준 아래다 — 파서가 화면 글자의 일부를 못 본다" \
              "(못 본 자리에서 나온 「잔여 0」은 사실이 아니다 · P-77)"
       else
         skip "기준선이 없다" "(python scripts/verify_ui_copy.py --freeze)"
       fi
       return 0 ;;
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
    post-arg-style)     gate_post_arg_style ;;
    live-freshness)     gate_live_freshness ;;
    gate-header)        gate_gate_header ;;
    route-alive)        gate_route_alive ;;
    contract-route-reach) gate_contract_route_reach ;;
    click-completes)    gate_click_completes ;;
    bundle-api-base)    gate_bundle_api_base ;;
    evidence-roundtrip) gate_evidence_roundtrip ;;
    camera-secret-logs) gate_camera_secret_logs ;;
    admin-doors)        gate_admin_doors ;;
    test-writes-prod-zero) gate_test_writes_prod_zero ;;
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
  # ★ [P-70 · 2026-09-06] **환경이 빠져 회색이 된 게이트는 건수를 말할 수 없다.**
  #   잴 자리가 없어서 안 잰 것이지 「건수 없는 게이트」가 아니다. 그것을 빨강으로
  #   바꾸면 환경 결함이 다시 제품 결함의 색을 입는다 — 이 절이 없애려던 바로 그 자리다.
  if grep -qF "$GATE_ENV_MARK 미비" "$log"; then
    :
  elif ! grep -qF "$GATE_INPUTS_MARK" "$log"; then
    fail "게이트 '$1' 이 입력 건수를 말하지 않았다 ← D-301 (건수 없는 게이트는 게이트가 아니다)"
    rc=1
  fi
  rm -f "$log"
  return $rc
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: gate-header — **게이트가 자기가 무엇을 쟀는지 먼저 말한다** (P-107 · 턴 M)
#
# ★ 출생 표본 (D-310) — 턴 L 이 연 게이트 넷은 **넷 다 초록**이었고, 넷 다 제품이
#   아닌 것을 재고 있었다: 8월 라우트 사진(531 vs 살아 있는 705) · 손으로 적은 분모
#   30(살아 있는 쓰기 표면 377) · **역할 0 계정**으로 걸은 화면 걷기 · 호스트 **root**
#   자격으로 잰 저장소 200(앱의 자격은 5자 자리표이고 앱은 503).
#   넷의 공통점은 색이 아니다 — **무엇을 쟀는지 아무도 말하지 않았다.**
#
#   그래서 머리글 세 줄(TARGET/AS/SOURCE)이 없는 게이트는 **회색**이다. 통과가 아니다.
#   이 게이트는 세 줄이 **적혀 있는지**가 아니라 **찍히는지**를 본다 — 게이트를
#   실제로 연다(D-210).
# ─────────────────────────────────────────────────────────────────────────────
gate_gate_header() {
  head_ "GATE gate-header — 머리글 TARGET/AS/SOURCE · 파이프 exit (P-107)"
  local out rc n

  if out=$($PY scripts/verify_gate_header.py --self-test 2>&1); then
    pass "판정기 자기시험 통과 (양성 3 · 변이 3 · 출생 표본 4)"
  else
    fail "판정기 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_gate_header.py 2>&1); rc=$?

  # D-301 — 몇 개를 **실제로 열었는지** 말한다. 열지 못했으면 0건이고, 0건은 통과가 아니다.
  n=$(echo "$out" | grep -o '실제로 연 것 [0-9]*개' | grep -o '[0-9]*' | head -1)
  inputs "${n:-0}" "머리글을 받으려고 **실제로 연** 게이트 수"          "게이트를 하나도 못 열었다 — 판정이 아니라 열거기·파이썬 고장이다" || return 1

  # ★ [P-204 · 턴 Y · 차선 Q] `?` 를 빼지 않는다 — **회색 줄을 안 찍으면 회색이 안 보인다.**
  #   넷째 수(MEASURED_LINE)는 빨강이 아니라 회색을 내는데, 종전 그물은 `[OX]` 만 떠서
  #   그 줄이 출력에서 통째로 사라졌다. 안 보이는 회색은 초록처럼 읽힌다.
  echo "$out" | grep -E "^\[P-107\] 수|^  [OX?]  " | sed 's/^/        /'
  if [ $rc -eq 0 ]; then
    pass "$(echo "$out" | tail -1)"
    return 0
  fi
  if [ $rc -eq 2 ]; then
    skip "gate-header" "못 쟀다 (exit 2) — 회색은 통과가 아니다"
    return 2
  fi
  fail "머리글이 없거나 어긋난 게이트가 있다 — **무엇을 쟀는지 말하지 않은 초록은 초록이 아니다**"
  echo "$out" | sed 's/^/        /'
  return 1
}

# ★ ui-secrets 가 secrets 바로 뒤다 — **V 의 첫 판정기**(09-26 §6).

# -----------------------------------------------------------------------------
# GATE: bundle-api-base — **서는 번들 안에 API 주소가 박혀 있나**  (P-182 · 턴 V)
#
# * 출생 표본 [실측 2026-09-18 · 턴 U]: 조율자가 `gx-fe-build` 의 `/app/.env` 없이
#   프런트를 다시 지었다. `vite` 는 0, 번들 해시 게이트도 초록(그 게이트는 신원만
#   묻는다), 화면도 떴다. 그런데 `VITE_API_URL` 이 빈 문자열이 되어 로그인 POST 가
#   API 가 아니라 SPA 제 원점으로 갔고(501), V 의 측정이 40분 통째로 막혔다.
#   **아무것도 빨갛지 않았다** — 그 자리를 묻는 게이트가 없었다.
#
# 이 게이트는 덤으로 정적 서버가 `/api/...` 에 404 를 내는지도 문다(턴 U 에 V 가
# 찾은 거짓 초록의 씨 — 옛 서버는 200+index.html 을 돌려줬다).
#
# 기대 밑동을 모르면 **회색**이다. 모르는 채로 초록을 내지 않는다.
gate_bundle_api_base() {
  #: ⚠ `session` 을 딛지 **않는다** — 이 게이트는 로그인하지 않는다. 정적 파일을
  #:   익명으로 읽을 뿐이다. 처음엔 session 을 딛게 짰다가 남이 세션을 쥐고 있다는
  #:   이유로 회색이 났다 — **재지 못할 이유가 없는데 회색을 내는 게이트**는 곧 꺼진다.
  env_require mount || return 2   # 컨테이너 안에서 HTTP 로 SPA 를 문다
  head_ "GATE bundle-api-base — 서는 번들에 API 주소가 박혀 있나 (P-182)"
  # * **출생 표본** (D-310) — `verify_bundle_api_base.py::self_test` 의 `BIRTH_SAMPLE` 에
  #   그날의 값이 박혀 있다: 턴 U 에 `/app/.env` 없이 지은 번들에서 실제로 뽑힌 주소
  #   리터럴 앞머리(`react.dev` · `bit.ly` … · `http://localhost:8000` 은 **없다**).
  #   아래 자기시험이 그 표본을 빨강으로 판정하지 못하면 이 게이트는 시작하지 않는다.
  local out rc
  if out=$($PY scripts/verify_bundle_api_base.py --self-test 2>&1); then
    pass "판정 자기시험 통과 (규칙 7종 + 뽑기 2종)"
  else
    fail "판정 자기시험 실패 - 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_bundle_api_base.py           --spa "${GX_WEB:-http://localhost:3002}"           --expect "${GX_EXPECT_API_BASE:-${GX_API_INTERNAL:-http://localhost:8000}}" 2>&1); rc=$?
  local nentry
  nentry=$(echo "$out" | grep -m1 -oE '엔트리 [0-9]+개 읽음' | tr -dc '0-9')
  inputs "${nentry:-0}" "서버가 HTTP 로 내준 엔트리 JS (파일이 아니라 응답을 읽었다)"          "SPA 가 답하지 않거나 index.html 에 모듈 스크립트가 없다 - 읽을 번들이 없었다" || return 1
  case $rc in
    0) pass "$(echo "$out" | grep -m1 -E '^\[BUNDLE-API\] 초록' || echo '[BUNDLE-API] 초록 (판정문을 못 찾았다)')"
       echo "$out" | grep -m1 -E '^\[BUNDLE-API\] SPA' | sed 's/^/        /'
       return 0 ;;
    2) skip "판정 불가 - SPA 가 안 서거나 기대 밑동을 모른다" "(통과가 아니다)"
       echo "$out" | grep -E '^\[BUNDLE-API\] 회색' | sed 's/^/        /'
       return 0 ;;
    *) fail "서는 번들에 API 주소가 안 박혔다 - 화면은 뜨지만 로그인이 API 로 가지 않는다"
       echo "$out" | sed 's/^/        /'; return 1 ;;
  esac
}

# -----------------------------------------------------------------------------
# GATE: evidence-roundtrip — **증거 JSON 을 다시 읽어도 같은 수가 나오나**  (P-189 · 턴 W)
#
# * 출생 표본 [실측 2026-09-19 · 턴 W · 차선 Q]: 살아 있는 FC 증거의 한글만 cp949
#   왕복으로 깨뜨려 **같은 판정기**에 먹였더니 29/48 이 **8/48** 이 됐다. 초록 21개가
#   빨강으로 내려앉는데 **예외는 하나도 나지 않았다** — 따옴표와 중괄호는 아스키라
#   JSON 은 그대로 파싱되고, 뭉개지는 것은 네 칸 중 ④ 화면 문구뿐이다.
#   그래서 판정기는 죽지 않고, 초록을 내고, **틀린 수를 말한다.**
#
# 「썼다」로는 이것이 안 잡힌다. 쓰는 쪽은 이미 깨진 글자를 성실하게 utf-8 로 적는다.
# 술어는 하나뿐이다 — **같은 파일을 다시 읽어 같은 수가 나오는가.**
#
# ⚠ 이 게이트는 신선도를 재지 않는다. 낡은 증거가 0 이 되는 것은 **「못 잼」이지
#   「0점」이 아니다**(그 규율은 각 판정기의 MAX_AGE_HOURS 가 진다).
gate_evidence_roundtrip() {
  head_ "GATE evidence-roundtrip — 증거를 다시 읽어도 같은 수인가 (P-189)"
  local out rc n
  if out=$($PY scripts/verify_evidence_roundtrip.py --self-test 2>&1); then
    pass "판정 자기시험 통과 (출생 표본 + 세 칸 규칙 10종)"
  else
    fail "판정 자기시험 실패 - 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_evidence_roundtrip.py 2>&1); rc=$?
  n=$(echo "$out" | grep -m1 -oE '증거 파일 [0-9]+개 읽음' | tr -dc '0-9')
  inputs "${n:-0}" "다시 읽어 다시 센 증거 JSON (파일 바이트를 읽었다)" \
         "읽을 증거가 하나도 없다 - 아직 아무도 재지 않았다는 뜻이고, 0건은 통과가 아니다" || return 1

  echo "$out" | grep -E '^  [OX?] ' | sed 's/^/        /'
  # ★ [턴 W · ㉣] **안 걸은 것과 열린 세션은 게이트 얼굴에 이름으로 뜬다.**
  #   행 목록에만 있으면 다음 사람이 그 빈자리를 초록으로 읽는다.
  echo "$out" | grep -E '^\[P-189\] \[(안 걸음|세션)\]|^       [A-Z0-9]+ ' | sed 's/^/        /'
  case $rc in
    0) pass "$(echo "$out" | grep -m1 -E '^\[P-189\] 초록' || echo '[P-189] 초록')"
       return 0 ;;
    2) skip "evidence-roundtrip" "못 쟀다 (exit 2) - 회색은 통과가 아니다"
       echo "$out" | grep -E '^\[P-189\] 회색' | sed 's/^/        /'
       return 0 ;;
    *) fail "증거를 다시 읽으니 같은 수가 아니다 - **그 증거로 잰 수는 수가 아니다**"
       echo "$out" | sed 's/^/        /'; return 1 ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: camera-secret-logs — **카메라 자격이 로그에 적히는가** (P-200 · 턴 X · U3)
#
# ★ 출생 표본 — **막은 것이 한 턴 만에 돌아왔다.**
#   턴 W(P-192)에 `capture_service.py` 의 `print("rtsp_url: ", rtsp_url)` 과
#   `logger.info(f"… RTSP: {rtsp_url}")` 를 `_redact` 로 막았다. 그런데 **지키는
#   판정기를 안 세웠다.** 턴 X 에 열어 보니 옆 파일에서 같은 줄 **일곱 개**가
#   멀쩡히 살아 있었다 [실측 2026-09-20 · `stream_monitor_services.py`]:
#
#       :651  logger.info(f"… RTSP URL: {rtsp_url}")        ← rtsp_url = m.ip_source
#       :688  logger.info(f"… body: {json.dumps(body_data)}") ← **한 겹 건너 샌다**
#       :744 · :1247(print) · :1254 · :1275 · :1286
#
#   `StreamMonitor.ip_source` 는 운영자가 손으로 적는 칸이고 그 꼴이 흔히
#   `rtsp://아이디:비밀번호@호스트:554/…` 다. 즉 **카메라 비밀번호가 접근 로그에 남는다.**
#   로그 줄은 지우지 않는 것이 규약이므로(D-004 회전) 애초에 안 적는 수밖에 없다.
#
# ★ 술어가 **둘**인 이유 — 로그는 회전으로 사라지고, 코드는 남는다.
#   ① `docker logs` 를 실제로 읽어 `rtsp://<무엇>:<무엇>@` 이 **몇 줄인가**를 센다.
#      (이 판의 로그는 전부 stdout 이다 — `settings.LOGGING` 의 root 핸들러가
#       `console` 하나뿐이고 파일 핸들러가 없다. 앞단 nginx 도 같이 본다.)
#      자르는 기준은 줄이 아니라 **시각**(`--since`)이다.
#   ② 파이썬 AST 로 `ip_source` 에서 흘러나온 값이 씻기지 않고 `logger.*`/`print`
#      에 닿는 줄을 찾는다. **이름으로 안 센다** — 죄가 있는 것은 `rtsp_url` 이라는
#      이름이 아니라 `ip_source` 라는 샘이다. 그래서 `backend/delivery/` 의
#      `print("stream_urls: ", stream_urls)` 는 안 걸린다(금지구역 오탐 0).
#
# ★ **음성 대조를 했다 — 이 게이트는 빨개지는 것을 봤다** [2026-09-20 · 턴 X]:
#   · ② 코드: `capture_service.py:230` 의 `_redact(` 를 **한 번 벗겨** 심었더니
#     `빨강 · capture_service.py:229` · rc=1. 되돌린 뒤 원본과 **차이 0줄**.
#   · ① 로그: **가짜 자격**을 stdout 으로 뱉는 컨테이너를 띄워 `--container` 로
#     겨눴더니 세 줄 중 **한 줄**만 잡았다(씻긴 꼴·내부 주소는 안 잡음) · rc=1.
#     그 뒤 컨테이너를 지웠다. ⚠ 진짜 카메라 자격은 한 번도 안 썼다.
# ─────────────────────────────────────────────────────────────────────────────
gate_camera_secret_logs() {
  # ⚠ 「환경 없음」은 **자격증명·로그인이 없다**는 뜻이다. `docker` 실행 파일은 필요하고,
  #   없으면 로그 면이 **회색**이 된다(초록이 아니다 — rc=2 로 재 봤다).
  env_none "자격증명 0 · 서버 로그인 0 (읽기만) — 다만 **docker CLI** 가 없으면 로그 면은 회색"
  head_ "GATE camera-secret-logs — 카메라 자격이 로그에 적히는가 (P-200)"
  local out rc nlog npy

  if out=$($PY scripts/verify_camera_secret_logs.py --self-test 2>&1); then
    pass "판정 자기시험 통과 (출생 표본 9 + 로그 줄 표본 6)"
  else
    fail "판정 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_camera_secret_logs.py 2>&1); rc=$?
  npy=$(echo "$out" | grep -m1 -oE '파이썬 파일 [0-9]+개 훑음' | tr -dc '0-9')
  nlog=$(echo "$out" | grep -m1 -oE '로그 줄 [0-9]+개 훑음' | tr -dc '0-9')
  # ★ 두 면을 **따로** 센다. 한 수로 합치면 「로그를 못 읽었는데 코드가 많아서 초록」이
  #   가능해진다 — 그것이 D-301 이 금지한 바로 그 모양이다.
  inputs "${npy:-0}" "AST 로 훑은 backend 파이썬 파일" \
         "파이썬 파일을 한 개도 못 읽었다 — 정적 술어가 눈이 먼 것이지 0건이 아니다" || return 1
  inputs "${nlog:-0}" "실제로 읽은 살아 있는 로그 줄 (docker logs --since · 줄 아닌 시각으로 잘랐다)" \
         "로그를 한 줄도 못 읽었다 — 컨테이너가 안 떴거나 docker 가 없다. 「자격 0줄」이 아니다" || return 1

  echo "$out" | grep -E '^  [OX?] ' | sed 's/^/        /'
  # ★ rtsp 언급이 0줄이면 ①의 초록은 「지켜졌다」가 아니라 「지나간 것이 없다」이다.
  #   그 문장을 게이트 얼굴에 띄운다 — 행에만 있으면 다음 사람이 넓게 읽는다.
  echo "$out" | grep -E '⚠ rtsp 언급 자체가' | sed 's/^/        /'
  case $rc in
    0) pass "자격이 로그로 가는 줄 0 — 살아 있는 로그 · 코드 둘 다"
       return 0 ;;
    2) skip "camera-secret-logs" "한 면을 못 쟀다 — 회색은 통과가 아니다"
       echo "$out" | grep -E '^\[P-200\] 회색' | sed 's/^/        /'
       return 0 ;;
    *) fail "카메라 자격이 로그로 간다 — **막은 것이 돌아왔다**"
       echo "$out" | sed 's/^/        /'; return 1 ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: test-writes-prod-zero — **시험이 운영 감사표에 행을 남기는가** (P-202 · 턴 Y · S)
#
# ★ 출생 표본 — 이 게이트를 만든 것은 **차선 S 의 사고다** [실측 2026-09-20 · 턴 X]
#   시험 DB 다툼 가드의 첫 판이 「이 DB 에 누가 붙어 있나」를 **장고 연결로 물었다.**
#   묻는 행위 자체가 뒤의 `create_test_db` 를 바꿨고, 시험 셋이 운영 DB 에 붙어
#   운영 감사표에 `guardianx.test.law08_race` **219행**을 남겼다. 그 무리 안에서
#   증거 체인이 갈려 끊김 **#276795** 가 났다.
#
#   · 그 219행은 **지울 수 없다**(대표 결정 「끊김만 등재하고 행은 둔다」). 감사표에서
#     행을 지우는 것은 「안 고쳐졌다」의 증명 자체를 약하게 한다.
#   · 즉 비용이 **영구적**이다. 갚는 길은 「다시 안 나게 하는 것」뿐이고, 가드만 달고
#     지키는 판정기를 안 세우면 그 가드는 한 턴 만에 돌아온다 — 턴 W→X 의
#     `camera-secret-logs` 가 그 얼굴을 그대로 보여 줬다.
#
# ★ 분모는 **전량 시험 수**다. 시험 셋만 돌리고 낸 「새 행 0」은 0 이 아니다 —
#   그 0 은 「안 샜다」가 아니라 **「샐 자리를 안 지나갔다」**이다 (D-301).
#
# ⚠ 이 게이트는 **오래 걸린다**(전량 단위 시험을 실제로 돌린다 · 약 6분). 짧게 만들려면
#   분모를 줄이는 수밖에 없고, 분모를 줄이면 재는 것이 사라진다. 시간을 줄이는 대신
#   **재지 않는 쪽**을 고르면 그것이 바로 이 게이트가 태어난 이유가 된다.
#
# ⚠ 시험의 **빨강은 이 게이트의 색이 아니다.** 여기서 보는 수는 「운영 표에 행이
#   늘었나」 하나다 — 오히려 깨진 실행이 더 잘 샌다.
# ─────────────────────────────────────────────────────────────────────────────
gate_test_writes_prod_zero() {
  # ⚠ 「환경 없음」이 아니다 — **docker 와 gx-shell 이 필요하다.** 없으면 회색이다.
  env_none "자격증명 0 (읽기만) — 다만 **docker · gx-shell** 이 없으면 표 면은 회색"
  head_ "GATE test-writes-prod-zero — 시험이 운영 감사표에 쓰는가 (P-202)"
  local out rc ntests nwire

  if out=$($PY scripts/verify_test_writes_prod_zero.py --self-test 2>&1); then
    pass "판정 자기시험 통과 (출생 표본 219행 + 회색·분모 갈래)"
  else
    fail "판정 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_test_writes_prod_zero.py --db 2>&1); rc=$?
  nwire=$(echo "$out" | grep -m1 -oE '가드 배선 자리 [0-9]+곳' | tr -dc '0-9')
  ntests=$(echo "$out" | grep -m1 -oE '전량 단위 시험 [0-9]+건' | tr -dc '0-9')
  # ★ 두 수를 **따로** 센다. 합치면 「시험을 한 건도 안 돌렸는데 배선이 4곳이라 초록」이
  #   가능해진다 — D-301 이 금지한 바로 그 모양이다.
  inputs "${nwire:-0}" "가드 배선 자리 (정적으로 확인한 곳)" \
         "배선 자리를 하나도 못 읽었다 — 파일을 못 본 것이지 0곳이 아니다" || return 1
  inputs "${ntests:-0}" "**분모** — 실제로 돌린 전량 단위 시험 (샐 자리를 지나간 수)" \
         "시험을 한 건도 안 돌렸다 — 그 「새 행 0」은 「샐 자리를 안 지나갔다」이다" || return 1

  echo "$out" | grep -E '^\[P-202\] (①|②)' | sed 's/^/        /'
  # ★ 새다면 **어느 시험이 썼는지**(id·logger_name)까지 · 그 실행의 시험 빨강 이름도
  #   함께 띄운다. 후자는 이 게이트의 색이 아니지만, 안 적으면 다음 사람이
  #   이 초록을 「전량 초록」으로 읽는다.
  echo "$out" | grep -E '^    · ' | sed 's/^/        /'
  case $rc in
    0) pass "시험이 운영 감사표에 남긴 **새 행 0** (기준선 219행은 그대로 둔다)"
       return 0 ;;
    2) skip "test-writes-prod-zero" "못 쟀다 (exit 2) — 회색은 통과가 아니다"
       echo "$out" | grep -E '판정 불가|안 쟀다' | sed 's/^/        /'
       return 0 ;;
    *) fail "**시험이 운영 감사표에 썼다** — 그 행은 지울 수도 고칠 수도 없다 (P-191)"
       echo "$out" | sed 's/^/        /'; return 1 ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE: admin-doors — **파기·집행 문이 U4 에게 닫혀 있는가 · 겹이 둘인가** (P-208 U24 ②)
#
# ★ 이 게이트가 태어난 자리 — **실제로 있었던 사고**
#   턴 W 에 LAW-07′ 다섯 문을 U4 에게 열면서 문지기 `_admin` 을 **일괄 치환**했다.
#   그 한 번이 청구 면 다섯이 아니라 **파기·집행 문까지** U4 에게 열었다.
#
# ★★ 그리고 턴 X 에 그 사고를 재현하니 **더 나쁜 것**이 나왔다: 치환했는데
#   **POST 둘은 그대로 403** 이었다 — P-119 읽기 전용 관문이 앞에서 끊어 `_admin`
#   까지 가지도 않기 때문이다. 즉 **쓰기 문만 재는 시험은 이 사고를 못 잡고,
#   관문이 사고를 덮는다.** 그래서 겹을 갈라서 잰다:
#       ① GET 두 문으로 `_admin` 을 **직접** 잰다 (읽기는 관문이 안 본다)
#       ② 쓰기 둘은 관문을 **끄고**(`READONLY_ROLE_GATE_ENABLED=False`) 한 번 더 누른다
#
#   시험 파일은 지워질 수 있다. **게이트는 대장에 이름으로 남는다** — 그래서 이 게이트는
#   제품(문지기 배치)과 **시험의 겹**을 둘 다 보고, **따로 센다.**
# ─────────────────────────────────────────────────────────────────────────────
gate_admin_doors() {
  # 자격증명도 서버도 안 쓴다 — 저장소 파일 바이트만 읽는다. 그래서 회색이 날 자리가 없다.
  env_none "자격증명 0 · 서버 0 — law_api.py 와 두 겹 시험 파일을 AST 로 읽는다 (파일만 본다)"
  head_ "GATE admin-doors — 파기·집행 문지기 + 두 겹 시험 (P-208 U24 ②)"
  local out rc ndoor nbranch

  if out=$($PY scripts/verify_admin_doors.py --self-test 2>&1); then
    pass "판정 자기시험 통과 (출생 표본 5 · 양성 2)"
  else
    fail "판정 자기시험 실패 — 이 게이트는 눈이 멀었다"
    echo "$out" | sed 's/^/        /'
    return 1
  fi

  out=$($PY scripts/verify_admin_doors.py 2>&1); rc=$?
  ndoor=$(echo "$out"   | grep -m1 -oE '훑은 문 [0-9]+개'   | tr -dc '0-9')
  nbranch=$(echo "$out" | grep -m1 -oE '훑은 갈래 [0-9]+개' | tr -dc '0-9')
  # ★ 두 면을 **따로** 센다. 한 수로 합치면 「시험이 통째로 사라졌는데 제품이 멀쩡해서
  #   초록」이 가능해진다 — D-301 이 금지한 바로 그 모양이다.
  inputs "${ndoor:-0}" "AST 로 읽은 라우트 문 (_admin 4 + _privacy_officer 5)" \
         "제품 파일을 못 읽었다 — 정적 술어가 눈이 먼 것이지 0문이 아니다" || return 1
  inputs "${nbranch:-0}" "두 겹 시험에서 서 있어야 하는 갈래 (겹① 겹② 분모 넓힌쪽)" \
         "시험 파일을 못 읽었다 — 겹을 재는 것이 사라진 것이지 0갈래가 아니다" || return 1

  echo "$out" | grep -E '^    [OX] ' | sed 's/^/        /'
  case $rc in
    0) pass "파기·집행 문 넷은 _admin · 청구 면 다섯은 _privacy_officer · 두 겹 갈래 넷 서 있다"
       return 0 ;;
    *) fail "문지기가 옮겨 갔거나 겹 하나가 사라졌다 — **어느 문인지 이름으로** 아래에 있다"
       echo "$out" | grep -E '✗' | sed 's/^/        /'; return 1 ;;
  esac
}

ALL_GATES=(live-freshness gate-header secrets ui-secrets ui-copy post-arg-style bypass isolation model-inheritance deprecated-base ui-library forbidden-zone dormant route-alive contract-route-reach click-completes bundle-api-base evidence-roundtrip camera-secret-logs test-writes-prod-zero admin-doors)

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
