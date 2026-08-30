"""
🔐 Signal Protection - Prevent Recursive Loops & Rate Limiting
CRITICAL FIX để prevent server down
"""
import threading
import time
from collections import OrderedDict
from functools import wraps
from django.core.cache import cache as django_cache


# ═══════════════════════════════════════════════════════════════════════════
# 속도 제한 — **버리지 않는다. 미룬다** (D-367)
# ═══════════════════════════════════════════════════════════════════════════
#
# 무엇이 잘못돼 있었나 — [실측 2026-09-11 · 코드]
# ------------------------------------------------
# 이 파일의 `rate_limited` 는 상한을 넘으면 **`return` 했다.** 한 줄 찍고 끝이었다:
#
#     if SignalProtection.check_rate_limit(model_name, max_per_minute):
#         print(f"⚠️ Rate limit exceeded for {model_name} ... - skipping")
#         return                      # ← 이 자리가 **drop** 이다
#
# 유일한 사용처는 `common/universal_optimization.py::universal_cache_invalidation`
# (`post_save`·`post_delete` 전역 수신기, 200/분)이므로 **버려진 것은 이벤트 행이
# 아니라 캐시 무효화**다. 이벤트는 `kernels/k1_event/services.py::record_detection`
# 이 `@transaction.atomic` 안에서 저장하고, 그 경로에는 상한도 큐도 없다.
#
# ★ 그래도 결함이다. 등급을 낮추지 않는다:
#     캐시 무효화를 버리면 **낡은 화면이 남는다.** 폭주는 곧 재난이고, 재난일 때
#     관제 대시보드·이벤트 목록이 옛 데이터를 보여 준다. 「이벤트가 사라졌다」와
#     **보는 사람에게는 같은 일**이다. F-10 「30초」를 재는 화면이 그 화면이다.
#
# 그래서 규칙을 바꾼다 — **지연은 허용, 소실은 불허** (D-367)
# ------------------------------------------------------------
#   ① 상한 아래면 지금 한다
#   ② 상한을 넘으면 **미룬다** (버리지 않는다)
#   ③ 같은 (모델, pk) 의 미룬 것은 **접는다.** 접는 것은 버리는 것이 아니다 —
#      같은 행의 무효화 두 번은 **같은 무효화 한 번**이다. 이 접기가 없으면
#      큐가 폭주를 그대로 받아 상한이 있던 이유(서버 보호)가 사라진다
#   ④ 큐가 차면 **가장 낮은 등급부터** 버린다. 가장 오래된 것이 아니다
#   ⑤ ★ **심각 등급은 어떤 경우에도 버리지 않는다.** 큐가 심각 등급으로 가득 차면
#      새 심각 등급은 **그 자리에서 처리한다** — 느려지는 것은 허용, 잃는 것은 불허
#
# 강제: `scripts/verify_event_drop.py` (소실 경로 부작위 검사) ·
#       `backend/tests/test_event_no_drop.py`

#: 미룬 것을 담는 자리의 상한. **접기(③) 덕에 이 수는 「서로 다른 행의 수」**다 —
#: 같은 행이 100번 저장돼도 한 칸만 쓴다. 그래서 폭주보다 **테넌트 규모**를 따른다.
#: 39대 · 100대 규모에서 1분 안에 바뀌는 서로 다른 행이 5000을 넘기 어렵다 [추정].
#: 넘으면 ④⑤ 가 판정하고, 버린 건수는 `SignalProtection.defer_stats()` 에 남는다 —
#: **조용히 버리지 않는다** (D-290).
DEFER_QUEUE_MAX = 5000

#: 한 번 흘릴 때 처리하는 최대 건수. 신호 처리기 안에서 흘리므로 무한히 하면
#: 저장 한 번이 큐 전체를 떠안는다 — **미루기가 새로운 정지가 된다.**
DRAIN_BATCH = 50

