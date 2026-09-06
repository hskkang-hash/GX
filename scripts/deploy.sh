#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# scripts/deploy.sh — **배치는 절차가 아니라 명령이다** (세종 판정 P-64 · 2026-09-05 턴 F · 차선 Q)
#
# 무엇을 막는가 — **한 줄을 빠뜨린 절차가 하루를 삼켰다**
# ------------------------------------------------------------------------------
# 배치는 `docs/agent/RUNBOOK_로컬기동.md` STEP 2C 에 **손 절차**로 적혀 있었다.
# 그 절차의 ③(배치)을 한 번 빠뜨린 결과 **2026-09-04 07:17 자 낡은 번들이 하루 동안
# 서비스됐고**, 그 사이 찍힌 화면 증거 24장이 전부 낡은 번들의 증거였다.
# 손 절차는 빠뜨릴 수 있다. **명령은 빠뜨릴 수 없다.**
#
#   빌드 → 다이제스트 → 배치(원자적) → 번들 해시 게이트 → walk_scenarios 1회
#   → 하나라도 실패하면 **되돌리고 exit 1**
#
# ★ 이 스크립트가 지키는 불변 셋
#   ① **실패해도 이전 번들이 계속 서비스된다.** 새 번들은 `_fe_dist_new` 에 풀고,
#      **풀어 둔 채로 먼저 잰다.** 통과한 뒤에만 자리를 바꾼다. 자리를 바꾼 뒤에
#      빨강이 나면 `_fe_dist_prev` 를 도로 끼운다(되돌린 것을 **다시 재서** 보인다).
#   ② **판정기를 새로 짓지 않는다.** 번들 신원은 `scripts/verify_bundle_hash.py`(P-59),
#      걷기는 `scripts/walk_scenarios.py` 가 판정한다. 이 파일은 **순서와 되돌리기**만 안다.
#   ③ **회색은 초록이 아니다** (D-301). 못 잰 것은 0 으로 내지 않는다 — exit 2 다.
#
# ⚠ **`gx-fe-build` 의 `/app` 은 저장소를 물고 있지 않다 — 자기 사본이다.**
#   소스를 넣지 않고 빌드하면 그 `exit 0` 은 **직전 턴 코드**에 대한 것이다(P-59 거짓 초록).
#   그래서 이 스크립트는 **언제나 먼저 `docker cp` 로 소스를 넣는다.**
#
# 쓰는 법
#   scripts/deploy.sh                     빌드 → 배치 → 게이트 → 걷기
#   scripts/deploy.sh --no-walk           걷기를 건너뛴다(번들 해시 게이트까지만)
#   scripts/deploy.sh --strict-walk       걷기가 **회색이어도** 되돌린다
#   scripts/deploy.sh --skip-build        이미 빌드된 산출물로 배치만 다시 한다
#   scripts/deploy.sh --allow-dirty       프런트 작업본이 더러워도 진행(아래 ★)
#   scripts/deploy.sh --self-test         판정 규칙만 (도커 없이 · 되돌리기 결정표 · 프로필 관문)
#   scripts/deploy.sh --profile prod --target staging   운영 프로필로 스테이징에 올린다
#
# ★ **프로필** (P-75 · SEC-18 · 2026-09-06 턴 H) — 기본은 `dev`/`local`, **지금 그대로**다.
#   `--profile dev|prod`  백엔드가 어느 설정으로 뜨는가 (`config.settings` / `config.settings_prod`)
#   `--target local|staging|production`  이 번들이 어디에 서는가. staging·production 은 **공개 URL** 이다.
#   규칙 셋:
#     ① 개발 프로필로 공개 URL 을 열려 하면 **배치 거부**한다. [실측 2026-09-06 턴 G]
#        아무 선언 없이 뜨는 `config.settings` 는 SECRET_KEY=자리표 · DEBUG=True ·
#        ALLOWED_HOSTS=[*] · 쿠키 둘 주석이다 — 여는 순간 트레이스백·Host 무제한·세션 위조.
#     ② prod 프로필이면 **어디에 서든** `verify_prod_settings.py` 5/5 를 먼저 잰다.
#        초록이 아니면 배치하지 않는다(회색도 아니다 — 회색은 exit 2).
#     ③ 로컬·개발 배치는 **막지 않는다.** 막으면 그것은 보안이 아니라 고장이다.
#   `GX_DEPLOY_PROFILE` · `GX_DEPLOY_TARGET` 환경변수로도 같은 값을 준다.
#   ⚠ **지금 이 명령은 목적지가 staging 이어도 원격에 밀지 않는다** — 스테이징 서버가
#     아직 없다(대표 승인 대기 · RESUME_NEXT §3). 목적지는 지금 「무엇을 허락하는가」를
#     정하는 값이고, 원격 배선은 서버가 서면 이 자리에 잇는다. 그때 이 관문은 이미 서 있다.
#
# ★ **작업본이 더러우면 번들이 거짓말을 한다.** 번들에는 `GX_COMMIT:<HEAD>` 가 박히는데
#   내용은 커밋되지 않은 코드다. 게이트는 그 둘을 구별할 수 없으므로 **여기서 막는다.**
#
# 종료 코드: 0 배치했고 다 초록 · 1 실패(되돌렸다 · **이전 번들이 선다**) · 2 못 쟀다(회색)
#
# 드릴 스위치(증거용): `GX_DEPLOY_FORCE_FAIL=gate|walk` 를 주면 그 자리에서 일부러
#   실패시킨다. **되돌리기가 실제로 도는지**를 재기 위한 것이다 — 함정 ③의 실측.
set -uo pipefail

