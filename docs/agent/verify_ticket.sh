#!/usr/bin/env bash
# GuardianX 티켓 검증 러너 — STEP 5 공통 게이트 자동화
# 사용: ./verify_ticket.sh W1-3
set -euo pipefail
TICKET="${1:?사용법: verify_ticket.sh <TICKET_ID>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0; FAIL=0
run() { echo "▶ $*"; if eval "$*"; then echo "  ✅ PASS"; PASS=$((PASS+1)); else echo "  ❌ FAIL"; FAIL=$((FAIL+1)); fi; }

echo "=== [$TICKET] 공통 게이트 ==="
run "cd $ROOT/frontend && npm run lint --silent"
run "cd $ROOT/frontend && npm run type-check"
run "cd $ROOT/backend && python manage.py makemigrations --check --dry-run"
run "cd $ROOT/backend && python manage.py test tests.test_tenant_isolation"

echo "=== [$TICKET] 티켓 게이트 ==="
python3 - "$TICKET" << 'PY'
import sys, yaml, subprocess, os
tid = sys.argv[1]
reg = os.path.join(os.path.dirname(__file__), 'tickets.yaml')
d = yaml.safe_load(open(reg, encoding='utf-8'))
t = next((x for x in d['tickets'] if x['id'] == tid), None)
if not t: sys.exit(f"티켓 {tid} 없음")
cmds = t.get('verify') or []
if not cmds: print("  (티켓 verify 명령 없음 — DoD 육안 확인 필요)")
for c in cmds:
    print(f"▶ {c}")
    r = subprocess.run(c, shell=True)
    print("  ✅ PASS" if r.returncode == 0 else "  ❌ FAIL")
print("\n=== DoD (사람이 재현할 것) ===")
print(t.get('dod',''))
print("\nhuman_gate:", t.get('human_gate'))
PY

echo
echo "공통 게이트 결과: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
