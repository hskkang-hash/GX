# 프록시 지시어 **한 벌** — 위치마다 베끼지 않는다 (D-369).
# 두 벌로 적으면 반드시 어긋나고, 어긋난 뒤에는 어느 쪽이 정본인지 아무도 모른다.
proxy_pass http://gx_app;
# ★ 이 두 줄은 **한 벌이다** — `upstream ... keepalive` 를 쓰면서 하나라도 빼면
#   앞단이 502 를 낸다. [실측 2026-09-05 · 턴 C] 처음 세웠을 때 넣지 않았고,
#   3,600 요청 중 **6건이 502** 로 돌아왔다(예산 게이트가 그 자리를 빨강으로 잡았다).
#   HTTP/1.1 로 말하고 `Connection:` 을 비워야 뒷단이 연결을 끊지 않는다.
proxy_http_version 1.1;
proxy_set_header Connection "";
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_connect_timeout 10s;
proxy_read_timeout 120s;
proxy_send_timeout 120s;

# ★ 뒷단이 **일부러** 워커를 재활용한다 — `backend/gunicorn.conf.py` 의
#   `max_requests = 200` (메모리 누수 대비). 재활용하는 순간 그 워커에 실려 있던
#   연결은 끊기고, 앞단은 그것을 502 로 손님에게 전한다.
#   **앞단이 있는 이유가 바로 이것이다**: 뒷단의 정상적인 재활용을 손님이 보지 않게 한다.
#   [실측 2026-09-05 · 턴 C] keepalive 를 맞춘 뒤 502 는 6건 → 1건이 됐고,
#   남은 한 건이 이 재활용 창이다.
proxy_next_upstream error timeout http_502;
# ★ 2 는 모자랐다 [실측]: 두 번 다 같은 죽어 가는 워커의 낡은 연결에 걸리면 거기서
#   포기하고 502 가 나간다. 3 이면 그 창을 넘는다.
# ⚠ `non_idempotent` 는 **넣지 않는다.** 넣으면 POST 도 다시 보내고, 그것은 502 를
#   없애는 대신 **경보를 두 번 보내는** 결함으로 바꾸는 일이다. GET 만 다시 보낸다.
#   ★ [실측 2026-09-05 · 턴 D] 이제 그 「두 번」에 **수가 있다.** 같은 부하 네 벌
#     (14,888 요청)에서 앞단은 **재시도 113건 중 104건을 되살렸다**(손님은 200 을 봤다).
#     그 113건이 쓰기였다면 `non_idempotent` 를 켠 순간 **104건이 중복 전송**된다 —
#     0.7%, 즉 1,000건에 7건이다. 재난 경보에서 그것은 502 보다 나쁘다.
#     근거: `docs/agent/evidence/OPS-13a/README.md` §3 ④.
proxy_next_upstream_tries 3;
proxy_next_upstream_timeout 15s;