EXIT_OK=0; EXIT_FAIL=1; EXIT_GRAY=2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── 이름들. **두 벌로 적지 않는다** — RUNBOOK 은 이 파일을 부를 뿐이다 ──────────
BUILDER="${GX_BUILDER_CONTAINER:-gx-fe-build}"     # 빌드 컨테이너(/app 은 사본)
SERVER="${GX_SERVE_CONTAINER:-gx-shell}"           # 3002 를 내주는 컨테이너
LIVE="${GX_LIVE_DIR:-/app/_fe_dist}"               # 서버가 내주는 자리
# ⚠ **자리 이름에 시각을 넣는다** [실측 2026-09-05 턴 F]. 고정 이름(`_fe_dist_new`)을
#   쓰다가 두 번째 실행이 `rm: cannot remove … Directory not empty` 로 죽었다 —
#   이 `/app` 은 **윈도 바인드 마운트**이고, 방금 쓴 폴더를 지우는 것이 늘 되지는 않는다.
#   지울 수 없는 자리를 **다시 쓰려 하지 않는다**: 새 이름을 쓰고, 치우는 것은 덤으로 한다.
NEW="${LIVE}_new_${WHEN2:-$(date +%H%M%S)}"        # 새 번들을 **먼저 푸는** 자리
PREV="${LIVE}_prev_${WHEN2:-$(date +%H%M%S)}"      # 직전 번들 — 되돌릴 때 쓴다
OUTDIR="${GX_BUILD_OUTDIR:-dist_deploy}"           # 빌드 컨테이너 안의 산출물 폴더
WEB="${GX_WEB:-http://localhost:3002}"             # 게이트가 물어볼 주소(컨테이너 안)
API="${GX_API_INTERNAL:-http://localhost:8000}"    # 걷기가 쓸 API
SPA_PORT="${GX_SPA_PORT:-3002}"
NODE_HEAP="${GX_NODE_HEAP:-6144}"                  # ⚠ 2GB 로는 OOM 으로 죽는다

WHEN="$(date +%Y%m%d_%H%M%S)"
EVID="$ROOT/docs/agent/evidence/P-64"
LOG="$EVID/deploy_${WHEN}.log"

DO_WALK=1; STRICT_WALK=0; SKIP_BUILD=0; ALLOW_DIRTY=0; SELF_TEST=0
# ── 프로필·목적지 (P-75 · SEC-18 · 2026-09-06 턴 H · 차선 S) ────────────────
#   프로필 = 백엔드가 어느 설정으로 뜨는가 (dev = `config.settings` · prod = `config.settings_prod`)
#   목적지 = 이 번들이 어디에 서는가 (local = 지금 이 기계 · staging/production = **공개 URL**)
#   기본은 **지금 도는 그대로**다 — dev/local. 매 턴 끝의 로컬 배치가 이 파일을 부른다.
PROFILE="${GX_DEPLOY_PROFILE:-dev}"
TARGET="${GX_DEPLOY_TARGET:-local}"
PENDING=""
for a in "$@"; do
  # `--profile prod` 와 `--profile=prod` 를 **둘 다** 받는다 — 지시서는 앞엣것으로 적혔고
  # 손으로 치는 사람은 뒤엣것을 친다. 형식 때문에 배치가 막히는 일은 없어야 한다.
  if [ -n "$PENDING" ]; then
    case "$PENDING" in profile) PROFILE="$a" ;; target) TARGET="$a" ;; esac
    PENDING=""; continue
  fi
  case "$a" in
    --profile) PENDING=profile ;;
    --target) PENDING=target ;;
    --no-walk) DO_WALK=0 ;;
    --strict-walk) STRICT_WALK=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    --allow-dirty) ALLOW_DIRTY=1 ;;
    --self-test) SELF_TEST=1 ;;
    --profile=*) PROFILE="${a#--profile=}" ;;
    --target=*) TARGET="${a#--target=}" ;;
    -h|--help) sed -n '3,52p' "$0"; exit 0 ;;
    *) echo "[DEPLOY] 모르는 인자: $a"; exit 2 ;;
  esac
done

say() { echo "[DEPLOY] $*"; }

# ═══════════════════════════════════════════════════════════════════════════
# 프로필 관문 — **순수 함수다** (P-75 · SEC-18 · 2026-09-06 턴 H · 차선 S)
# ═══════════════════════════════════════════════════════════════════════════
# 무엇을 막는가 — **개발 프로필로 공개 URL 을 여는 것**
# [실측 2026-09-06 · 턴 G] 아무 선언 없이 뜨는 `config.settings` 는
#   `SECRET_KEY="your-secret-key-here"` · `DEBUG=True` · `ALLOWED_HOSTS=["*"]` ·
#   쿠키 둘 주석이다. 그 프로필로 스테이징·운영을 열면 **여는 순간** 트레이스백 노출 ·
#   Host 무제한 · 저장소에 적힌 키로 세션 위조다. 배치는 그 자리를 지나간다 —
#   그러니 **배치가 막는다**.
#
# 입력: 프로필(dev|prod) · 목적지(local|staging|production)
# 출력: "간다:0" 그대로 진행 · "게이트먼저:0" `verify_prod_settings.py` 5/5 를 먼저 잰다
#       "거부:1" 배치하지 않는다 · "회색:2" **모르는 이름은 초록이 아니다**
#
# ★ 로컬·개발은 **지금 그대로 간다.** 이 관문이 매 턴 끝의 로컬 배치를 막으면
#   그것은 보안이 아니라 고장이다.
profile_gate() {
  local profile="$1" target="$2"
  case "$profile" in dev|prod) ;; *) echo "회색:2"; return ;; esac
  case "$target" in local|staging|production) ;; *) echo "회색:2"; return ;; esac
  # prod 프로필은 **어디에 서든** 게이트를 먼저 지난다. 프로필을 말만 바꾸고
  # 선언을 안 심은 채 뜨는 것이 정확히 우리가 막는 것이다.
  [ "$profile" = "prod" ] && { echo "게이트먼저:0"; return; }
  [ "$target" = "local" ] && { echo "간다:0"; return; }
  echo "거부:1"
}

