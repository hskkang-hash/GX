#!/usr/bin/env sh
# WO-GRDX-20261003-04 레인 B — QA 판 `guardianx-qa` 띄우기 (이 PC · 127.0.0.1:8510).
#
#   sh scripts/qa/qa_up.sh
#
# ① env 를 새로 짓거나 그대로 쓰고(운영 값 복사 0) 운영 컨테이너 값과 sha256 대조(같으면 멈춤 · M5)
# ② QA 화면 번들(../gx-spa-qa/index.html · VITE_QA_BUILD=true 로 지은 것)이 있는지 본다
# ③ compose up -d → qa-backend 가 migrate → qa_seed → gunicorn
# 끄기: docker compose -p guardianx-qa -f docker-compose.qa.yml down   (초기화는 down -v)
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"

python scripts/qa/qa_env.py --check-ops gx-gunicorn-e

SPA_DIR=${GX_QA_SPA_DIR:-../gx-spa-qa}
if [ ! -f "$SPA_DIR/index.html" ]; then
  echo "[qa_up] QA 화면 번들이 없다: $SPA_DIR/index.html — VITE_QA_BUILD=true 로 지어 그 자리에 둔다(ENV.md ③)"
  exit 2
fi

docker compose -p guardianx-qa -f docker-compose.qa.yml up -d
docker compose -p guardianx-qa -f docker-compose.qa.yml ps
echo "[qa_up] 뒷단은 migrate·시드 뒤에 선다(처음은 몇 분) — 확인: curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8510/qa/keys"