#: 흘리개 스레드가 쉬는 간격(초). 폭주가 끝나 신호가 끊기면 흘릴 사람이 없다 —
#: 그때 낡은 캐시가 **영원히** 남는 것을 막는 것이 이 스레드의 유일한 일이다.
DRAIN_INTERVAL = 5.0

#: 등급. **낮은 수가 높은 등급**이다 (버릴 때 큰 수부터 버린다).
PRIORITY_CRITICAL = 0   # 재난 경로 — 버리지 않는다. 이건 상수다
PRIORITY_NORMAL = 1
PRIORITY_LOW = 2

#: 재난 경로의 모델. **이름으로 잠근다** (D-285 ②) — `sender._meta.model_name` 소문자.
#: 늘리려면 여기와 `backend/tests/test_event_no_drop.py::CRITICAL_MODELS` 를
#: **같은 커밋에서** 고친다. 두 벌은 반드시 어긋난다 (D-369).
CRITICAL_MODELS = frozenset({
    "detectionevent",      # 탐지 이벤트 — 이 제품이 하는 일 그 자체
    "eventclip",           # 이벤트의 영상 구간 (D-306 · 계약 11조)
    "notificationrule",    # 발송 규칙 — 낡으면 **안 나가야 할 곳으로 나간다**
    "deliveryrecord",      # 발송 이력 — F-10 「30초」를 재는 두 점이 여기 있다
})


def priority_of(sender, instance) -> int:
    """이 저장이 어느 등급인가. **재난 경로면 심각 등급이다.**

    ★ `severity` 필드를 보지 않고 **모델로** 정한다. 이유는 D-290 이다:
      `severity='info'` 인 탐지 이벤트도 **오탐률의 분모**이고(K1 이 이벤트를 접지
      않는 이유와 같다), 그 분모가 조용히 줄면 U1 의 수가 거짓이 된다.
      「낮은 등급 이벤트」와 「이벤트가 아닌 것」은 다르다.
    """
    model_name = getattr(getattr(sender, "_meta", None), "model_name", None)
    if model_name is None:
        model_name = getattr(sender, "__name__", "unknown")
    return PRIORITY_CRITICAL if str(model_name).lower() in CRITICAL_MODELS else PRIORITY_NORMAL