# ═══════════════════════════════════════════════════════════════════════════
# 되돌리기 결정 — **순수 함수다** (D-277). 자기시험이 합성 입력을 먹인다
# ═══════════════════════════════════════════════════════════════════════════
# 입력: 어느 단계(stage) 에서 · 어떤 종료 코드(rc) 가 났나 · --strict-walk 인가
# 출력: "되돌린다:<이 명령의 종료 코드>" 또는 "둔다:<종료 코드>"
#
# ★ 판정의 뼈대 — **자리를 바꾸기 전 실패와 바꾼 뒤 실패는 다른 일이다.**
#   바꾸기 전(build·digest·predeploy)에 죽으면 **되돌릴 것이 없다** — 이전 번들은
#   애초에 건드려지지 않았고, 그래서 그대로 서 있다. 바꾼 뒤(webgate·walk)에
#   죽으면 **되돌려야** 이전 번들이 선다.
decide() {
  local stage="$1" rc="$2" strict="${3:-0}"
  case "$stage" in
    build|digest|predeploy)
      # 자리를 아직 안 바꿨다 — 되돌릴 것이 없다(이전 번들은 손대지 않았다)
      [ "$rc" = "0" ] && { echo "둔다:0"; return; }
      echo "안바꿨다:$rc"; return ;;
    webgate)
      # 번들 신원 게이트. **회색도 되돌린다** — 「서버가 새 번들을 낸다」를
      # 증명하지 못한 채 새 번들을 세워 두면 그 자리가 다음 P-59 다.
      [ "$rc" = "0" ] && { echo "둔다:0"; return; }
      echo "되돌린다:1"; return ;;
    walk)
      [ "$rc" = "0" ] && { echo "둔다:0"; return; }
      if [ "$rc" = "2" ]; then
        # 회색: 걷지 **못했다**(playwright·API·세션). 번들은 이미 신원이 증명됐다.
        # 기본은 **두고 exit 2** — 못 잰 것 때문에 좋은 번들을 내리면 그 자체가 사고다.
        # --strict-walk 는 그 판단을 뒤집는다(무인 배치용).
        [ "$strict" = "1" ] && { echo "되돌린다:1"; return; }
        echo "둔다:2"; return
      fi
      echo "되돌린다:1"; return ;;
  esac
  echo "둔다:2"
}

self_test() {
  local bad=() got
  chk() { # chk <기대> <stage> <rc> [strict]
    got="$(decide "$2" "$3" "${4:-0}")"
    [ "$got" = "$1" ] || bad+=("decide($2,$3,${4:-0}) = $got — 기대 $1: $5")
  }
  # ── ★ 출생 표본 (D-310) — 이 명령을 만들게 한 사고 ──────────────────────
  #   09-04 07:17 번들이 하루를 살았다. 그때 빠진 것은 **배치 한 걸음**이었고,
  #   빠졌다는 것을 아무도 몰랐다. 그래서 첫 표본은 「배치 뒤 게이트가 빨강이면
  #   반드시 되돌린다」이다 — 낡은 번들이 서 있는 것보다 **모르는 번들이 서 있는
  #   것이 나쁘다**.
  chk "되돌린다:1" webgate 1 0 "배치 뒤 번들 신원이 빨강인데 안 되돌린다"
  chk "되돌린다:1" webgate 2 0 "번들 신원을 **못 쟀는데** 새 번들을 세워 둔다 (D-301)"
  chk "둔다:0"     webgate 0 0 "신원이 초록인데 되돌린다"
  # ── 자리를 바꾸기 전 실패 — 되돌릴 것이 없다 ─────────────────────────────
  chk "안바꿨다:1" build     1 0 "빌드가 죽었는데 되돌리기를 부른다(바꾼 적이 없다)"
  chk "안바꿨다:2" predeploy 2 0 "배치 전 게이트 회색인데 자리를 바꾼 것으로 친다"
  chk "둔다:0"     build     0 0 "빌드 성공이 실패로 읽힌다"
  # ── 걷기 ────────────────────────────────────────────────────────────────
  chk "되돌린다:1" walk 1 0 "걷다가 막혔는데 새 번들을 세워 둔다"
  chk "둔다:2"     walk 2 0 "**못 걸었다**(회색)를 이유로 좋은 번들을 내린다"
  chk "되돌린다:1" walk 2 1 "--strict-walk 인데 회색을 두고 간다"
  chk "둔다:0"     walk 0 0 "걷기 통과가 실패로 읽힌다"
  # ── 회색은 초록이 아니다: 어떤 자리에서도 rc=2 가 0 으로 새지 않는다 ────
  for s in webgate walk build; do
    case "$(decide "$s" 2 0)" in *:0) bad+=("$s 에서 회색이 exit 0 으로 샌다");; esac
  done

  # ── 프로필 관문 (P-75 · SEC-18) ─────────────────────────────────────────
  pchk() { # pchk <기대> <프로필> <목적지> <사유>
    got="$(profile_gate "$2" "$3")"
    [ "$got" = "$1" ] || bad+=("profile_gate($2,$3) = $got — 기대 $1: $4")
  }
  # ★ **출생 표본** — 이 관문을 만들게 한 그날의 설정(2026-09-06 턴 G 실측):
  #   `SECRET_KEY="your-secret-key-here"` · `DEBUG=True` · `ALLOWED_HOSTS=["*"]` ·
  #   쿠키 둘 주석. **그 프로필로 공개 URL 을 여는 배치**가 첫 표본이다.
  pchk "거부:1" dev staging    "개발 프로필로 스테이징을 연다 — 트레이스백·Host 무제한·세션 위조"
  pchk "거부:1" dev production "개발 프로필로 운영을 연다"
  # ★ 지금 도는 로컬 배치는 **계속 돈다** — 이 줄이 빨개지면 턴이 못 닫힌다
  pchk "간다:0" dev local      "로컬·개발 배치가 막힌다(이 관문의 고장)"
  # prod 프로필은 어디에 서든 5/5 를 먼저 잰다 — 이름만 prod 인 것을 막는다
  pchk "게이트먼저:0" prod staging    "prod 프로필인데 판정기를 안 부른다"
  pchk "게이트먼저:0" prod production "prod 프로필인데 판정기를 안 부른다"
  pchk "게이트먼저:0" prod local      "로컬이라고 prod 프로필의 판정을 건너뛴다"
  # 모르는 이름은 **초록이 아니다** (D-301)
  pchk "회색:2" staging staging "프로필 자리에 목적지를 넣었는데 통과한다"
  pchk "회색:2" dev stg         "모르는 목적지 이름이 통과한다"
  pchk "회색:2" prod ''         "목적지가 비었는데 통과한다"

  if [ "${#bad[@]}" -gt 0 ]; then
    say "자기시험 실패 — 명령을 먼저 의심한다 (D-350):"
    printf '    %s\n' "${bad[@]}"
    return $EXIT_FAIL
  fi
  say "자기시험 통과 — 출생 표본 3(09-04 번들) · 배치 전 3 · 걷기 4 · 회색 누출 3"
  say "자기시험 통과 — 프로필 관문 9(출생 표본 2 = 개발 프로필로 공개 URL · 로컬 1 · prod 3 · 회색 3)"
  return $EXIT_OK
}

