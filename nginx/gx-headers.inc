# 보안 머리 **한 벌** — WO-GRDX-20261002-11 AC-1c (GRDX-FIRST-020)
# ★ nginx `add_header` 는 **상속이 끊긴다**: 한 location 이 제 `add_header` 를 하나라도 두면 위(server)의
#   `add_header` 는 그 location 에서 통째로 사라진다. 그래서 이 한 벌을 server 에 한 번, 그리고
#   제 `add_header`(예: `/assets/` 의 Cache-Control)를 두는 location 마다 `include` 한다 — 베끼지 않는다.
# `always` — 4xx/5xx(관문의 거절 포함)에도 붙는다. 생성물(`generated/gx-gate.conf`)은 `add_header` 가 0 이라
# server 수준 한 벌이 API 응답에도 그대로 닿는다(없다는 것을 시험이 지킨다).
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