class SignalProtection:
    """
    🔐 Protection mechanisms for signal handlers
    - Recursion detection
    - Rate limiting
    - Debouncing
    """
    
    # Recursion guard (thread-local)
    _recursion_guard = threading.local()
    
    # Rate limiting (shared)
    _rate_limit_lock = threading.Lock()
    _rate_limit_counters = {}  # {model_name: [(timestamp1, timestamp2, ...)]}
    
    # Debouncing (shared)
    _debounce_lock = threading.Lock()
    _debounce_timers = {}  # {key: Timer}
    _debounce_pending = {}  # {key: data}
    
    @classmethod
    def check_recursion(cls, signal_key: str) -> bool:
        """
        🔐 Check if signal is already being processed (recursion detection)
        Returns: True if recursion detected, False otherwise
        """
        if not hasattr(cls._recursion_guard, 'active'):
            cls._recursion_guard.active = set()
        
        if signal_key in cls._recursion_guard.active:
            return True  # Recursion detected!
        
        return False
    
    @classmethod
    def mark_active(cls, signal_key: str):
        """Mark signal as active"""
        if not hasattr(cls._recursion_guard, 'active'):
            cls._recursion_guard.active = set()
        cls._recursion_guard.active.add(signal_key)
    
    @classmethod
    def mark_inactive(cls, signal_key: str):
        """Mark signal as inactive"""
        if hasattr(cls._recursion_guard, 'active'):
            cls._recursion_guard.active.discard(signal_key)
    
    @classmethod
    def check_rate_limit(cls, model_name: str, max_per_minute: int = 100) -> bool:
        """
        🚦 Check if rate limit exceeded
        Returns: True if rate limit exceeded, False otherwise
        """
        current_time = time.time()
        cutoff_time = current_time - 60  # 1 minute ago
        
        with cls._rate_limit_lock:
            # Get existing timestamps
            if model_name not in cls._rate_limit_counters:
                cls._rate_limit_counters[model_name] = []
            
            timestamps = cls._rate_limit_counters[model_name]
            
            # Remove old timestamps (> 1 minute ago)
            timestamps = [t for t in timestamps if t > cutoff_time]
            cls._rate_limit_counters[model_name] = timestamps
            
            # Check if limit exceeded
            if len(timestamps) >= max_per_minute:
                return True  # Rate limit exceeded!
            
            # Add current timestamp
            timestamps.append(current_time)
            
            return False
    

    # ═══════════════════════════════════════════════════════════════════
    # 미룬 것을 담는 자리 — **버리지 않는다** (D-367)
    # ═══════════════════════════════════════════════════════════════════
    #
    # 키는 `(함수, 모델, pk)` 다. 같은 키가 다시 오면 **접는다** — 같은 행의
    # 무효화 두 번은 같은 무효화 한 번이다. 접힌 횟수는 세어서 남긴다
    # (「접었다」와 「버렸다」가 통계에서 구별돼야 한다 — D-290).
    _defer_lock = threading.Lock()
    _defer_queue = OrderedDict()      # {key: dict(priority, func, sender, instance, ...)}
    _defer_flusher = None             # 흘리개 스레드. 첫 미룸 때 하나만 뜬다
    _defer_stats = {
        "deferred": 0,       # 미룬 횟수
        "coalesced": 0,      # 접은 횟수 — **버린 것이 아니다**
        "drained": 0,        # 나중에 실제로 처리한 횟수
        "ran_inline": 0,     # 큐가 심각 등급으로 차서 그 자리에서 처리한 횟수
        "dropped": 0,        # ★ **버린 횟수. 0 이어야 한다** — 게이트가 이 수를 본다
        "drop_detail": {},   # 버렸다면 무엇을 버렸는지 (모델별 건수)
        "failed": 0,         # 흘리다 예외가 난 횟수 (버린 것과 구별한다)
    }

    @classmethod
    def defer_stats(cls) -> dict:
        """미룸 통계 한 벌. **`dropped` 가 0 이 아니면 그것이 소실이다.**"""
        with cls._defer_lock:
            out = dict(cls._defer_stats)
            out["drop_detail"] = dict(cls._defer_stats["drop_detail"])
            out["queue_len"] = len(cls._defer_queue)
            return out

    @classmethod
    def reset_defer_state(cls):
        """시험용 — 큐와 통계를 비운다. 운영 경로에서 부르지 않는다."""
        with cls._defer_lock:
            cls._defer_queue.clear()
            cls._defer_stats.update({
                "deferred": 0, "coalesced": 0, "drained": 0,
                "ran_inline": 0, "dropped": 0, "failed": 0,
            })
            cls._defer_stats["drop_detail"] = {}
        with cls._rate_limit_lock:
            cls._rate_limit_counters.clear()

    @classmethod
    def defer(cls, func, sender, instance, kwargs, *, priority: int,
              model_name: str) -> str:
        """상한을 넘은 호출 하나를 **미룬다.**

        반환:
            `"coalesced"`  같은 (함수·모델·pk) 가 이미 큐에 있다 — 접었다
            `"queued"`     큐에 넣었다
            `"run_now"`    ★ 큐가 **심각 등급으로** 가득 찼다. 버릴 수 없으므로
                           부르는 쪽이 **그 자리에서** 처리하라는 뜻이다
        """
        instance_id = getattr(instance, "pk", None)
        if instance_id is None:
            instance_id = getattr(instance, "id", id(instance))
        key = (getattr(func, "__name__", repr(func)), str(model_name), instance_id)

        with cls._defer_lock:
            existing = cls._defer_queue.get(key)
            if existing is not None:
                # 접는다 — 마지막 상태를 남긴다. 무효화는 「최신 상태 기준」이 옳다.
                existing["instance"] = instance
                existing["kwargs"] = kwargs
                existing["coalesced"] += 1
                # 등급은 **높은 쪽(작은 수)** 을 남긴다. 낮춰 쓰면 심각한 것이
                # 낮은 등급으로 큐에 앉아 넷째 규칙에서 버려질 수 있다.
                existing["priority"] = min(existing["priority"], priority)
                cls._defer_stats["coalesced"] += 1
                return "coalesced"

            if len(cls._defer_queue) >= DEFER_QUEUE_MAX:
                victim_key = cls._pick_victim_locked(priority)
                if victim_key is None:
                    # 버릴 수 있는 것이 없다 — 큐가 전부 심각 등급이다.
                    # **심각 등급은 어떤 경우에도 버리지 않는다.**
                    cls._defer_stats["ran_inline"] += 1
                    return "run_now"
                victim = cls._defer_queue.pop(victim_key)
                cls._defer_stats["dropped"] += 1
                vmodel = victim["model_name"]
                cls._defer_stats["drop_detail"][vmodel] = (
                    cls._defer_stats["drop_detail"].get(vmodel, 0) + 1)

            cls._defer_queue[key] = {
                "priority": priority,
                "func": func,
                "sender": sender,
                "instance": instance,
                "kwargs": kwargs,
                "model_name": str(model_name),
                "queued_at": time.time(),
                "coalesced": 0,
            }
            cls._defer_stats["deferred"] += 1

        cls._ensure_flusher()
        return "queued"

    @classmethod
    def _pick_victim_locked(cls, incoming_priority: int):
        """버릴 것을 고른다 — **가장 낮은 등급부터. 가장 오래된 것이 아니다.**

        ★ 심각 등급(`PRIORITY_CRITICAL`)은 후보에 넣지 않는다. 그리고 들어오는
          것보다 **엄격히 낮은 등급**만 버린다 — 같은 등급을 버리면 「누가 먼저
          왔는가」가 등급 규칙을 이기고, 그러면 규칙이 규칙이 아니다.
        """
        worst_key, worst_priority = None, incoming_priority
        for k, v in cls._defer_queue.items():
            p = v["priority"]
            if p == PRIORITY_CRITICAL:
                continue
            if p > worst_priority:
                worst_key, worst_priority = k, p
        return worst_key

    @classmethod
    def _ensure_flusher(cls):
        """흘리개 스레드를 **하나만** 띄운다.

        왜 필요한가: 큐는 다음 신호가 올 때 흘러간다. 그런데 폭주가 끝나면
        신호가 끊기고, 그러면 마지막 몇 건이 **영원히** 큐에 남는다 —
        그 상태가 곧 「낡은 화면이 안 풀린다」이고, 미루기가 사실상 버리기가 된다.
        """
        if cls._defer_flusher is not None and cls._defer_flusher.is_alive():
            return
        with cls._defer_lock:
            if cls._defer_flusher is not None and cls._defer_flusher.is_alive():
                return
            t = threading.Thread(target=cls._flush_loop, name="signal-defer-flusher",
                                 daemon=True)
            cls._defer_flusher = t
        t.start()

    @classmethod
    def _flush_loop(cls):
        idle_rounds = 0
        while idle_rounds < 12:          # 1분 동안 할 일이 없으면 눕는다
            time.sleep(DRAIN_INTERVAL)
            try:
                done = cls.drain_deferred(None)
            except Exception:            # noqa: BLE001 — 흘리개가 죽으면 큐가 남는다
                done = 0
                cls._defer_stats["failed"] += 1
            idle_rounds = 0 if done else idle_rounds + 1

    @classmethod
    def drain_deferred(cls, max_per_minute) -> int:
        """미룬 것을 **등급 높은 것부터** 처리한다. 처리한 건수를 돌려준다.

        `max_per_minute` 가 `None` 이면 상한을 묻지 않는다 — 흘리개 스레드는
        요청 경로 밖이라 여기서 막을 이유가 없다. 요청 경로에서 부를 때는 상한을
        넘겨서 **미루기가 새로운 정지가 되지 않게** 한다.
        """
        done = 0
        for _ in range(DRAIN_BATCH):
            with cls._defer_lock:
                if not cls._defer_queue:
                    return done
                # 등급이 높은 것(작은 수) 중 **가장 오래된 것**
                best_key = min(
                    cls._defer_queue,
                    key=lambda k: (cls._defer_queue[k]["priority"],
                                   cls._defer_queue[k]["queued_at"]),
                )
                model_name = cls._defer_queue[best_key]["model_name"]
            if max_per_minute is not None and \
                    cls.check_rate_limit(model_name, max_per_minute):
                return done             # 아직 여유가 없다. 큐에 그대로 둔다
            with cls._defer_lock:
                entry = cls._defer_queue.pop(best_key, None)
            if entry is None:
                continue
            try:
                entry["func"](entry["sender"], entry["instance"], **entry["kwargs"])
                with cls._defer_lock:
                    cls._defer_stats["drained"] += 1
            except Exception:            # noqa: BLE001
                # ★ 실패는 소실이 아니다 — **세어서 남긴다.** 조용히 넘기면
                #   「미뤘다」와 「미루다 잃었다」가 통계에서 같아진다 (D-290).
                with cls._defer_lock:
                    cls._defer_stats["failed"] += 1
                import logging
                logging.getLogger(__name__).warning(
                    "[DEFER] %s 무효화 재시도 실패 — 버린 것이 아니라 실패다",
                    model_name, exc_info=True)
            finally:
                try:
                    from django.db import connection
                    if (connection.connection is not None
                            and threading.current_thread() is cls._defer_flusher):
                        connection.close()
                except Exception:        # noqa: BLE001
                    pass
            done += 1
        return done

    @classmethod
    def cleanup_rate_limits(cls):
        """Cleanup old rate limit data (should run periodically)"""
        current_time = time.time()
        cutoff_time = current_time - 120  # Keep 2 minutes of data
        
        with cls._rate_limit_lock:
            for model_name in list(cls._rate_limit_counters.keys()):
                timestamps = cls._rate_limit_counters[model_name]
                timestamps = [t for t in timestamps if t > cutoff_time]
                
                if not timestamps:
                    del cls._rate_limit_counters[model_name]
                else:
                    cls._rate_limit_counters[model_name] = timestamps