if [ "$SELF_TEST" = "1" ]; then self_test; exit $?; fi

mkdir -p "$EVID"
exec > >(tee -a "$LOG") 2>&1
say "═══ P-64 배치 명령 · $WHEN ═══"
self_test || exit $EXIT_FAIL

# ═══════════════════════════════════════════════════════════════════════════
# ⓪′ 프로필 관문 — **아무것도 짓기 전에** 먼저 답한다 (P-75 · SEC-18)
# ═══════════════════════════════════════════════════════════════════════════
say "[프로필] $PROFILE · [목적지] $TARGET  (기본은 dev/local — 지금 도는 그대로)"
GATE="$(profile_gate "$PROFILE" "$TARGET")"
case "$GATE" in
  거부:*)
    say "**배치 거부** — 개발 프로필($PROFILE)로 $TARGET 을 열지 않는다."
    # ⚠ 이 줄에 역따옴표를 쓰지 않는다 — 큰따옴표 안의 역따옴표는 **명령 치환**이라
    #   `config.settings: command not found` 가 배치 로그에 찍힌다 [실측 2026-09-06].
    say "  [실측 2026-09-06 · 턴 G] config.settings 는 아무 선언 없이 뜨면"
    say "    SECRET_KEY=자리표 · DEBUG=True · ALLOWED_HOSTS=[*] · 쿠키 둘 주석 이다."
    say "  여는 순간 트레이스백 노출 · Host 무제한 · **저장소에 적힌 키로 세션 위조**다."
    say "  → 운영 프로필로 다시 부른다: scripts/deploy.sh --profile prod --target $TARGET"
    say "    (선언 이름은 저장소 뿌리 .env.example 의 「운영 프로필 선언」 절)"
    exit $EXIT_FAIL ;;
  회색:*)
    say "**못 쟀다** — 모르는 프로필·목적지 이름이다(프로필=$PROFILE · 목적지=$TARGET)."
    say "  프로필 dev|prod · 목적지 local|staging|production. **모르는 이름은 초록이 아니다**"
    exit $EXIT_GRAY ;;
esac

# ═══════════════════════════════════════════════════════════════════════════
# ⓪ 먼저 신원을 정한다 — **커밋 40자리.** `--short` 는 부딪힐 수 있다
# ═══════════════════════════════════════════════════════════════════════════
COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null | tr -d '\r\n')"
if ! printf '%s' "$COMMIT" | grep -qE '^[0-9a-f]{40}$'; then
  say "**못 쟀다** — HEAD 를 40자리로 못 읽었다: '${COMMIT}'"; exit $EXIT_GRAY
fi
say "[커밋] $COMMIT"

# ⚠ 작업본 검사는 **빌드할 때만** 뜻이 있다. `--skip-build` 는 작업본을 입력으로
#   삼지 않는다 — 그때 이 검사를 걸면 「이 배치가 무엇을 배치하는가」와 무관한 이유로
#   멈춘다. 대신 그 경우에는 **무엇을 배치하는지 판정기가 말한다**(번들 신원 게이트).
DIRTY=""
[ "$SKIP_BUILD" = "0" ] && DIRTY="$(git -C "$ROOT" status --porcelain -- frontend 2>/dev/null | head -20)"
[ "$SKIP_BUILD" = "1" ] && say "⚠ --skip-build — **이 배치의 입력은 작업본이 아니라 이미 묶인 산출물**이다. 신원은 아래 게이트가 판정한다"
if [ -n "$DIRTY" ]; then
  if [ "$ALLOW_DIRTY" = "1" ]; then
    say "⚠ 프런트 작업본이 더럽다 — **번들에 박힐 $COMMIT 은 이 내용이 아니다**. --allow-dirty 로 진행:"
    printf '[DEPLOY]     %s\n' $DIRTY
  else
    say "**멈춘다** — 프런트 작업본이 더럽다. 번들에는 HEAD($COMMIT) 가 박히는데"
    say "  내용은 커밋되지 않은 코드다. 게이트는 그 둘을 구별하지 못하고, 그 구별 불가가"
    say "  P-59 사고의 모양이다. 커밋하거나 --allow-dirty 를 준다:"
    printf '[DEPLOY]     %s\n' $DIRTY
    exit $EXIT_FAIL
  fi
