#!/usr/bin/env bash
# P-107 — **게이트의 종료 코드는 파이프에서 살아남아야 한다** (2026-09-07 · 턴 M · 차선 Q).
#
# 무엇을 막는가 — 출생 표본
# --------------------------
# [실측 2026-09-07 · 턴 L · docs/agent/evidence/TURN-L/coordinator_20260907.md:48]
#
#     python scripts/X.py 2>&1 | tail -18; echo "[exit=$?]"
#
#   `$?` 는 파이프의 **마지막 명령(`tail`)** 의 값이다. `tail` 은 언제나 0 이다.
#   그래서 **여덟 줄이 전부 `exit=0`** 으로 적혔다. `verify_readiness_scores` 는
#   스스로 「회색(exit 2)」이라고 말하고 있었는데, 그 줄은 초록이었다.
#   **여덟 줄이 무의미했다.**
#
# 어떻게 막는가 — 파이프를 아예 쓰지 않는다
# ------------------------------------------
#   `set -o pipefail` 한 줄로도 되지만, 그것은 **이 파일 안에서만** 산다. 다음 사람이
#   터미널에 손으로 치는 줄에는 붙지 않는다. 그래서 이 래퍼는 한 걸음 더 간다:
#   게이트 출력을 **파일에 받고**, 화면에는 그 파일을 잘라 보여 준다.
#   종료 코드는 **게이트를 직접 부른 자리**에서 잡는다 — 잘라 보여 주는 일과
#   판정을 읽는 일이 서로 다른 자리에서 일어난다.
#
#   ./scripts/gate_run.sh python scripts/verify_screens.py
#   ./scripts/gate_run.sh --tail 30 -- python scripts/verify_prod_settings.py
#   ./scripts/gate_run.sh --full -- python scripts/verify_write_auth.py
#
# 종료 코드: **게이트의 것을 그대로 돌려준다** (0 초록 · 1 빨강 · 2 회색).
#            래퍼 자신의 사용법 오류만 64 다 — 게이트의 코드와 섞이지 않게.
set -uo pipefail
export PYTHONIOENCODING=utf-8

TAIL=25
FULL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --tail) TAIL="${2:-25}"; shift 2 ;;
    --tail=*) TAIL="${1#--tail=}"; shift ;;
    --full) FULL=1; shift ;;
    --) shift; break ;;
    -h|--help)
      sed -n '2,28p' "$0"; exit 0 ;;
    *) break ;;
  esac
done

if [ $# -eq 0 ]; then
  echo "[GATE-RUN] 무엇을 돌릴지 안 주었다 — 사용법: ./scripts/gate_run.sh [--tail N|--full] -- <명령…>" >&2
  exit 64
fi

LOG="$(mktemp -t gxgate.XXXXXX)"
trap 'rm -f "$LOG"' EXIT

# ★ 여기서 파이프를 쓰지 않는다. 파이프가 없으면 `$?` 가 거짓말할 자리도 없다.
"$@" >"$LOG" 2>&1
RC=$?

if [ "$FULL" -eq 1 ]; then
  cat "$LOG"
else
  LINES=$(wc -l < "$LOG")
  if [ "$LINES" -gt "$TAIL" ]; then
    printf '[GATE-RUN] … 앞 %d줄 생략 (--full 로 전문) …\n' "$((LINES - TAIL))"
  fi
  tail -n "$TAIL" "$LOG"
fi

# ★ 머리글(P-107)이 없으면 **회색**이다 — 통과로 세지 않는다.
#   무엇을 쟀는지 말하지 않은 게이트의 초록은 초록이 아니다.
HDR=$(grep -c 'TARGET=' "$LOG")
if [ "$HDR" -eq 0 ]; then
  printf '[GATE-RUN] ⚠ 머리글(TARGET=/AS=/SOURCE=)이 없다 — 이 게이트는 **회색**으로 센다 (P-107)\n'
fi

printf '[GATE-RUN] exit=%d  ← **게이트가 낸 값이다** (파이프의 값이 아니다)  cmd: %s\n' "$RC" "$*"
exit "$RC"