def recursion_protected(func):
    """
    🔐 Decorator: Protect function from recursive calls
    
    Usage:
        @receiver(post_save)
        @recursion_protected
        def my_signal_handler(sender, instance, **kwargs):
            ...
    """
    @wraps(func)
    def wrapper(sender, instance, **kwargs):
        # Generate unique key
        instance_id = getattr(instance, 'id', getattr(instance, 'pk', 'unknown'))
        # Handle both model classes and instances
        if hasattr(sender, '__name__'):
            sender_name = sender.__name__
        elif hasattr(sender, '_meta') and hasattr(sender._meta, 'model_name'):
            sender_name = sender._meta.model_name
        else:
            sender_name = 'unknown'
        signal_key = f"{sender_name}_{instance_id}_{func.__name__}"
        
        # Check recursion
        if SignalProtection.check_recursion(signal_key):
            print(f"⚠️ Recursion detected: {signal_key} - skipping")
            return
        
        try:
            # Mark as active
            SignalProtection.mark_active(signal_key)
            
            # Execute function
            return func(sender, instance, **kwargs)
            
        finally:
            # Always mark as inactive
            SignalProtection.mark_inactive(signal_key)
    
    return wrapper


def rate_limited(max_per_minute: int = 100):
    """
    🚦 Decorator: 상한을 넘은 호출을 **미룬다** (D-367). 버리지 않는다.

    Usage:
        @receiver(post_save)
        @rate_limited(max_per_minute=50)
        def my_signal_handler(sender, instance, **kwargs):
            ...

    ★ 이 데코레이터의 옛 판(2026-09-11 이전)은 상한을 넘으면 `return` 했다.
      바꾼 이유와 규칙은 이 절 머리말에 있다 — **지연은 허용, 소실은 불허.**
    """
    def decorator(func):
        @wraps(func)
        def wrapper(sender, instance, **kwargs):
            # Handle both model classes and instances
            if hasattr(sender, '_meta'):
                model_name = sender._meta.model_name
            else:
                model_name = getattr(sender, '__name__', 'unknown')

            # ① 밀린 것이 먼저다. 새 것을 처리하고 밀린 것을 두면 큐가 늙는다.
            SignalProtection.drain_deferred(max_per_minute)

            # ② 상한 아래면 지금 한다
            if not SignalProtection.check_rate_limit(model_name, max_per_minute):
                return func(sender, instance, **kwargs)

            # ③ 넘었다 — **미룬다**
            outcome = SignalProtection.defer(
                func, sender, instance, kwargs,
                priority=priority_of(sender, instance),
                model_name=model_name,
            )
            if outcome == "run_now":
                # ⑤ 큐가 심각 등급으로 가득 찼다. 버릴 수 없으므로 **여기서 한다.**
                #    느려지는 것은 허용이고, 잃는 것은 불허다.
                return func(sender, instance, **kwargs)
            return None

        return wrapper
    return decorator