fi

for c in "$BUILDER" "$SERVER"; do
  docker inspect "$c" >/dev/null 2>&1 || { say "**못 쟀다** — 컨테이너 $c 가 없다"; exit $EXIT_GRAY; }
done

# ── prod 프로필이면 **여기서 5/5 를 잰다** (P-75 · SEC-18) ───────────────────
# ★ 판정기를 새로 짓지 않는다(이 파일의 불변 ②). `verify_prod_settings.py` 가
#   운영 프로필을 **실제로 아홉 번 띄워** 닫혀 있는지 판정한다. 이 파일은 순서만 안다.
# ⚠ 컨테이너 안에서 돈다 — 호스트에는 Django·dj-core 가 없다. 파이프를 쓰지 않는다
#   (`| tail` 은 앞 명령의 종료 코드를 덮는다).
if [ "$GATE" = "게이트먼저:0" ]; then
  say "[0/6] 운영 프로필 판정 — verify_prod_settings.py (선언이 빠지면 기동을 거부하는가)"
  PRODGATE_LOG="$EVID/prod_settings_${WHEN}.log"
  # 드릴 스위치(증거용) — `GX_PROD_GATE_BACKEND=<dir>` 를 주면 판정기가 그 자리의
  #   `config/` 를 본다. **이 관문이 빨강일 때 실제로 배치를 막는지**를 재기 위한 것이다
  #   (망가뜨린 사본을 컨테이너 `/tmp` 에 두고 겨눈다 — 저장소는 안 건드린다).
  PRODGATE_ARGS=""
  [ -n "${GX_PROD_GATE_BACKEND:-}" ] && PRODGATE_ARGS="--backend ${GX_PROD_GATE_BACKEND}" \
    && say "      ⚠ 드릴: 판정기가 ${GX_PROD_GATE_BACKEND} 를 본다 (증거용 · 평시에는 비어 있다)"
  MSYS_NO_PATHCONV=1 docker exec "$SERVER" python /repo/scripts/verify_prod_settings.py $PRODGATE_ARGS > "$PRODGATE_LOG" 2>&1
  rc=$?
  sed 's/^/[DEPLOY]     /' "$PRODGATE_LOG" | tail -12
  say "      판정 종료코드=$rc · 전문 → $PRODGATE_LOG"
  # 도커가 명령 자체를 못 돌린 것(125·126·127)은 **실패가 아니라 못 잰 것**이다
  case "$rc" in 125|126|127) rc=2 ;; esac
  if [ "$rc" = "2" ]; then
    say "**못 쟀다** — 운영 프로필을 못 띄웠다(회색). **회색은 통과가 아니다**(D-301)."
    say "  자리는 안 바꿨다 — 이전 번들이 그대로 선다"
    exit $EXIT_GRAY
  fi
  if [ "$rc" != "0" ]; then
    say "**배치 거부** — 운영 프로필이 5/5 가 아니다. **이 게이트 초록 없이 공개 URL 을 열지 않는다**"
    say "  자리는 안 바꿨다 — 이전 번들이 그대로 선다"
    exit $EXIT_FAIL
  fi
  say "      운영 프로필 5/5 — 선언이 서 있고, 빠지면 뜨지 않는다"
fi

# 자격증명은 저장소 밖에서 (D-204). 걷기에만 쓴다
if [ -f "$ROOT/.env.gates" ]; then set -a; . "$ROOT/.env.gates"; set +a; fi

# ═══════════════════════════════════════════════════════════════════════════
# ① 소스를 **넣는다** — 이 한 걸음이 빠지면 아래 exit 0 은 직전 턴 코드 것이다
# ═══════════════════════════════════════════════════════════════════════════
if [ "$SKIP_BUILD" = "0" ]; then
  say "[1/6] 소스 투입 → $BUILDER:/app  (⚠ /app 은 저장소가 아니라 사본이다)"
  # ⚠ `docker cp` 의 호스트 쪽은 **상대 경로**로 준다 — Git Bash 가 `/c/...` 를
  #   자기 마음대로 바꾸는 자리이고, 바뀐 경로는 도커가 못 읽는다(RUNBOOK STEP 2C 와 같은 형).
  cd "$ROOT" || exit $EXIT_GRAY
  MSYS_NO_PATHCONV=1 docker exec "$BUILDER" sh -c 'rm -rf /app/src && mkdir -p /app/src' \
    && docker cp frontend/src/. "$BUILDER:/app/src" \
    && docker cp frontend/vite.config.ts "$BUILDER:/app/vite.config.ts" \
    && docker cp frontend/index.html "$BUILDER:/app/index.html"
  rc=$?
  if [ -d "$ROOT/frontend/public" ]; then
    docker cp frontend/public/. "$BUILDER:/app/public" || rc=1
  fi
  if [ "$rc" != "0" ]; then say "**실패** — 소스를 못 넣었다. 자리는 안 바꿨다"; exit $EXIT_FAIL; fi
  # 의존성이 바뀌었는지는 **말해 준다** — 이 명령은 npm install 을 하지 않는다
  H_HOST="$(sha256sum "$ROOT/frontend/package.json" | cut -c1-12)"
  H_CONT="$(MSYS_NO_PATHCONV=1 docker exec "$BUILDER" sh -c 'sha256sum /app/package.json' | cut -c1-12)"
  [ "$H_HOST" = "$H_CONT" ] || say "⚠ package.json 이 다르다(host $H_HOST ≠ 컨테이너 $H_CONT) — 이 명령은 npm install 을 하지 않는다"

  # ═════════════════════════════════════════════════════════════════════════
  # ② 빌드 — **종료 코드를 파이프로 덮지 않는다**
  # ═════════════════════════════════════════════════════════════════════════
  say "[2/6] 빌드 (GX_COMMIT=$COMMIT · 힙 ${NODE_HEAP}MB · --outDir $OUTDIR)"
  BUILD_LOG="$EVID/build_${WHEN}.log"
  MSYS_NO_PATHCONV=1 docker exec \
    -e NODE_OPTIONS="--max-old-space-size=${NODE_HEAP}" \
    -e GX_COMMIT="$COMMIT" \
    "$BUILDER" sh -c "cd /app && npx vite build --outDir $OUTDIR --emptyOutDir" > "$BUILD_LOG" 2>&1
  rc=$?
  tail -6 "$BUILD_LOG" | sed 's/^/[DEPLOY]     /'
  say "      빌드 종료코드=$rc · 전문 → $BUILD_LOG"
  case "$(decide build $rc)" in
    안바꿨다:*) say "**실패** — 빌드가 죽었다. **자리를 안 바꿨으므로 이전 번들이 그대로 선다**"; exit $EXIT_FAIL ;;
  esac
