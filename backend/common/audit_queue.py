# -*- coding: utf-8 -*-
"""P-65 — **감사 기록이 큐에 갇혀 있는가** (2026-09-05 · 차선 F · 차선 E).

    [실측 턴 E] celery 워커가 0개이던 사흘 동안 감사 로그 쓰기
    (`core.logger.tasks.task_add_log`)가 **12,468건** 밀려 있었다.
    정본(`logger_auditlogs`)은 지워지지 않았다 — 그런데 **쓰이지도 않고 있었다.**

★ 왜 이것이 「감시 신호」인가
-----------------------------
이 저장소는 감사 로그를 「지워지는가」로만 지켜 왔다(OPS-07 ②). 그런데 감사에
답하지 못하는 길은 둘이다:

    ㉠ 있던 것이 **지워진다**      ← OPS-07 이 본다
    ㉡ 생긴 것이 **안 쓰인다**     ← 아무도 안 봤다. 여기다.

㉡이 더 조용하다. 표는 그대로 있고, 행 수도 줄지 않고, 화면도 멀쩡하다.
**없는 것은 안 보이기 때문에** 사흘이 지나도 아무도 모른다.

★ 큐 이름의 함정 — `LLEN default` 는 **언제나 0** 이다
------------------------------------------------------
이 저장소의 celery 는 우선순위 큐를 쓴다(`broker_transport_options.priority_steps
= 0..9` · `config/settings.py`). kombu 의 redis 전송은 우선순위마다 **다른 키**에
넣는다 — 이름 뒤에 `\x06\x16` + 우선순위 숫자가 붙는다:

    default            ← 우선순위 0 (접미 없음)
    default\x06\x161   ← 우선순위 1
    …
    default\x06\x169

그리고 이 저장소의 기본 우선순위는 **10**(`task_default_priority=10`)이라 kombu 가
9로 깎아 넣는다. 즉 **평범한 태스크는 `default` 에 하나도 안 들어간다.**
`LLEN default` 로 재면 12,468건이 밀려 있어도 **0** 이 나온다 — 그 0 을 초록으로
읽는 것이 이 신호가 막으려는 거짓말이다. 그래서 **접미가 붙은 이름을 전수로** 센다.

★ 「지연(초)」는 어떻게 재는가 — **실측 둘에서 나온 [추정] 하나**
----------------------------------------------------------------
celery 메시지에는 **넣은 시각이 없다**(프로토콜 v2 헤더에 그 칸이 없다 [실측]).
그러므로 「이 메시지가 얼마나 기다렸나」를 직접 잴 수는 없다. 지어내지 않는다 —
대신 **잴 수 있는 둘**로 셈한다:

    ① 밀린 건수      [실측]  = 접미 큐들의 LLEN 합
    ② 쓰는 속도      [실측]  = 최근 N분간 `logger_auditlogs` 에 들어온 행 수

    지연(초) [추정] = 밀린 건수 ÷ 초당 쓰는 속도

속도가 **0인데 밀린 것이 있으면** 나눌 수 없다. 그때는 「마지막으로 쓰인 뒤 흐른
시간」을 쓴다 — 그것은 참값의 **하한**이다(적어도 그만큼은 기다렸다). 모자라게
적지, 부풀리지 않는다.

    · 밀린 것이 0이면 지연은 0이다. **조용한 밤을 경보로 만들지 않는다** —
      큐가 비어 있으면 늦은 것이 없다. 이 갈래가 없으면 트래픽 없는 새벽마다
      경보가 울리고, 그러면 이 신호는 꺼진다(D-290).
"""
from __future__ import annotations

#: kombu redis 전송이 우선순위 큐 이름에 끼우는 구분자. **이 두 바이트가 함정이다.**
PRIORITY_SEP = "\x06\x16"

#: 쓰는 속도를 재는 창(분). 짧으면 조용한 순간에 0 이 나오고, 길면 방금 죽은 것을 못 본다.
RATE_WINDOW_MINUTES = 10


def queue_names(base: str, steps) -> list:
    """`base` 하나가 실제로 차지하는 **모든 redis 키**.

    kombu 규칙: 우선순위 0 은 접미 없이 `base`, 나머지는 `base + SEP + 우선순위`.
    """
    names = [base]
    for pri in steps or ():
        try:
            pri = int(pri)
        except (TypeError, ValueError):
            continue
        if pri:
            name = "%s%s%d" % (base, PRIORITY_SEP, pri)
            if name not in names:
                names.append(name)
    return names