def debounced(wait_seconds: float = 1.0):
    """
    ⏱️ Decorator: Debounce function calls (group rapid calls into one)
    
    Usage:
        @receiver(m2m_changed)
        @debounced(wait_seconds=1.0)
        def my_m2m_handler(sender, instance, action, **kwargs):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(sender, instance, action=None, **kwargs):
            # Generate unique key
            instance_id = getattr(instance, 'id', getattr(instance, 'pk', 'unknown'))
            # Handle both model classes and instances
            if hasattr(sender, '__name__'):
                sender_name = sender.__name__
            elif hasattr(sender, '_meta') and hasattr(sender._meta, 'model_name'):
                sender_name = sender._meta.model_name
            else:
                sender_name = 'unknown'
            debounce_key = f"{sender_name}_{instance_id}_{func.__name__}"
            
            with SignalProtection._debounce_lock:
                # Cancel previous timer
                if debounce_key in SignalProtection._debounce_timers:
                    SignalProtection._debounce_timers[debounce_key].cancel()
                
                # Store pending data
                SignalProtection._debounce_pending[debounce_key] = {
                    'sender': sender,
                    'instance': instance,
                    'action': action,
                    'kwargs': kwargs
                }
                
                # Create new timer
                def execute_function():
                    with SignalProtection._debounce_lock:
                        if debounce_key in SignalProtection._debounce_pending:
                            data = SignalProtection._debounce_pending.pop(debounce_key)
                            SignalProtection._debounce_timers.pop(debounce_key, None)
                            
                            # Execute function with pending data
                            func(data['sender'], data['instance'], 
                                 action=data['action'], **data['kwargs'])
                
                timer = threading.Timer(wait_seconds, execute_function)
                SignalProtection._debounce_timers[debounce_key] = timer
                timer.start()
        
        return wrapper
    return decorator


def protected_signal(max_per_minute: int = 100, debounce_seconds: float = 0):
    """
    🔐 Decorator: Full protection (recursion + rate limit + optional debounce)
    
    Usage:
        @receiver(post_save)
        @protected_signal(max_per_minute=50, debounce_seconds=1.0)
        def my_signal_handler(sender, instance, **kwargs):
            ...
    """
    def decorator(func):
        # Apply protections in order
        protected_func = recursion_protected(func)
        protected_func = rate_limited(max_per_minute)(protected_func)
        
        if debounce_seconds > 0:
            protected_func = debounced(debounce_seconds)(protected_func)
        
        return protected_func
    
    return decorator