else
  say "[1-2/6] --skip-build — 이미 있는 $BUILDER:/app/$OUTDIR 로 간다"
fi

# ═══════════════════════════════════════════════════════════════════════════
# ③ 다이제스트 — **무엇을 배치하는지 이름과 수로 적는다**
# ═══════════════════════════════════════════════════════════════════════════
say "[3/6] 다이제스트"
DIGEST_TXT="$(MSYS_NO_PATHCONV=1 docker exec "$BUILDER" sh -c \
  "cd /app/$OUTDIR 2>/dev/null && find . -type f | sort | xargs sha256sum | sha256sum && find . -type f | wc -l")"
rc=$?
if [ "$rc" != "0" ] || [ -z "$DIGEST_TXT" ]; then
  say "**못 쟀다** — 산출물을 못 읽었다(빈 빌드는 「빈 집합끼리 일치」로 초록이 난다). 자리는 안 바꿨다"
  exit $EXIT_GRAY
fi
DIGEST="$(printf '%s' "$DIGEST_TXT" | head -1 | cut -c1-16)"
NFILES="$(printf '%s' "$DIGEST_TXT" | tail -1 | tr -d ' \r')"
say "      다이제스트 $DIGEST · 파일 $NFILES 개"
if [ "${NFILES:-0}" -lt 5 ]; then
  say "**못 쟀다** — 산출물이 $NFILES 개뿐이다. 빈 산출물을 배치하지 않는다"; exit $EXIT_GRAY
fi

# ═══════════════════════════════════════════════════════════════════════════
# ④ 배치 — **새 자리에 먼저 풀고, 재고, 통과한 뒤에만 바꿔치기**
# ═══════════════════════════════════════════════════════════════════════════
say "[4/6] 새 자리에 푼다 → $SERVER:$NEW  (이 동안 $LIVE 는 계속 서비스된다)"
# 지난 실행이 남긴 자리는 **덤으로** 치운다 — 못 치워도 진행한다(이름이 겹치지 않는다)
MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c   "rm -rf ${LIVE}_new_* ${LIVE}_prev_* ${LIVE}_new ${LIVE}_prev 2>/dev/null; true" >/dev/null 2>&1
MSYS_NO_PATHCONV=1 docker exec "$BUILDER" sh -c "cd /app && tar cf - $OUTDIR" \
  | MSYS_NO_PATHCONV=1 docker exec -i "$SERVER" sh -c \
    "rm -rf $NEW && mkdir -p $NEW && tar xf - -C $NEW --strip-components=1"
rc=$?
[ "$rc" = "0" ] || { say "**실패** — 못 풀었다. 자리를 안 바꿨으므로 이전 번들이 선다"; exit $EXIT_FAIL; }

say "      배치 전 게이트 — 푼 번들이 $COMMIT 라고 말하는가 (P-59)"
MSYS_NO_PATHCONV=1 docker exec -e GX_COMMIT="$COMMIT" "$SERVER" \
  python /repo/scripts/verify_bundle_hash.py --dist "$NEW" --no-deploy-evidence
rc=$?
case "$(decide predeploy $rc)" in
  안바꿨다:*)
    say "**실패** — 푼 번들이 $COMMIT 를 말하지 않는다(빌드가 낡은 사본을 묶었다)."
    say "  **자리를 안 바꿨다 — 이전 번들이 그대로 선다.** 이것이 09-04 사고를 막는 자리다"
    MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c "rm -rf $NEW"
    exit $EXIT_FAIL ;;
esac

# ── 바꿔치기. **여기서부터는 되돌릴 것이 생긴다** ───────────────────────────
# ★★ **이 `/app` 은 윈도 바인드 마운트다 — 폴더 이름 바꾸기가 늘 되지 않는다.**
#   [실측 2026-09-05 턴 F] `mv $PREV $LIVE` 가 오류 없이 **빈 폴더**를 남겼고, 그 순간
#   3002 가 404 를 냈다. 되돌리기가 되돌리지 못한 것이다 —
#   **되돌릴 수 없는 배치는 배치가 아니다.** 그래서 셋을 바꿨다:
#     ㉠ 직전 번들은 **옮기지 않고 복사로** 떠 둔다(못 뜨면 배치하지 않는다)
#     ㉡ 바꿔치기 뒤 **`index.html` 이 실재하는지 본다** — 이름 바꾸기의 종료 코드를 믿지 않는다
#     ㉢ 깨져 있으면 **복사로 고친다**: 새 번들에서, 그것도 안 되면 직전 번들에서
live_ok() {
  MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c "[ -f $LIVE/index.html ]" >/dev/null 2>&1
}
restore_from() {   # $1 자리의 내용을 **복사로** $LIVE 에 앉힌다
  MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c     "mkdir -p $LIVE; rm -rf $LIVE/* 2>/dev/null; cp -a $1/. $LIVE/ 2>/dev/null; [ -f $LIVE/index.html ]"     >/dev/null 2>&1
}