def judge_lag(backlog, rate_per_min, idle_seconds):
    """**순수 함수** — 밀린 건수·쓰는 속도·마지막 쓰기 이후 시간에서 지연(초)을 셈한다.

    `(lag_seconds, basis)`. `None` 은 **못 쟀다**이지 0이 아니다 (D-301).
    """
    if backlog is None:
        return None, "밀린 건수를 **못 쟀다** — 브로커에 못 닿았다"
    if backlog == 0:
        # ★ 큐가 비었으면 늦은 것이 없다. 조용한 밤은 장애가 아니다.
        return 0.0, "밀린 것이 0건 — 지연 없음 [실측]"
    if rate_per_min:
        lag = backlog / (float(rate_per_min) / 60.0)
        return round(lag, 1), ("밀린 %d건 ÷ 쓰는 속도 %.2f건/분 [실측 둘] = %.1f초 [추정]"
                               % (backlog, float(rate_per_min), lag))
    if idle_seconds is None:
        return None, ("밀린 %d건인데 쓰는 속도도 마지막 쓰기 시각도 **못 쟀다** — "
                      "지연을 셈할 근거가 없다" % backlog)
    # ★ 속도 0 + 밀린 것 있음 = **아무도 안 쓰고 있다.** 나눌 수 없으므로 하한을 적는다.
    return float(idle_seconds), (
        "밀린 %d건인데 최근 %d분간 **한 건도 안 쓰였다** — 마지막 쓰기 이후 %d초. "
        "참값의 **하한**이다(적어도 이만큼 기다렸다) [실측]"
        % (backlog, RATE_WINDOW_MINUTES, idle_seconds))


def measure(now=None, base=None) -> dict:
    """지금 이 브로커·이 DB 를 잰다. **못 잰 칸은 `None`** 이다.

    `base` 는 **시험용**이다 — 밀린 큐를 실제로 만들어 이 신호가 빨개지는지 보려면
    워커가 안 먹는 이름이 필요하다. 환경변수로 두지 않는다: 환경변수로 두면 누군가
    운영에서 그 값을 빈 큐로 돌려 놓는 순간 이 신호가 **영원히 초록**이 된다.
    """
    from datetime import datetime, timedelta, timezone as _tz

    out = {"backlog": None, "queue_keys": {}, "queue_base": None,
           "write_rate_per_min": None, "last_write_at": None,
           "idle_seconds": None, "lag_seconds": None, "lag_basis": "",
           "errors": {}}
    now = now or datetime.now(_tz.utc)

    # ── ① 밀린 건수 — **접미가 붙은 이름을 전수로** ────────────────────────
    try:
        from config.celery import app

        base = base or app.conf.task_default_queue or "default"
        steps = ((app.conf.broker_transport_options or {}).get("priority_steps")
                 or list(range(10)))
        out["queue_base"] = base
        conn = app.connection_for_read()
        try:
            client = conn.default_channel.client
            total = 0
            for name in queue_names(base, steps):
                n = int(client.llen(name) or 0)
                if n:
                    out["queue_keys"][repr(name)] = n
                total += n
            out["backlog"] = total
        finally:
            try:
                conn.release()
            except Exception:
                pass
    except Exception as exc:                       # noqa: BLE001
        out["errors"]["backlog"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])

    # ── ② 쓰는 속도 · 마지막 쓰기 ─────────────────────────────────────────
    try:
        from core.logger.models import AuditLogs

        since = now - timedelta(minutes=RATE_WINDOW_MINUTES)
        rows = AuditLogs._base_manager.filter(create_datetime__gte=since).count()
        out["write_rate_per_min"] = round(rows / float(RATE_WINDOW_MINUTES), 3)
        last = (AuditLogs._base_manager.order_by("-create_datetime")
                .values_list("create_datetime", flat=True).first())
        if last is not None:
            out["last_write_at"] = last.isoformat(timespec="seconds")
            out["idle_seconds"] = int((now - last).total_seconds())
    except Exception as exc:                       # noqa: BLE001
        out["errors"]["write_rate"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])

    out["lag_seconds"], out["lag_basis"] = judge_lag(
        out["backlog"], out["write_rate_per_min"], out["idle_seconds"])
    return out


def digest_line(facts: dict | None = None) -> str:
    """생존 알림 본문에 실리는 **한 줄**. 못 쟀으면 못 쟀다고 적는다.

    ★ 왜 안부 편지에 이 줄을 넣는가. 「GuardianX 정상」이라는 제목이 참이려면
      **그 정상을 증명할 기록이 지금 쓰이고 있어야** 한다. 감사 기록이 큐에 갇힌
      채로 나가는 「정상」은 증거 없는 안부다.
    """
    try:
        f = facts if facts is not None else measure()
    except Exception as exc:                       # noqa: BLE001
        return "감사 기록 대기: **못 쟀다** (%s)" % type(exc).__name__
    if f.get("backlog") is None:
        return "감사 기록 대기: **못 쟀다** — %s" % (
            f.get("errors", {}).get("backlog") or "사유 없음")
    lag = f.get("lag_seconds")
    if lag is None:
        return "감사 기록 대기 %d건 · 지연 **못 쟀다**" % f["backlog"]
    return "감사 기록 대기 %d건 · 지연 %.0f초" % (f["backlog"], lag)
