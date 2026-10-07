#!/usr/bin/env sh
# WO-GRDX-20261007-01 T1 레인 B — QA 화면 번들 짓기(VITE_QA_BUILD=true) → 키 모양 제거 → C:/GuardianX/gx-spa-qa
#
#   sh scripts/qa/qa_build.sh
#
# ① 빌드 통(gx-fe-build)의 /bq 에 저장소 소스만 깨끗이 넣는다(통의 /app/src 에는 옛 차선 파일이 섞일 수 있다)
# ② API 주소는 비워 같은 출처(P-286 · 통의 .env 에 localhost:8000 이 있다 — 안 덮으면 화면이 다른 출처를 부른다)
#    바깥 키는 전부 FAKE_ 로 덮어 짓는다(M5) · 힙 6GB(기본 2GB 는 OOM)
# ③ rj-core 안에 박힌 지도 키(인수 코드 · 고칠 수 없다 · FIRST-010 계열)는 **산출물에서만** 키 모양을 지운다
# ④ 산출물을 QA 앞문이 읽는 자리로 내보낸다 — 앞문은 다시 읽기 필요 없음(정적 파일)
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && (pwd -W 2>/dev/null || pwd))  # Git Bash: C:/… 모양(MSYS_NO_PATHCONV 아래 docker cp 가 /c/… 를 못 읽는다)
OUT=${GX_QA_SPA_DIR:-$ROOT/../gx-spa-qa}
export MSYS_NO_PATHCONV=1

docker exec gx-fe-build sh -c 'rm -rf /bq/src /bq/public /bq/index.html; mkdir -p /bq && cd /app && cp package.json vite.config.ts tsconfig*.json .env /bq/ && ln -sfn /app/node_modules /bq/node_modules'
docker cp "$ROOT/frontend/src" gx-fe-build:/bq/src
docker cp "$ROOT/frontend/public" gx-fe-build:/bq/public
docker cp "$ROOT/frontend/index.html" gx-fe-build:/bq/index.html

docker exec gx-fe-build sh -c 'cd /bq && VITE_QA_BUILD=true VITE_API_URL= VITE_API_URL_FE= VITE_STREAMING_WS= VITE_GCS_API_URL=/api/gcs VITE_KAKAO_API_KEY=FAKE_qa VITE_GOOGLE_MAPS_API_KEY=FAKE_qa VITE_TURN_URL=turn:turn.invalid VITE_TURN_USERNAME=FAKE_qa VITE_TURN_PASSWORD=FAKE_qa VITE_STREAMING_BASE_URL=http://streaming.invalid VITE_STREAMING_WEBRTC_URL=http://streaming.invalid VITE_AI_STREAM_WS_URL=ws://ai.invalid NODE_OPTIONS=--max-old-space-size=6144 npx vite build --outDir dist_qa --emptyOutDir > build_qa.log 2>&1' || { echo "[qa_build] 빌드 실패 — gx-fe-build:/bq/build_qa.log"; exit 1; }

docker exec gx-fe-build sh -c 'cd /bq/dist_qa && grep -rlE "AIza[0-9A-Za-z_-]{35}" . | xargs -r sed -i -E "s/AIza[0-9A-Za-z_-]{35}/FAKE_QA_GOOGLE_KEY_REMOVED_BY_QA_BUILD__/g"; echo "[qa_build] 키 모양 남음: $(grep -rlE "AIza[0-9A-Za-z_-]{35}" . | wc -l) · qa/as 파일: $(grep -rl "qa/as" . | wc -l)"'

mkdir -p "$OUT"
docker cp gx-fe-build:/bq/dist_qa/. "$OUT/"
echo "[qa_build] 내보냄: $OUT"