say "      직전 번들을 **복사로** 떠 둔다 → $PREV"
MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c   "rm -rf $PREV 2>/dev/null; mkdir -p $PREV; if [ -f $LIVE/index.html ]; then cp -a $LIVE/. $PREV/ && [ -f $PREV/index.html ]; else echo '(직전 번들이 없다 — 첫 배치)'; fi"
if [ $? != 0 ]; then
  say "**실패** — 직전 번들을 못 떴다. **되돌릴 수 없는 배치는 하지 않는다** — 자리를 안 바꾼다"
  exit $EXIT_FAIL
fi

say "      바꿔치기: $NEW → $LIVE"
MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c "rm -rf $LIVE 2>/dev/null; mv $NEW $LIVE 2>/dev/null; true"
if ! live_ok; then
  say "      ⚠ 이름 바꾸기가 자리를 깨뜨렸다(바인드 마운트) — **복사로 고친다**"
  restore_from "$NEW" || restore_from "$PREV"     || { say "**실패** — 자리를 못 세웠다. 사람이 봐야 한다: $LIVE · $NEW · $PREV"; exit $EXIT_FAIL; }
fi
SWAPPED=1

rollback() {
  say "── 되돌린다 — $PREV → $LIVE (**복사로** — 이름 바꾸기는 이 마운트에서 못 믿는다)"
  restore_from "$PREV" || say "  ⚠ 직전 번들로 못 되돌렸다 — $PREV 를 사람이 본다"
  say "── 되돌린 것을 **다시 잰다** (선언이 아니라 적용을 본다 · D-301)"
  MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c \
    "grep -ho 'GX_COMMIT:[0-9a-f]\{40\}' $LIVE/assets/*.js 2>/dev/null | sort -u; ls $LIVE/index.html"
  ensure_spa
  MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c \
    "python - <<'PY'
import urllib.request
try:
    b=urllib.request.urlopen('$WEB/index.html',timeout=10).read()
    print('[DEPLOY]     되돌린 뒤 3002 응답 %d바이트 — **이전 번들이 서비스된다**'%len(b))
except Exception as e:
    print('[DEPLOY]     ⚠ 되돌린 뒤 3002 를 못 읽었다:',e)
PY"
}

# ═══════════════════════════════════════════════════════════════════════════
# ⑤ 번들 해시 게이트 — **서버가 내는 것**을 문다. dist 는 곁길이다
# ═══════════════════════════════════════════════════════════════════════════
ensure_spa() {
  # 3002 가 닫혀 있으면 SPA 정적 서버를 세운다. **열려 있으면 건드리지 않는다**
  MSYS_NO_PATHCONV=1 docker exec "$SERVER" python -c \
    "import socket,sys;s=socket.socket();s.settimeout(2);sys.exit(0 if s.connect_ex(('127.0.0.1',$SPA_PORT))==0 else 1)" \
    >/dev/null 2>&1 && return 0
  say "      SPA($SPA_PORT) 가 닫혀 있다 — 세운다"
  MSYS_NO_PATHCONV=1 docker exec -i "$SERVER" sh -c "cat > /tmp/gx_spa_server.py" <<'PY'
# SPA 정적 서버 — 알 수 없는 경로는 index.html 로 되돌린다(클라이언트 라우팅)
import os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
ROOT = os.environ.get("GX_LIVE_DIR", "/app/_fe_dist")
PORT = int(os.environ.get("GX_SPA_PORT", "3002"))
class H(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = super().translate_path(path)
        if not os.path.exists(p) and "." not in os.path.basename(p):
            return os.path.join(ROOT, "index.html")
        return p
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")   # 캐시가 장애를 덮는다
        super().end_headers()
os.chdir(ROOT)
ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
PY
  MSYS_NO_PATHCONV=1 docker exec -d -e GX_LIVE_DIR="$LIVE" -e GX_SPA_PORT="$SPA_PORT" \
    "$SERVER" python /tmp/gx_spa_server.py
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    MSYS_NO_PATHCONV=1 docker exec "$SERVER" python -c \
      "import socket,sys;s=socket.socket();s.settimeout(2);sys.exit(0 if s.connect_ex(('127.0.0.1',$SPA_PORT))==0 else 1)" \
      >/dev/null 2>&1 && { say "      SPA 섰다 ($WEB · ROOT=$LIVE)"; return 0; }
    sleep 1
  done
  say "      ⚠ SPA 가 안 섰다"
  return 1
}

# =========================================================================
# P-72 — **배치 증거를 먼저 쓰고, 게이트는 그것과 맞춘다** (2026-09-06 · 턴 G · 차선 S)
#
#   옛 규칙은 「서버 번들 == HEAD」였다. 그래서 배치를 마친 뒤 **보고서 한 장을
#   커밋하는 것만으로** 게이트가 빨개졌다 — 코드는 한 줄도 안 움직였는데.
#   그 빨강이 가리키는 사실은 「서버가 낡은 코드를 낸다」가 아니라 「문서가 하나
#   늘었다」였다. 사실과 색이 어긋나는 게이트는 곧 무시당한다(D-353).
#
#   이제 배치한 커밋을 `docs/agent/evidence/deploy/` 에 적고, 게이트는 둘을 함께 본다:
#     (1) 서버 번들 == **증거에 적힌 배치 커밋**
#     (2) HEAD - 배치 커밋 차이가 `docs/**` 뿐
#   증거는 **게이트가 돌기 전에** 쓴다 — 게이트가 물어야 할 것이 그 증거이기 때문이다.
#
# ⚠ **컨테이너에는 `.git` 이 없다** [실측 2026-09-06]. (2)는 저장소가 있는 여기(호스트)
#   에서 재서 `GX_DRIFT_JSON` 으로 넘긴다 — 사람이 기억할 절차를 만들지 않는다(D-286).
# =========================================================================
DEPLOY_EVID="$ROOT/docs/agent/evidence/deploy"
mkdir -p "$DEPLOY_EVID"
cat > "$DEPLOY_EVID/${WHEN}.json" <<JSONEOF
{
  "deploy_commit": "$COMMIT",
  "deployed_at": "$(date -Iseconds)",
  "deployed_by": "scripts/deploy.sh",
  "server": "$SERVER:$LIVE -> $WEB",
  "gate_evidence": "docs/agent/evidence/P-64/bundle_gate_${WHEN}.json",
  "deploy_log": "docs/agent/evidence/P-64/deploy_${WHEN}.log",
  "note": "P-72 — 무엇을 배치했는가의 정본. 번들 해시 게이트는 HEAD 가 아니라 이 커밋과 맞춘다."
}
JSONEOF
say "      배치 증거 -> docs/agent/evidence/deploy/${WHEN}.json (P-72)"
GX_DRIFT_JSON="$(python "$ROOT/scripts/verify_bundle_hash.py" --emit-drift --deploy-commit "$COMMIT" 2>/dev/null)"
export GX_DRIFT_JSON

say "[5/6] 번들 해시 게이트 — 서버가 내는 번들 == **배치 커밋**? (P-72)"
ensure_spa
if [ "${GX_DEPLOY_FORCE_FAIL:-}" = "gate" ]; then
  say "      ⚠ 드릴: GX_DEPLOY_FORCE_FAIL=gate — 게이트를 일부러 빨강으로 만든다"
  rc=1
else
  MSYS_NO_PATHCONV=1 docker exec -e GX_COMMIT="$COMMIT" -e GX_DRIFT_JSON "$SERVER" \
    python /repo/scripts/verify_bundle_hash.py --web "$WEB" \
    --deploy-evidence /docs/agent/evidence/deploy \
    --out "/docs/agent/evidence/P-64/bundle_gate_${WHEN}.json"
  rc=$?
fi
case "$(decide webgate $rc)" in
  되돌린다:*)
    say "**실패(exit $rc)** — 서버가 내는 번들이 **배치 커밋**이라고 말하지 못한다"
    rollback
    say "**exit 1 · 배치 취소** — 화면에서 본 것을 「병합된 코드」라고 부를 수 없다(P-59)"
    exit $EXIT_FAIL ;;
esac
say "      게이트 통과 — 3002 가 내는 번들 = 배치 커밋 $COMMIT (P-72)"

# ═══════════════════════════════════════════════════════════════════════════
# ⑥ walk_scenarios 1회 — **배치된 번들 위를 사람처럼 지나간다**
# ═══════════════════════════════════════════════════════════════════════════
if [ "$DO_WALK" = "0" ]; then
  say "[6/6] --no-walk — 걷지 않았다. **걷지 않은 것은 걸었는데 괜찮은 것과 다르다**"
  say "═══ exit 0 · 배치 완료(걷기 생략) · 로그 $LOG ═══"
  exit $EXIT_OK
fi

say "[6/6] walk_scenarios 1회 (390×844px · $WEB · API $API)"
if [ "${GX_DEPLOY_FORCE_FAIL:-}" = "walk" ]; then
  say "      ⚠ 드릴: GX_DEPLOY_FORCE_FAIL=walk — 걷기를 일부러 빨강으로 만든다"
  rc=1
else
  MSYS_NO_PATHCONV=1 docker exec \
    -e GX_ROUTE_USER="${GX_ROUTE_USER:-}" -e GX_ROUTE_PASSWORD="${GX_ROUTE_PASSWORD:-}" \
    "$SERVER" python /repo/scripts/walk_scenarios.py \
    --web "$WEB" --api "$API" \
    --json-out "/docs/agent/evidence/P-64/walk_${WHEN}.json"
  rc=$?
fi
case "$(decide walk $rc $STRICT_WALK)" in
  되돌린다:*)
    say "**실패(walk exit $rc)** — 배치된 번들 위에서 걸음이 막혔다"
    rollback
    say "**exit 1 · 배치 취소**"
    exit $EXIT_FAIL ;;
  둔다:2)
    say "**회색(exit 2)** — 걷지 **못했다**(playwright · API · 세션 중 하나)."
    say "  번들 신원은 초록이므로 되돌리지 않는다. **회색은 초록이 아니다**(D-301) —"
    say "  무인 배치에서 이것을 막으려면 --strict-walk 를 준다"
    say "═══ exit 2 · 배치는 섰고 걷기는 못 쟀다 · 로그 $LOG ═══"
    exit $EXIT_GRAY ;;
esac

# 성공했으므로 직전 번들은 더 필요 없다 — 치우는 것도 **덤**이다(못 치워도 성공은 성공)
MSYS_NO_PATHCONV=1 docker exec "$SERVER" sh -c "rm -rf $PREV 2>/dev/null; true" >/dev/null 2>&1
say "═══ exit 0 — 빌드·배치·번들 해시(= HEAD)·걷기 모두 초록 · 로그 $LOG ═══"
exit $EXIT_OK
