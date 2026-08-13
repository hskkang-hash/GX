import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pytz
from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.db.models import Min
from django.utils import timezone
from django.utils.dateparse import parse_datetime


logger = logging.getLogger(__name__)
IN_PROCESS_STATUS_CODES = {"in_process", "in_progress"}

# Activation locking:
# - Prevent concurrent activation tasks from starting profiles that share the same drone(s)
# - Use cache.add for a lightweight distributed lock (requires shared cache backend for multi-worker safety)
DRONE_ACTIVATION_LOCK_TTL_SECONDS = 10 * 60  # 10 minutes safety window
DRONE_RESERVATION_KEY_PREFIX = "surveillance:drone_reservation:"
DRONE_RESERVATION_MIN_TTL_SECONDS = 60 * 60  # 1 hour
DRONE_RESERVATION_BUFFER_SECONDS = 60 * 60   # +1 hour buffer after end/start window


def _drone_lock_key(device_id: int) -> str:
    return f"surveillance:drone_activation_lock:{device_id}"


def _acquire_drone_locks(device_ids: Sequence[int], owner: str) -> Tuple[bool, List[str]]:
    """
    Acquire distributed locks for the given device_ids.
    Returns (success, acquired_keys).
    """
    acquired: List[str] = []
    # Deterministic order to reduce risk of partial lock patterns
    for device_id in sorted(set(int(x) for x in device_ids if x)):
        key = _drone_lock_key(device_id)
        try:
            ok = cache.add(key, owner, timeout=DRONE_ACTIVATION_LOCK_TTL_SECONDS)
        except Exception as exc:  # cache backend error
            logger.warning("[SURVEILLANCE] Cache error while acquiring drone lock %s: %s", key, exc)
            ok = False
        if not ok:
            # Release what we acquired so far
            for acquired_key in acquired:
                try:
                    cache.delete(acquired_key)
                except Exception:
                    pass
            return False, []
        acquired.append(key)
    return True, acquired


def _release_drone_locks(keys: Sequence[str]) -> None:
    for key in keys:
        try:
            cache.delete(key)
        except Exception:
            pass


def _drone_reservation_key(device_id: int) -> str:
    return f"{DRONE_RESERVATION_KEY_PREFIX}{device_id}"


def _get_reserved_profile_id(device_id: int) -> Optional[int]:
    """
    Reservation value is expected to be either:
    - int profile_id
    - dict with {"profile_id": int, ...}
    """
    try:
        value = cache.get(_drone_reservation_key(device_id))
    except Exception:
        return None

    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        candidate = value.get("profile_id")
        if isinstance(candidate, int):
            return candidate
        try:
            return int(candidate)
        except Exception:
            return None
    try:
        return int(value)
    except Exception:
        return None


def _resolve_drone_unavailable_cancel_reason(language_code: Optional[str]) -> str:
    from common.constant import MESSAGE_ENUM

    reason_dict = MESSAGE_ENUM.DRONE_UNAVAILABLE_CANCEL_REASON
    normalized_map = {}
    fallback_value = None
    for key, message in reason_dict.items():
        if isinstance(key, str):
            normalized = key.lower()
        else:
            candidate = getattr(key, "value", None)
            if isinstance(candidate, str):
                normalized = candidate.lower()
            else:
                candidate = getattr(key, "code", None)
                if isinstance(candidate, str):
                    normalized = candidate.lower()
                else:
                    normalized = str(key).lower()
        normalized_map[normalized] = message
        if fallback_value is None and normalized == "en":
            fallback_value = message

    if fallback_value is None and normalized_map:
        fallback_value = next(iter(normalized_map.values()))

    if language_code:
        normalized_language = language_code.lower()
        if normalized_language in normalized_map:
            return normalized_map[normalized_language]

    return fallback_value or "Profile cancelled because assigned drones are performing other missions"


def _is_profile_ended(profile_id: int) -> bool:
    """
    Consider a profile ended if it has actual_end_time, or status in cancelled/completed/rejected.
    """
    try:
        from surveillance.models import SurveillanceProfile

        row = (
            SurveillanceProfile._base_manager
            .select_related("status")
            .filter(id=profile_id)
            .values("actual_end_time", "status__code")
            .first()
        )
        if not row:
            return True
        if row.get("actual_end_time") is not None:
            return True
        status_code = row.get("status__code")
        return status_code in {"cancelled", "completed", "rejected"}
    except Exception:
        # Be conservative: do NOT treat unknown as ended
        return False


def _compute_reservation_ttl_seconds(profile) -> int:
    """
    Compute a dynamic reservation TTL.
    - Prefer estimated_end_time if available
    - Otherwise, keep until after start_time (+buffer)
    - Always at least DRONE_RESERVATION_MIN_TTL_SECONDS
    """
    now = timezone.now()
    if timezone.is_naive(now):
        now = timezone.make_aware(now, timezone.get_current_timezone())

    start_time = getattr(profile, "start_time", None)
    if start_time and timezone.is_naive(start_time):
        start_time = timezone.make_aware(start_time, timezone.get_current_timezone())

    estimated_end = getattr(profile, "estimated_end_time", None)
    if estimated_end and timezone.is_naive(estimated_end):
        estimated_end = timezone.make_aware(estimated_end, timezone.get_current_timezone())

    target = None
    if estimated_end:
        target = estimated_end
    elif start_time:
        target = start_time

    if not target:
        return max(DRONE_RESERVATION_MIN_TTL_SECONDS, DRONE_ACTIVATION_LOCK_TTL_SECONDS)

    seconds = (target - now).total_seconds() + DRONE_RESERVATION_BUFFER_SECONDS
    return int(max(DRONE_RESERVATION_MIN_TTL_SECONDS, seconds))


def _get_profile_state(profile_id: int) -> Optional[Dict[str, Any]]:
    """
    Lightweight profile snapshot for contention decisions.
    """
    try:
        from surveillance.models import SurveillanceProfile

        row = (
            SurveillanceProfile._base_manager
            .select_related("status")
            .filter(id=profile_id)
            .values("id", "start_time", "not_yet", "actual_end_time", "status__code")
            .first()
        )
        return row
    except Exception:
        return None


def _is_preemptable_owner(owner_state: Dict[str, Any], current_start_time: Optional[datetime]) -> bool:
    """
    Preempt only if owner is a waiting profile (not_yet=True), not started/in-process,
    and has a later start_time than current profile.
    """
    try:
        if not owner_state:
            return False
        if owner_state.get("actual_end_time") is not None:
            return True
        if not bool(owner_state.get("not_yet")):
            return False
        status_code = owner_state.get("status__code")
        if status_code in IN_PROCESS_STATUS_CODES:
            return False
        owner_start = owner_state.get("start_time")
        if not owner_start or not current_start_time:
            return False
        if timezone.is_naive(owner_start):
            owner_start = timezone.make_aware(owner_start, timezone.get_current_timezone())
        if timezone.is_naive(current_start_time):
            current_start_time = timezone.make_aware(current_start_time, timezone.get_current_timezone())
        # Strictly later -> preemptable
        return owner_start > (current_start_time + timedelta(seconds=1))
    except Exception:
        return False


def _db_winner_profile_ids_by_device(device_ids: Sequence[int]) -> Dict[int, int]:
    """
    Fallback winner selection by DB when reservation is missing/unreliable.
    Winner is the profile with the earliest start_time; if equal, earliest SurveillanceProfileDrone.modified_on
    among profiles that are waiting to start (not_yet=True), not ended.
    Tie-breaker: smaller profile_id.
    """
    try:
        from surveillance.models import SurveillanceProfileDrone

        rows = (
            SurveillanceProfileDrone._base_manager
            .filter(
                device_id__in=list({int(x) for x in device_ids if x}),
                profile__not_yet=True,
                profile__actual_end_time__isnull=True,
            )
            .exclude(profile__status__code__in=["cancelled", "completed", "rejected"])
            .values("device_id", "profile_id", "profile__start_time")
            .annotate(first_checked_at=Min("modified_on"))
            .order_by("device_id", "profile__start_time", "first_checked_at", "profile_id")
        )
        winners: Dict[int, int] = {}
        for row in rows:
            did = int(row["device_id"])
            if did not in winners and row.get("profile_id") is not None:
                winners[did] = int(row["profile_id"])
        return winners
    except Exception as exc:
        logger.warning("[SURVEILLANCE] DB fallback winner selection failed: %s", exc)
        return {}


def _normalize_language_code(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return str(value).lower()


def _resolve_auto_cancel_reason(language_code: Optional[str]) -> str:
    from common.constant import MESSAGE_ENUM

    reason_dict = MESSAGE_ENUM.SURVEILLANCE_PROFILE_DRONE_ISSUE_CANCEL_REASON
    normalized_map = {}
    fallback_value = None
    for key, message in reason_dict.items():
        if isinstance(key, str):
            normalized = key.lower()
        else:
            candidate = getattr(key, "value", None)
            if isinstance(candidate, str):
                normalized = candidate.lower()
            else:
                candidate = getattr(key, "code", None)
                if isinstance(candidate, str):
                    normalized = candidate.lower()
                else:
                    normalized = str(key).lower()
        normalized_map[normalized] = message
        if fallback_value is None and normalized == "en":
            fallback_value = message

    if fallback_value is None and normalized_map:
        fallback_value = next(iter(normalized_map.values()))

    if language_code:
        normalized_language = language_code.lower()
        if normalized_language in normalized_map:
            return normalized_map[normalized_language]

    return fallback_value or "Profile cancelled because a drone encountered an issue during surveillance."


def _parse_metadata_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse datetime từ metadata và normalize về UTC."""
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        return None

    # Normalize về UTC để đảm bảo tính toán nhất quán
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    
    # Convert về UTC nếu chưa phải UTC
    if parsed.tzinfo != pytz.UTC:
        parsed = parsed.astimezone(pytz.UTC)

    return parsed


def _get_overdue_profile_hours() -> float:
    """
    Lấy thời gian overdue từ AdminConfig 'Overdue Profile', mặc định 24 giờ.
    
    NOTE: close_old_connections() đã được gọi tự động bởi task_prerun signal trong celery.py
    Chỉ gọi lại khi retry sau SSL/connection errors
    """
    from django.db.utils import OperationalError, InterfaceError
    
    default_hours = 24.0
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            from core.configuration.models import AdminConfig
            
            # Use _base_manager to avoid group filter in background tasks
            config = AdminConfig._base_manager.filter(name='Overdue Profile').first()
            if config and isinstance(getattr(config, 'settings', None), dict):
                raw_value = config.settings.get('overdue_hours')
                if raw_value is not None:
                    if isinstance(raw_value, (int, float)):
                        return float(raw_value)
                    else:
                        return float(str(raw_value).strip())
            return default_hours
        except (OperationalError, InterfaceError) as exc:
            error_msg = str(exc).lower()
            if any(keyword in error_msg for keyword in ['ssl', 'connection', 'eof', 'closed', 'wrong version']):
                if attempt < max_retries - 1:
                    logger.warning(
                        "[SURVEILLANCE][OVERDUE] SSL/Connection error khi lấy config (attempt %s/%s): %s, retrying...",
                        attempt + 1,
                        max_retries,
                        str(exc)
                    )
                    # Chỉ close connections khi retry sau SSL/connection error
                    from django.db import close_old_connections, connections
                    close_old_connections()
                    connections.close_all()
                    continue
                else:
                    logger.warning(
                        "[SURVEILLANCE][OVERDUE] Không thể lấy config Overdue Profile sau %s attempts: %s, dùng giá trị mặc định %s giờ",
                        max_retries,
                        str(exc),
                        default_hours
                    )
                    return default_hours
            else:
                logger.warning(
                    "[SURVEILLANCE][OVERDUE] Không thể lấy config Overdue Profile: %s, dùng giá trị mặc định %s giờ",
                    str(exc),
                    default_hours
                )
                return default_hours
        except Exception as exc:
            logger.warning(
                "[SURVEILLANCE][OVERDUE] Không thể lấy config Overdue Profile: %s, dùng giá trị mặc định %s giờ",
                str(exc),
                default_hours
            )
            return default_hours
    
    return default_hours


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def execute_surveillance_profile(self, profile_id: int) -> None:
    """
    Triggered by scheduler khi tới giờ chạy profile.
    Hiện tại chỉ ghi nhận metadata và chuyển status nếu có cấu hình.
    """

    from surveillance.models import SurveillanceProfile, SurveillanceStatus

    try:
        # Use _base_manager to avoid group filter in background tasks
        profile = SurveillanceProfile._base_manager.select_related("status").get(id=profile_id)
    except SurveillanceProfile.DoesNotExist:
        logger.warning("[SURVEILLANCE] profile %s not found when executing", profile_id)
        return

    try:
        metadata = profile.metadata or {}
        metadata.update({
            "last_executed_at": timezone.now().isoformat(),
            "executed_by_task": self.request.id,
        })

        # Nếu hệ thống có status 'pending_device_check' thì chuyển sang đó
        next_status: Optional[SurveillanceStatus] = None
        if profile.status and profile.status.code == "pending_approval":
            next_status = SurveillanceStatus._base_manager.filter(code="pending_device_check").first()

        if next_status:
            profile.status = next_status

        profile.metadata = metadata
        profile.save(update_fields=["status", "metadata", "modified_on"])

        logger.info("[SURVEILLANCE] Scheduled profile %s executed", profile.code)

    except Exception as exc:
        logger.exception("[SURVEILLANCE] Error executing profile %s: %s", profile.code, exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def activate_surveillance_profile(self, profile_id: int) -> None:
    """
    Kích hoạt profile khi đến giờ start_time.
    Chuyển sang in_progress và upload lên Flightbird.
    """

    from surveillance.models import SurveillanceProfile, SurveillanceProfileDrone
    from surveillance.services.surveillance_profile_service import SurveillanceProfileService

    try:
        # Use _base_manager to avoid group filter in background tasks
        profile = SurveillanceProfile._base_manager.select_related("status").get(id=profile_id)
    except SurveillanceProfile.DoesNotExist:
        logger.warning("[SURVEILLANCE] Profile %s not found when activating", profile_id)
        return

    acquired_lock_keys: List[str] = []
    try:
        # Kiểm tra profile đã được kích hoạt chưa hoặc đã bị hủy
        if profile.actual_end_time:
            logger.info("[SURVEILLANCE] Profile %s đã có actual_end_time, bỏ qua kích hoạt", profile_id)
            return

        # Kiểm tra status hiện tại
        current_status_code = profile.status.code if profile.status else None
        if current_status_code in {"in_progress", "in_process"}:
            logger.info("[SURVEILLANCE] Profile %s đã ở trạng thái %s, bỏ qua kích hoạt", profile_id, current_status_code)
            return

        # Kiểm tra start_time đã đến chưa để tránh activate sớm
        if profile.start_time:
            start_time = profile.start_time
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time, timezone.get_current_timezone())
            
            now = timezone.now()
            if now.tzinfo != pytz.UTC:
                now = now.astimezone(pytz.UTC)
            if start_time.tzinfo != pytz.UTC:
                start_time = start_time.astimezone(pytz.UTC)
            
            # Cho phép chênh lệch 30 giây để tránh race condition với process_auto_launch
            if start_time > now + timedelta(seconds=30):
                logger.info(
                    "[SURVEILLANCE] Profile %s chưa đến giờ start_time (start_time=%s, now=%s), bỏ qua kích hoạt",
                    profile_id,
                    start_time.isoformat(),
                    now.isoformat(),
                )
                return

        # 1) Load assigned drones (devices)
        assignments = list(
            SurveillanceProfileDrone._base_manager
            .select_related("device", "device__status")
            .filter(profile_id=profile_id, device__isnull=False)
            .only("id", "device_id", "device__unit_id", "device__status__code")
        )
        device_ids = [a.device_id for a in assignments if a.device_id]
        current_start_time = profile.start_time
        if current_start_time and timezone.is_naive(current_start_time):
            current_start_time = timezone.make_aware(current_start_time, timezone.get_current_timezone())

        # 2) Acquire per-drone activation locks to avoid concurrent activations of the same drones
        if device_ids:
            owner = f"{profile_id}:{getattr(self.request, 'id', None) or str(uuid.uuid4())}"
            ok, acquired_lock_keys = _acquire_drone_locks(device_ids, owner=str(owner))
            if not ok:
                # If the lock is held by the same profile, treat as duplicate activation and exit.
                same_profile_lock = False
                for did in sorted(set(device_ids)):
                    try:
                        holder = cache.get(_drone_lock_key(did))
                    except Exception:
                        holder = None
                    if isinstance(holder, str) and holder.startswith(f"{profile_id}:"):
                        same_profile_lock = True
                        break
                if same_profile_lock:
                    logger.info("[SURVEILLANCE] Duplicate activation for profile %s detected (lock already held). Skipping.", profile_id)
                    return

                # Otherwise, another profile is activating one of the drones -> auto-cancel (no retry).
                try:
                    language_code = None
                    profile_lang = (
                        SurveillanceProfile._base_manager
                        .select_related("created_by__language")
                        .filter(id=profile_id)
                        .values_list("created_by__language__code", flat=True)
                        .first()
                    )
                    language_code = _normalize_language_code(profile_lang)
                    reason = _resolve_drone_unavailable_cancel_reason(language_code)
                    SurveillanceProfileService.cancel_profile_task(profile_id, task_type=None)
                    SurveillanceProfileService.cancel_profile(
                        profile_id,
                        reason=reason,
                        cancelled_by=None,
                        use_base_manager=True,
                        extra_metadata={
                            "auto_cancelled_type": "drone_lock_contention",
                            "activation_cancelled_at": timezone.now().isoformat(),
                        },
                    )
                except Exception as cancel_exc:
                    logger.warning("[SURVEILLANCE] Failed to auto-cancel profile %s on lock contention: %s", profile_id, cancel_exc)
                return

        # 3) Determine winner by reservation (cache), with DB fallback for missing/unreliable keys.
        # Winner rule: earlier start_time wins; if equal, earlier check_time (SurveillanceProfileDrone.modified_on) wins.
        if device_ids:
            device_ids_unique = sorted(set(device_ids))
            ttl_seconds = _compute_reservation_ttl_seconds(profile)
            cache_winners: Dict[int, int] = {}
            missing_or_stale: List[int] = []

            for did in device_ids_unique:
                owner_id = _get_reserved_profile_id(did)
                if not owner_id:
                    missing_or_stale.append(did)
                    continue
                if owner_id != profile_id and _is_profile_ended(owner_id):
                    missing_or_stale.append(did)
                    continue
                cache_winners[did] = int(owner_id)

            db_winners = _db_winner_profile_ids_by_device(device_ids_unique) if missing_or_stale else {}

            # Compose final winner per device:
            # - If cache winner exists (active) -> use it
            # - Else use DB winner if available
            # - Else treat as no winner and allow this profile to claim
            final_winners: Dict[int, int] = dict(cache_winners)
            for did in missing_or_stale:
                if did in db_winners:
                    final_winners[did] = int(db_winners[did])

            # If any device is "won" by another active profile -> cancel this profile
            active_owner_ids: set[int] = set()
            for did, winner_pid in final_winners.items():
                if winner_pid and winner_pid != profile_id and not _is_profile_ended(winner_pid):
                    owner_state = _get_profile_state(int(winner_pid)) or {}
                    if _is_preemptable_owner(owner_state, current_start_time):
                        # Do NOT cancel the later-start waiting profile here.
                        # It should be allowed to attempt activation at its own start_time.
                        # We simply ignore its reservation so it doesn't block earlier profiles.
                        continue
                    active_owner_ids.add(int(winner_pid))

            if active_owner_ids:
                try:
                    profile_lang = (
                        SurveillanceProfile._base_manager
                        .select_related("created_by__language")
                        .filter(id=profile_id)
                        .values_list("created_by__language__code", flat=True)
                        .first()
                    )
                    language_code = _normalize_language_code(profile_lang)
                    reason = _resolve_drone_unavailable_cancel_reason(language_code)
                    SurveillanceProfileService.cancel_profile_task(profile_id, task_type=None)
                    SurveillanceProfileService.cancel_profile(
                        profile_id,
                        reason=reason,
                        cancelled_by=None,
                        use_base_manager=True,
                        extra_metadata={
                            "auto_cancelled_type": "drone_reservation_contention",
                            "drone_reservation_owner_profile_ids": sorted(active_owner_ids),
                            "activation_cancelled_at": timezone.now().isoformat(),
                        },
                    )
                except Exception as cancel_exc:
                    logger.warning(
                        "[SURVEILLANCE] Failed to auto-cancel profile %s on active reservation owners: %s",
                        profile_id,
                        cancel_exc,
                    )
                return

            # We are the winner (or no winner exists) for all devices -> claim/refresh reservation for our drones.
            for did in device_ids_unique:
                winner_pid = final_winners.get(did)
                if winner_pid and winner_pid != profile_id:
                    # No reservation change; should not happen here due to active_owner_ids check, but be safe.
                    continue
                try:
                    cache.set(
                        _drone_reservation_key(did),
                        {"profile_id": profile_id, "claimed_at": timezone.now().isoformat()},
                        timeout=ttl_seconds,
                    )
                except Exception:
                    pass

        # 4) DB-level conflict check: prevent starting if any assigned drone is already used by an in-process profile
        if device_ids:
            busy_qs = (
                SurveillanceProfileDrone._base_manager
                .filter(
                    device_id__in=device_ids,
                    profile__actual_end_time__isnull=True,
                    profile__status__code__in=IN_PROCESS_STATUS_CODES,
                )
                .exclude(profile_id=profile_id)
            )
            if busy_qs.exists():
                # Auto-cancel (no retry)
                try:
                    profile_lang = (
                        SurveillanceProfile._base_manager
                        .select_related("created_by__language")
                        .filter(id=profile_id)
                        .values_list("created_by__language__code", flat=True)
                        .first()
                    )
                    language_code = _normalize_language_code(profile_lang)
                    reason = _resolve_drone_unavailable_cancel_reason(language_code)
                    SurveillanceProfileService.cancel_profile_task(profile_id, task_type=None)
                    SurveillanceProfileService.cancel_profile(
                        profile_id,
                        reason=reason,
                        cancelled_by=None,
                        use_base_manager=True,
                        extra_metadata={
                            "auto_cancelled_type": "drone_busy",
                            "activation_cancelled_at": timezone.now().isoformat(),
                        },
                    )
                except Exception as cancel_exc:
                    logger.warning("[SURVEILLANCE] Failed to auto-cancel profile %s on busy drones: %s", profile_id, cancel_exc)
                return

        # 5) Record activation attempt metadata (do NOT set actual_start_time here).
        # actual_start_time must only be set when Flightbird upload succeeds
        # (see SurveillanceProfileService.upload_profile_to_flightbird).
        # Use row lock to ensure consistent metadata update under concurrency.
        with transaction.atomic():
            locked_profile = (
                SurveillanceProfile._base_manager
                .select_for_update(nowait=False, skip_locked=False)
                .select_related("status")
                .get(id=profile_id)
            )

            metadata = locked_profile.metadata or {}
            metadata.setdefault("activation", {})
            metadata["activation"].update(
                {
                    "activation_started_at": timezone.now().isoformat(),
                    "activation_task_id": getattr(self.request, "id", None),
                    "retries": int(getattr(self.request, "retries", 0) or 0),
                }
            )
            locked_profile.metadata = metadata
            locked_profile.save(update_fields=["metadata", "modified_on"])
            profile = locked_profile

        # Upload lên Flightbird
        SurveillanceProfileService.upload_profile_to_flightbird(profile)

        # Cập nhật metadata
        metadata = profile.metadata or {}
        metadata.update({
            "activated_at": timezone.now().isoformat(),
            "activated_by_task": self.request.id,
        })
        profile.metadata = metadata
        profile.save(update_fields=["metadata", "modified_on"])

        logger.info("[SURVEILLANCE] Profile %s đã được kích hoạt thành công", profile.code)

    except Exception as exc:
        logger.exception("[SURVEILLANCE] Error activating profile %s: %s", profile.code, exc)
        raise
    finally:
        if acquired_lock_keys:
            _release_drone_locks(acquired_lock_keys)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def process_surveillance_auto_launch(self) -> None:
    """Periodic processor for delayed surveillance profile activation."""

    try:
        from surveillance.services.surveillance_profile_automation_service import (
            SurveillanceProfileAutomationService,
        )

        now = timezone.now()
        result = SurveillanceProfileAutomationService.process_auto_launch(now=now)

        preflight_count = len(result.get("preflight", [])) if result else 0
        activation_count = len(result.get("activation", [])) if result else 0

        if preflight_count or activation_count:
            logger.info(
                "[SURVEILLANCE][AUTO] Processed preflight=%s activation=%s (task=%s)",
                preflight_count,
                activation_count,
                getattr(self.request, "id", None),
            )

    except Exception as exc:
        logger.exception("[SURVEILLANCE][AUTO] Error processing auto launch task: %s", exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def process_surveillance_recurring_profiles(self) -> None:
    """Generate due recurring surveillance profiles based on repeat schedule."""

    try:
        from surveillance.services.surveillance_profile_service import SurveillanceProfileService

        now = timezone.now()
        created = SurveillanceProfileService.process_due_recurring_profiles(now=now)

        if created:
            logger.info(
                "[SURVEILLANCE][REPEAT] Generated %s recurring profiles (task=%s)",
                created,
                getattr(self.request, "id", None),
            )

    except Exception as exc:
        logger.exception("[SURVEILLANCE][REPEAT] Error processing recurring profiles: %s", exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def check_surveillance_profile_overdue(self, profile_id: int) -> None:
    """Check và hủy profile in_process nếu đã quá hạn kiểm tra."""

    from surveillance.models import SurveillanceProfile
    from surveillance.services.surveillance_profile_service import SurveillanceProfileService

    from django.db import transaction
    
    try:
        # Lock profile để tránh race condition với các task khác hoặc user cancel thủ công
        with transaction.atomic():
            profile = (
                SurveillanceProfile._base_manager
                .select_for_update(nowait=False, skip_locked=False)
                .select_related("status", "created_by__language")
                .get(id=profile_id)
            )
            
            status_code = profile.status.code if profile.status else None
            if status_code not in IN_PROCESS_STATUS_CODES:
                logger.info(
                    "[SURVEILLANCE][OVERDUE] Profile %s đã đổi trạng thái (%s), bỏ qua hủy tự động",
                    profile_id,
                    status_code,
                )
                metadata = dict(profile.metadata or {})
                metadata.pop("overdue_check_eta", None)
                metadata.pop("overdue_check_task_id", None)
                metadata["overdue_check_skipped_status"] = status_code
                profile.metadata = metadata
                profile.save(update_fields=["metadata", "modified_on"])
                return
            
            if profile.actual_end_time:
                logger.info(
                    "[SURVEILLANCE][OVERDUE] Profile %s đã có actual_end_time, bỏ qua hủy tự động",
                    profile_id,
                )
                return

            if not profile.actual_start_time:
                logger.info(
                    "[SURVEILLANCE][OVERDUE] Profile %s chưa có actual_start_time (chưa bắt đầu bay), bỏ qua hủy tự động",
                    profile_id,
                )
                metadata = dict(profile.metadata or {})
                metadata.pop("overdue_check_eta", None)
                metadata.pop("overdue_check_task_id", None)
                metadata["overdue_check_skipped_reason"] = "no_actual_start_time"
                profile.metadata = metadata
                profile.save(update_fields=["metadata", "modified_on"])
                return
            
            overdue_hours = _get_overdue_profile_hours()
            now = timezone.now()
            if now.tzinfo != pytz.UTC:
                now = now.astimezone(pytz.UTC)
            
            actual_start = profile.actual_start_time
            if timezone.is_naive(actual_start):
                actual_start = timezone.make_aware(actual_start, timezone.get_current_timezone())
            if actual_start.tzinfo != pytz.UTC:
                actual_start = actual_start.astimezone(pytz.UTC)
            
            check_time = actual_start + timedelta(hours=overdue_hours)
            if check_time > now:
                logger.info(
                    "[SURVEILLANCE][OVERDUE] Profile %s chưa quá hạn theo config hiện tại (check_time=%s, now=%s, overdue_hours=%.1f), bỏ qua",
                    profile_id,
                    check_time.isoformat(),
                    now.isoformat(),
                    overdue_hours,
                )
                metadata = dict(profile.metadata or {})
                metadata.pop("overdue_check_eta", None)
                metadata.pop("overdue_check_task_id", None)
                metadata["overdue_check_skipped_reason"] = "not_overdue_by_current_config"
                profile.metadata = metadata
                profile.save(update_fields=["metadata", "modified_on"])
                return

            language_code = None
            if profile.created_by and getattr(profile.created_by, "language", None):
                language_code = getattr(profile.created_by.language, "code", None)

            processed_at = timezone.now()
            reason = _resolve_auto_cancel_reason(language_code)
            success, _ = SurveillanceProfileService.cancel_profile(
                profile_id=profile.id,
                reason=reason,
                cancelled_by=None,
                use_base_manager=True,
                extra_metadata={
                    "auto_cancelled_type": "overdue",
                    "overdue_check_processed_at": processed_at.isoformat(),
                    "overdue_check_reason_language": _normalize_language_code(language_code),
                    "overdue_auto_cancelled": True,
                    "overdue_hours_config": overdue_hours,
                },
            )

            if success:
                logger.info(
                    "[SURVEILLANCE][OVERDUE] Profile %s đã bị hủy tự động do quá thời gian (%.1f giờ)",
                    profile.id,
                    overdue_hours,
                )
            else:
                logger.error(
                    "[SURVEILLANCE][OVERDUE] Hủy tự động profile %s thất bại",
                    profile.id,
                )
    except SurveillanceProfile.DoesNotExist:
        logger.warning("[SURVEILLANCE][OVERDUE] Profile %s không tồn tại khi kiểm tra quá hạn", profile_id)
        return
    except Exception as exc:
        logger.exception(
            "[SURVEILLANCE][OVERDUE] Error checking overdue for profile %s: %s",
            profile_id,
            exc,
        )
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def process_surveillance_profile_overdue(self) -> None:
    """
    Task chạy định kỳ để tự động hủy profile quá hạn theo lịch
    Chạy mỗi phút để kiểm tra và hủy ngay khi quá hạn (backup/fallback)
    
    NOTE: close_old_connections() đã được gọi tự động bởi task_prerun signal trong celery.py
    Chỉ cần gọi lại khi retry sau SSL/connection errors
    """
    from surveillance.models import SurveillanceProfile
    from surveillance.services.surveillance_profile_service import SurveillanceProfileService
    from django.db.utils import OperationalError, InterfaceError
    
    # Normalize now về UTC để so sánh nhất quán
    now = timezone.now()
    if now.tzinfo != pytz.UTC:
        now = now.astimezone(pytz.UTC)
    overdue_hours = _get_overdue_profile_hours()
    cancelled_count = 0
    error_count = 0
    max_query_retries = 3
    profiles = None
    for query_attempt in range(max_query_retries):
        try:
            profiles = (
                SurveillanceProfile._base_manager
                .select_related("status", "created_by__language")
                .filter(
                    status__code__in=IN_PROCESS_STATUS_CODES,
                    actual_start_time__isnull=False,  # Chỉ xử lý profile đã bắt đầu bay
                    actual_end_time__isnull=True,
                )
            )
            _ = profiles.first()
            break
        except (OperationalError, InterfaceError) as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['ssl', 'connection', 'eof', 'closed', 'wrong version']):
                if query_attempt < max_query_retries - 1:
                    logger.warning(
                        "[SURVEILLANCE][OVERDUE] SSL/Connection error khi query profiles (attempt %s/%s): %s, retrying...",
                        query_attempt + 1,
                        max_query_retries,
                        str(e)
                    )
                    from django.db import close_old_connections, connections
                    close_old_connections()
                    connections.close_all()
                    continue
                else:
                    logger.error(
                        "[SURVEILLANCE][OVERDUE] SSL/Connection error sau %s attempts khi query profiles: %s",
                        max_query_retries,
                        str(e)
                    )
                    raise
            else:
                raise
    
    if profiles is None:
        logger.error("[SURVEILLANCE][OVERDUE] Không thể query profiles sau %s attempts", max_query_retries)
        return
    
    for profile in profiles.iterator(chunk_size=50):
        try:
            actual_start = profile.actual_start_time
            if not actual_start:
                continue
            
            if timezone.is_naive(actual_start):
                actual_start = timezone.make_aware(actual_start, timezone.get_current_timezone())
            if actual_start.tzinfo != pytz.UTC:
                actual_start = actual_start.astimezone(pytz.UTC)
            
            check_time = actual_start + timedelta(hours=overdue_hours)
            
            if check_time <= now:
                from django.db import transaction
                
                try:
                    with transaction.atomic():
                        # Không dùng select_related với select_for_update vì có thể gây lỗi với nullable relationship
                        # Chỉ dùng skip_locked=True (không dùng nowait=True vì Django không cho phép dùng cả hai)
                        locked_profile = (
                            SurveillanceProfile._base_manager
                            .select_for_update(skip_locked=True)
                            .get(id=profile.id)
                        )
                        # Load relationships sau khi lock để tránh lỗi
                        locked_profile.status
                        if locked_profile.created_by:
                            locked_profile.created_by.language
                        
                        if locked_profile.actual_end_time:
                            continue
                        if locked_profile.status.code not in IN_PROCESS_STATUS_CODES:
                            continue
                        
                        locked_actual_start = locked_profile.actual_start_time
                        if not locked_actual_start:
                            continue
                        
                        if timezone.is_naive(locked_actual_start):
                            locked_actual_start = timezone.make_aware(locked_actual_start, timezone.get_current_timezone())
                        if locked_actual_start.tzinfo != pytz.UTC:
                            locked_actual_start = locked_actual_start.astimezone(pytz.UTC)
                        
                        locked_check_time = locked_actual_start + timedelta(hours=overdue_hours)
                        if locked_check_time > now:
                            continue
                        
                        language_code = None
                        if locked_profile.created_by and getattr(locked_profile.created_by, "language", None):
                            language_code = getattr(locked_profile.created_by.language, "code", None)
                        
                        reason = _resolve_auto_cancel_reason(language_code)
                        success, _ = SurveillanceProfileService.cancel_profile(
                            profile_id=locked_profile.id,
                            reason=reason,
                            cancelled_by=None,
                            use_base_manager=True,
                            extra_metadata={
                                "auto_cancelled_type": "overdue",
                                "overdue_check_processed_at": now.isoformat(),
                                "overdue_check_reason_language": _normalize_language_code(language_code),
                                "overdue_auto_cancelled": True,
                                "overdue_hours_config": overdue_hours,
                                "overdue_check_source": "backup_task",
                            },
                        )
                        
                        if success:
                            cancelled_count += 1
                            logger.info(
                                "[SURVEILLANCE][OVERDUE] Backup task cancelled profile %s (overdue %.1f hours)",
                                locked_profile.id,
                                overdue_hours,
                            )
                        else:
                            error_count += 1
                except SurveillanceProfile.DoesNotExist:
                    continue
                except Exception as lock_exc:
                    # Log exception để debug tại sao profile không được cancel
                    logger.warning(
                        "[SURVEILLANCE][OVERDUE] Exception khi lock profile %s trong backup task: %s",
                        profile.id,
                        str(lock_exc),
                        exc_info=True,
                    )
                    continue
        except Exception as e:
            error_count += 1
            logger.error(
                "[SURVEILLANCE][OVERDUE] Error processing profile %s in backup task: %s",
                profile.id if 'profile' in locals() else 'unknown',
                str(e),
            )
            continue
    
    if cancelled_count > 0 or error_count > 0:
        logger.info(
            "[SURVEILLANCE][OVERDUE] Backup task cancelled %s profiles, errors %s (task=%s)",
            cancelled_count,
            error_count,
            getattr(self.request, "id", None),
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def schedule_surveillance_profile_overdue_checks(self) -> None:
    """Định kỳ 5-10 phút kiểm tra và lên lịch hủy profile quá hạn."""

    from surveillance.models import SurveillanceProfile
    from celery import current_app

    now = timezone.now()
    if now.tzinfo != pytz.UTC:
        now = now.astimezone(pytz.UTC)
    overdue_hours = _get_overdue_profile_hours()

    profiles = (
        SurveillanceProfile._base_manager
        .select_related("status")
        .filter(
            status__code__in=IN_PROCESS_STATUS_CODES,
            actual_start_time__isnull=False,
            actual_end_time__isnull=True,
        )
    )

    scheduled_count = 0
    skipped_count = 0
    
    for profile in profiles:
        actual_start = profile.actual_start_time
        if not actual_start:
            continue
        
        if timezone.is_naive(actual_start):
            actual_start = timezone.make_aware(actual_start, timezone.get_current_timezone())
        if actual_start.tzinfo != pytz.UTC:
            actual_start = actual_start.astimezone(pytz.UTC)
        
        check_time = actual_start + timedelta(hours=overdue_hours)
        metadata = dict(profile.metadata or {})
        scheduled_time = _parse_metadata_datetime(metadata.get("overdue_check_eta"))
        scheduled_task_id = metadata.get("overdue_check_task_id")

        from django.db import transaction
        try:
            with transaction.atomic():
                # Không dùng select_related("status") với select_for_update vì có thể gây lỗi với nullable relationship
                # Chỉ dùng skip_locked=True (không dùng nowait=True vì Django không cho phép dùng cả hai)
                locked_profile = (
                    SurveillanceProfile._base_manager
                    .select_for_update(skip_locked=True)
                    .get(id=profile.id)
                )
                # Load status sau khi lock để tránh lỗi
                locked_profile.status
                
                if locked_profile.actual_end_time:
                    continue
                if locked_profile.status.code not in IN_PROCESS_STATUS_CODES:
                    continue
                
                locked_metadata = dict(locked_profile.metadata or {})
                locked_scheduled_time = _parse_metadata_datetime(locked_metadata.get("overdue_check_eta"))
                locked_scheduled_task_id = locked_metadata.get("overdue_check_task_id")
                
                if locked_scheduled_time and locked_scheduled_task_id:
                    # Nếu scheduled_time đã quá hạn, cần schedule lại
                    if locked_scheduled_time < now:
                        logger.info(
                            "[SURVEILLANCE][OVERDUE] Task cũ %s cho profile %s đã quá hạn (scheduled_for=%s, now=%s), sẽ schedule lại",
                            locked_scheduled_task_id,
                            locked_profile.id,
                            locked_scheduled_time.isoformat(),
                            now.isoformat(),
                        )
                        # Không cần revoke vì task đã quá hạn và không còn trong Celery
                    elif abs((locked_scheduled_time - check_time).total_seconds()) < 1:
                        skipped_count += 1
                        continue
                    else:
                        # Thời gian khác, hủy task cũ và schedule lại
                        try:
                            current_app.control.revoke(locked_scheduled_task_id, terminate=False)
                            logger.info(
                                "[SURVEILLANCE][OVERDUE] Đã hủy task cũ %s cho profile %s do thời gian thay đổi",
                                locked_scheduled_task_id,
                                locked_profile.id,
                            )
                        except Exception as revoke_exc:
                            logger.warning(
                                "[SURVEILLANCE][OVERDUE] Không thể hủy task cũ %s cho profile %s: %s",
                                locked_scheduled_task_id,
                                locked_profile.id,
                                revoke_exc,
                            )

                try:
                    if check_time <= now:
                        # Đã quá hạn, gọi trực tiếp hàm cancel để đảm bảo được xử lý ngay
                        # Thay vì dispatch task có thể không được worker pick up kịp
                        from surveillance.services.surveillance_profile_service import SurveillanceProfileService
                        language_code = None
                        if locked_profile.created_by and getattr(locked_profile.created_by, "language", None):
                            language_code = getattr(locked_profile.created_by.language, "code", None)
                        processed_at = timezone.now()
                        reason = _resolve_auto_cancel_reason(language_code)
                        success, _ = SurveillanceProfileService.cancel_profile(
                            profile_id=locked_profile.id,
                            reason=reason,
                            cancelled_by=None,
                            use_base_manager=True,
                            extra_metadata={
                                "auto_cancelled_type": "overdue",
                                "overdue_check_processed_at": processed_at.isoformat(),
                                "overdue_check_reason_language": _normalize_language_code(language_code),
                                "overdue_auto_cancelled": True,
                                "overdue_hours_config": overdue_hours,
                                "overdue_check_source": "scheduler_task",
                            },
                        )
                        if success:
                            logger.info(
                                "[SURVEILLANCE][OVERDUE] Profile %s đã bị hủy tự động do quá hạn (check_time=%s, now=%s, overdue_hours=%.1f)",
                                locked_profile.id,
                                check_time.isoformat(),
                                now.isoformat(),
                                overdue_hours,
                            )
                            # Xóa metadata về overdue check vì đã xử lý xong
                            locked_metadata.pop("overdue_check_eta", None)
                            locked_metadata.pop("overdue_check_task_id", None)
                            locked_metadata.pop("overdue_check_scheduled_at", None)
                            locked_profile.metadata = locked_metadata
                            locked_profile.save(update_fields=["metadata", "modified_on"])
                            scheduled_count += 1
                        else:
                            logger.error(
                                "[SURVEILLANCE][OVERDUE] Không thể hủy tự động profile %s do quá hạn",
                                locked_profile.id,
                            )
                        continue
                    else:
                        # Tính số giây từ bây giờ đến check_time
                        seconds_until = (check_time - now).total_seconds()
                        # Expires sau check_time 1 giờ để đảm bảo task không bị expire trước khi chạy
                        expires_time = check_time + timedelta(hours=1)
                        # Priority cao (0) cho task auto cancel để được xử lý trước
                        async_result = check_surveillance_profile_overdue.apply_async(
                            args=[locked_profile.id],
                            eta=check_time,
                            expires=expires_time,
                            priority=0,  # Priority cao nhất để được xử lý trước các task khác
                        )
                        
                        # Verify task đã được schedule thành công
                        try:
                            from celery.result import AsyncResult
                            verify_result = AsyncResult(async_result.id, app=current_app)
                            if verify_result.state:
                                logger.info(
                                    "[SURVEILLANCE][OVERDUE] Profile %s lên lịch kiểm tra lúc %s (task_id=%s, expires=%s, state=%s, seconds_until=%.1f)",
                                    locked_profile.id,
                                    check_time.isoformat(),
                                    async_result.id,
                                    expires_time.isoformat(),
                                    verify_result.state,
                                    seconds_until,
                                )
                            else:
                                logger.warning(
                                    "[SURVEILLANCE][OVERDUE] Profile %s task %s được schedule nhưng không có state trong Celery",
                                    locked_profile.id,
                                    async_result.id,
                                )
                        except Exception as verify_exc:
                            logger.warning(
                                "[SURVEILLANCE][OVERDUE] Không thể verify task %s sau khi schedule: %s",
                                async_result.id,
                                verify_exc,
                            )
                except Exception as exc:
                    logger.exception(
                        "[SURVEILLANCE][OVERDUE] Không thể lên lịch kiểm tra profile %s: %s",
                        locked_profile.id,
                        exc,
                    )
                    continue

                locked_metadata.update({
                    "overdue_check_eta": check_time.isoformat(),
                    "overdue_check_task_id": async_result.id,
                    "overdue_check_scheduled_at": now.isoformat(),
                    "overdue_hours_config": overdue_hours,
                })
                locked_profile.metadata = locked_metadata
                locked_profile.save(update_fields=["metadata", "modified_on"])
                scheduled_count += 1
        except SurveillanceProfile.DoesNotExist:
            continue
        except Exception as lock_exc:
            logger.debug(
                "[SURVEILLANCE][OVERDUE] Profile %s đang bị lock, bỏ qua schedule (có thể đang được xử lý bởi process khác)",
                profile.id,
            )
            continue
    
    if scheduled_count > 0 or skipped_count > 0:
        logger.info(
            "[SURVEILLANCE][OVERDUE] Đã xử lý %s profiles (scheduled=%s, skipped=%s, overdue_hours=%.1f)",
            scheduled_count + skipped_count,
            scheduled_count,
            skipped_count,
            overdue_hours,
        )




def _process_import_routes_in_thread(
    name: str,
    purpose_id: int,
    route_ids: list,
    user_id: int,
    import_task_id: str,
    altitude: float = 150.0,
    takeoff_altitude: Optional[float] = None,
    altitude_separation: Optional[float] = None,
    survey_angle: float = 0.0,
    frontal_overlap: float = 70.0,
    side_overlap: float = 70.0,
    entry_location: int = 1,
    cruise_speed: Optional[float] = None,
    hover_speed: float = 5.0,
    log_collection: bool = False,
    video_recording: bool = False,
    video_analysis: bool = False,
    note: Optional[str] = None,
    spacing: Optional[float] = None,
    trigger_distance: Optional[float] = None,
    turnaround_distance: float = 60.96,
    hover_and_capture: bool = False,
    refly_90_degrees: bool = False,
    camera_trigger_in_turnaround: bool = False,
    action_commands: Optional[list] = None,
    total_distance: Optional[float] = None,
    estimated_time: Optional[float] = None,
):
    """
    Process import routes to mission in background thread
    Updates TaskStatus để FE có thể poll status qua API
    """
    from surveillance.services.survey_mission_service import SurveyMissionService
    from common.utils import get_waypoint_speed
    from task_status.models import TaskStatus
    from task_status.services.task_status_service import TaskStatusService
    from core.user.models import CoreUser
    from common.constant import MESSAGE_ENUM, get_message
    
    try:
        logger.info(f"🔄 Starting import routes to mission processing for task {import_task_id}")
        
        # Get user
        user = CoreUser.objects.get(id=user_id)
        
        # Update status to processing
        processing_message = get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_IMPORT_STARTED)
        TaskStatusService.update_status(
            import_task_id,
            status=TaskStatus.Status.PROCESSING,
            message=processing_message,
            action='survey_mission_import_routes',
            task_channel=f'survey_mission_{user.username}',
            trigger_source='survey.mission.import_routes',
            progress=10.0,
        )
        
        # Gọi service method
        success, result = SurveyMissionService.import_routes_to_mission(
            name=name,
            purpose_id=purpose_id,
            route_ids=route_ids,
            altitude=altitude,
            takeoff_altitude=takeoff_altitude,
            altitude_separation=altitude_separation,
            survey_angle=survey_angle,
            frontal_overlap=frontal_overlap,
            side_overlap=side_overlap,
            entry_location=entry_location,
            cruise_speed=cruise_speed if cruise_speed is not None else get_waypoint_speed(),
            hover_speed=hover_speed,
            log_collection=log_collection,
            video_recording=video_recording,
            video_analysis=video_analysis,
            note=note,
            spacing=spacing,
            trigger_distance=trigger_distance,
            turnaround_distance=turnaround_distance,
            hover_and_capture=hover_and_capture,
            refly_90_degrees=refly_90_degrees,
            camera_trigger_in_turnaround=camera_trigger_in_turnaround,
            action_commands=action_commands,
            total_distance=total_distance,
            estimated_time=estimated_time,
            created_by_user=user,
            group_id=user.userprofilelink.group.id if user and user.userprofilelink and user.userprofilelink.group else None,
        )
        
        if not success:
            error_msg = result if isinstance(result, str) else "Failed to create mission"
            logger.error(f"❌ Import routes to mission failed: {error_msg}")
            
            TaskStatusService.update_status(
                import_task_id,
                status=TaskStatus.Status.FAILED,
                message=error_msg,
                progress=0.0,
                error_code='import_failed',
                error_details={'error': error_msg},
            )
            return
        
        logger.info(f"✅ Import routes to mission completed - Task ID: {import_task_id}, Mission ID: {result.id}")
        
        success_message = get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_CREATED)
        TaskStatusService.update_status(
            import_task_id,
            status=TaskStatus.Status.SUCCESS,
            message=success_message,
            progress=100.0,
            data={
                'mission_id': result.id,
                'mission_name': result.name,
            },
            related_model='surveillance.SurveyMission',
            related_object_id=str(result.id),
        )
        
    except Exception as e:
        logger.exception(f"❌ Error processing import routes to mission for task {import_task_id}: {e}")
        
        try:
            user = CoreUser.objects.get(id=user_id)
            error_message = f"{get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED)}: {str(e)}"
            TaskStatusService.update_status(
                import_task_id,
                status=TaskStatus.Status.FAILED,
                message=error_message,
                progress=0.0,
                error_code='import_error',
                error_details={'error': str(e)},
            )
        except Exception as update_error:
            logger.error(f"❌ Error updating task status: {update_error}")


def _process_download_video_analysis_reports_in_thread(
    profile_id: int,
    download_task_id: str,
    user_id: int,
):
    """
    Build PDF reports (WeasyPrint) for all VideoAnalysis records of a profile, zip them,
    upload to MinIO, and update TaskStatus for client-side polling.
    """
    import os
    import re
    import tempfile
    import zipfile
    from datetime import datetime, timedelta
    from typing import Any, Optional

    from django.db import close_old_connections

    from common.constant import MESSAGE_ENUM, get_message
    from config import settings
    from core.user.models import CoreUser
    import pytz
    from core.user.models import UserSettings
    from report_template.utils import (
        generate_pdf_report_template,
        generate_pdf_report_template_chromium,
        get_cached_korean_font_config,
    )
    from stream_monitors.utils.minio_client import minio_client
    from surveillance.services.surveillance_profile_service import SurveillanceProfileService
    from surveillance.schemas.schemas_djantic_out import VideoAnalysisOutSchema
    from surveillance.services.video_analysis_report_service import VideoAnalysisReportService
    from surveillance.models import VideoAnalysis as VideoAnalysisModel
    from task_status.models import TaskStatus
    from task_status.services.task_status_service import TaskStatusService

    temp_zip_path = None

    try:
        close_old_connections()

        user = CoreUser.objects.get(id=user_id)

        # Reuse font config once for the whole job
        font_config = get_cached_korean_font_config("fonts")

        def _get_system_settings_dict() -> dict:
            """
            Fetch system settings from AdminConfig (best-effort).
            Expected structure: AdminConfig(name="System").settings is a dict.
            """
            try:
                from core.configuration.models import AdminConfig
                config = (
                    AdminConfig.objects.filter(name="System", is_active=True)
                    .values("settings")
                    .first()
                )
                settings_data = config["settings"] if config and isinstance(config.get("settings"), dict) else {}

                # Some deployments store default formats under a nested key (e.g. `system_default_formats`)
                # while keeping other system settings at top-level. Prefer the nested dict if present.
                for key in ("system_default_formats", "systemDefaultFormats", "default_formats", "defaultFormats"):
                    nested = settings_data.get(key)
                    if isinstance(nested, dict) and (nested.get("_options") or nested.get("date_format") or nested.get("time_format")):
                        return nested

                return settings_data
            except Exception:
                return {}

        def _resolve_timezone_for_user() -> pytz.BaseTzInfo:
            # 1) User timezone
            try:
                tz_obj = getattr(user, "timezone", None)
                tz_code = getattr(tz_obj, "code", None) or getattr(tz_obj, "name", None)
                if isinstance(tz_code, str) and tz_code.strip():
                    return pytz.timezone(tz_code.strip())
            except Exception:
                pass
            # 2) System timezone (AdminConfig)
            settings_data = _get_system_settings_dict()
            tz_value = settings_data.get("timezone") or settings_data.get("time_zone") or settings_data.get("tz")
            if isinstance(tz_value, str) and tz_value.strip():
                try:
                    return pytz.timezone(tz_value.strip())
                except Exception:
                    pass
            # 3) Fallback
            return pytz.timezone("Asia/Ho_Chi_Minh")

        def _resolve_format_strings_for_user() -> tuple[str, str]:
            """
            Return (date_format_str, time_format_str) from user settings if any,
            else fall back to AdminConfig System settings, else defaults.
            """
            def _looks_like_date_tokens(fmt: str) -> bool:
                # detect both strftime and FE-style tokens
                return bool(
                    re.search(r"(%Y|%y|%m|%d|\bYYYY\b|\bYY\b|\bMM\b|\bDD\b)", fmt)
                )

            def _looks_like_time_tokens(fmt: str) -> bool:
                # detect both strftime and FE-style tokens
                return bool(
                    re.search(r"(%H|%I|%M|%S|%f|%p|%z|\bHH\b|\bhh\b|\bmm\b|\bss\b|\bSSS\b|\bA\b|\ba\b|\bZ\b)", fmt)
                )

            def _resolve_format_string_from_options(settings_dict: dict, kind: str, code: Any) -> Optional[str]:
                """
                System settings often store just a code/label (e.g. "DD/MM/YYYY", "24").
                If `_options` is present, resolve to the real `format_string` (strftime).
                """
                try:
                    if not isinstance(settings_dict, dict):
                        return None
                    options = settings_dict.get("_options")
                    if not isinstance(options, dict):
                        return None
                    if not isinstance(code, str) or not code.strip():
                        return None
                    code_s = code.strip()
                    key = "date_format" if kind == "date" else "time_format"
                    entries = options.get(key)
                    if not isinstance(entries, list):
                        return None
                    for item in entries:
                        if not isinstance(item, dict):
                            continue
                        item_code = item.get("code") or item.get("name")
                        if isinstance(item_code, str) and item_code.strip() == code_s:
                            fmt = item.get("format_string") or item.get("formatString")
                            if isinstance(fmt, str) and fmt.strip():
                                return fmt.strip()
                    return None
                except Exception:
                    return None

            def _normalize_system_format_value(settings_dict: dict, val: Any, kind: str) -> Optional[str]:
                """
                AdminConfig(System).settings may store either:
                - a real format string (strftime or moment/dayjs tokens), OR
                - a UI label like "DD/MM/YYYY" or "24"/"12" (time mode), OR
                - a dict/object. Best-effort normalize to a format string.
                """
                try:
                    # 1) If `_options` exists, prefer its `format_string` mapping by code.
                    fmt_from_options = _resolve_format_string_from_options(settings_dict, kind, val)
                    if isinstance(fmt_from_options, str) and fmt_from_options.strip():
                        return fmt_from_options.strip()

                    if isinstance(val, dict):
                        # Common shapes: {"format_string": "..."} or {"value": "..."} or {"code": "..."}
                        for k in ("format_string", "formatString", "value", "code", "name", "label"):
                            v = val.get(k)
                            if isinstance(v, str) and v.strip():
                                val = v.strip()
                                break
                        else:
                            return None
                    if not isinstance(val, str):
                        return None
                    s = val.strip()
                    if not s:
                        return None

                    if kind == "date":
                        # Typical UI labels
                        if s in ("DD/MM/YYYY", "DD-MM-YYYY", "MM/DD/YYYY", "YYYY-MM-DD", "YYYY/MM/DD"):
                            return s
                        return s

                    if kind == "time":
                        # UI dropdown often stores "24"/"12" meaning time mode, not a full time format.
                        if s == "24":
                            return "HH:mm"
                        if s == "12":
                            return "hh:mm A"
                        if s == "24_full":
                            return "HH:mm:ss"
                        if s == "12_full":
                            return "hh:mm:ss A"
                        # Already a format string (HH:mm, HH:mm:ss, etc) or strftime.
                        return s
                except Exception:
                    return None

            # Defaults
            date_format_str = "%Y-%m-%d"
            time_format_str = "%H:%M:%S"

            # 1) UserSettings
            try:
                user_settings = None
                if hasattr(user, "user_settings"):
                    user_settings = user.user_settings
                elif hasattr(user, "usersettings"):
                    user_settings = user.usersettings
                else:
                    user_settings = UserSettings.objects.select_related("date_format", "time_format").filter(user=user).first()

                if user_settings:
                    df = getattr(user_settings, "date_format", None)
                    tf = getattr(user_settings, "time_format", None)
                    df_str = getattr(df, "format_string", None) if df else None
                    tf_str = getattr(tf, "format_string", None) if tf else None
                    if isinstance(df_str, str) and df_str.strip():
                        # Guard: ignore misconfigured "date_format" that accidentally includes time tokens
                        s = df_str.strip()
                        if not (_looks_like_date_tokens(s) and _looks_like_time_tokens(s)):
                            date_format_str = s
                    if isinstance(tf_str, str) and tf_str.strip():
                        # Guard: ignore misconfigured "time_format" that accidentally includes date tokens
                        s = tf_str.strip()
                        if not _looks_like_date_tokens(s):
                            time_format_str = s
            except Exception:
                pass

            # 2) AdminConfig System settings
            settings_data = _get_system_settings_dict()
            sys_df_raw = settings_data.get("date_format") or settings_data.get("dateFormat")
            sys_tf_raw = settings_data.get("time_format") or settings_data.get("timeFormat")
            sys_df = _normalize_system_format_value(settings_data, sys_df_raw, "date")
            sys_tf = _normalize_system_format_value(settings_data, sys_tf_raw, "time")
            if isinstance(sys_df, str) and sys_df.strip() and date_format_str == "%Y-%m-%d":
                date_format_str = sys_df.strip()
            if isinstance(sys_tf, str) and sys_tf.strip() and time_format_str == "%H:%M:%S":
                time_format_str = sys_tf.strip()

            return date_format_str, time_format_str

        user_tz = _resolve_timezone_for_user()
        date_fmt, time_fmt = _resolve_format_strings_for_user()

        # Language for localizing month names / AM-PM in formatted output (avoid relying on OS locales)
        try:
            _lang_code = getattr(getattr(user, "language", None), "code", None) or "en"
        except Exception:
            _lang_code = "en"
        _lang_code = str(_lang_code).lower()
        if _lang_code == "kr":
            _lang_code = "ko"

        _MONTHS_EN_FULL = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        _MONTHS_EN_ABBR = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        _MONTH_LOCALIZATION = {
            # Korean: "12월"
            "ko": {
                "full": {m: f"{i}월" for i, m in enumerate(_MONTHS_EN_FULL, start=1)},
                "abbr": {m: f"{i}월" for i, m in enumerate(_MONTHS_EN_ABBR, start=1)},
            },
            # Thai full month names + common abbreviations
            "th": {
                "full": {
                    "January": "มกราคม",
                    "February": "กุมภาพันธ์",
                    "March": "มีนาคม",
                    "April": "เมษายน",
                    "May": "พฤษภาคม",
                    "June": "มิถุนายน",
                    "July": "กรกฎาคม",
                    "August": "สิงหาคม",
                    "September": "กันยายน",
                    "October": "ตุลาคม",
                    "November": "พฤศจิกายน",
                    "December": "ธันวาคม",
                },
                "abbr": {
                    "Jan": "ม.ค.",
                    "Feb": "ก.พ.",
                    "Mar": "มี.ค.",
                    "Apr": "เม.ย.",
                    "May": "พ.ค.",
                    "Jun": "มิ.ย.",
                    "Jul": "ก.ค.",
                    "Aug": "ส.ค.",
                    "Sep": "ก.ย.",
                    "Oct": "ต.ค.",
                    "Nov": "พ.ย.",
                    "Dec": "ธ.ค.",
                },
            },
            # Vietnamese: "Tháng 12", "Th12"
            "vi": {
                "full": {m: f"Tháng {i}" for i, m in enumerate(_MONTHS_EN_FULL, start=1)},
                "abbr": {m: f"Th{i}" for i, m in enumerate(_MONTHS_EN_ABBR, start=1)},
            },
        }

        _AMPM_LOCALIZATION = {
            "ko": {"AM": "오전", "PM": "오후"},
            "vi": {"AM": "SA", "PM": "CH"},
            # Thai commonly keeps AM/PM as-is; add mapping later if desired
        }

        _MONTH_FULL_RE = re.compile(r"\b(" + "|".join(_MONTHS_EN_FULL) + r")\b")
        _MONTH_ABBR_RE = re.compile(r"\b(" + "|".join(_MONTHS_EN_ABBR) + r")\b")
        _AMPM_RE = re.compile(r"\b(AM|PM)\b")

        def _localize_formatted_datetime(text: str) -> str:
            """
            Post-process a formatted datetime string to localize month names and AM/PM.
            This keeps formatting fast and avoids OS locale dependencies.
            """
            if not isinstance(text, str) or not text:
                return text
            if _lang_code == "en":
                return text

            month_map = _MONTH_LOCALIZATION.get(_lang_code)
            if month_map:
                try:
                    text = _MONTH_FULL_RE.sub(lambda m: month_map["full"].get(m.group(1), m.group(1)), text)
                    text = _MONTH_ABBR_RE.sub(lambda m: month_map["abbr"].get(m.group(1), m.group(1)), text)
                except Exception:
                    pass

            ampm_map = _AMPM_LOCALIZATION.get(_lang_code)
            if ampm_map:
                try:
                    text = _AMPM_RE.sub(lambda m: ampm_map.get(m.group(1), m.group(1)), text)
                except Exception:
                    pass
            return text

        def _to_strftime(fmt: str) -> str:
            """
            Convert common FE-style date/time formats (moment/dayjs) to Python strftime.
            If fmt already looks like strftime (contains %), return as-is.
            """
            if not isinstance(fmt, str):
                return "%Y-%m-%d"
            s = fmt.strip()
            if not s:
                return "%Y-%m-%d"
            if "%" in s:
                return s

            # Replace tokens (longest first)
            # Note: 'MM' (month) vs 'mm' (minute) must be handled carefully.
            mapping = [
                ("YYYY", "%Y"),
                ("YY", "%y"),
                ("DD", "%d"),
                ("HH", "%H"),
                ("hh", "%I"),
                ("mm", "%M"),
                ("ss", "%S"),
                ("SSS", "%f"),  # will be trimmed to 3 digits later
                ("A", "%p"),
                ("a", "%p"),
                ("Z", "%z"),
            ]
            # Month token must be replaced after minutes token check; use placeholder.
            s = s.replace("MM", "__MONTH__")
            for k, v in mapping:
                s = s.replace(k, v)
            s = s.replace("__MONTH__", "%m")
            return s

        def _has_date_tokens(fmt: str) -> bool:
            if not isinstance(fmt, str):
                return False
            return any(
                tok in fmt
                for tok in (
                    "%Y",
                    "%y",
                    "%m",
                    "%d",
                    "YYYY",
                    "YY",
                    "MM",
                    "DD",
                )
            )

        def _has_time_tokens(fmt: str) -> bool:
            if not isinstance(fmt, str):
                return False
            return any(
                tok in fmt
                for tok in (
                    "%H",
                    "%I",
                    "%M",
                    "%S",
                    "%f",
                    "%p",
                    "%z",
                    "HH",
                    "hh",
                    "mm",
                    "ss",
                    "SSS",
                    "A",
                    "a",
                    "Z",
                )
            )

        def _normalize_date_format_for_display(fmt: str) -> str:
            """
            Ensure date format is date-only.
            Guard against misconfigured formats that include time tokens (e.g. ISO datetime).
            """
            if not isinstance(fmt, str):
                return "%Y-%m-%d"
            s = fmt.strip()
            if not s:
                return "%Y-%m-%d"
            # If date format accidentally contains time tokens, try to take the date part only.
            if _has_date_tokens(s) and _has_time_tokens(s):
                # Common ISO-like: YYYY-MM-DDTHH:mm:ss...
                if "T" in s:
                    s = s.split("T", 1)[0].strip()
                else:
                    # Best-effort: take first whitespace-separated segment
                    s = s.split(" ", 1)[0].strip()
            return s or "%Y-%m-%d"

        def _normalize_time_format_for_display(fmt: str) -> str:
            """
            Ensure time format is time-only.
            Guard against misconfigured formats that include date tokens (e.g. 'YYYY-MM-DDTHH:mm:ss.SSSZ').
            For valid time-only formats, keep as-is (respect user settings).
            """
            if not isinstance(fmt, str):
                return "HH:mm:ss"
            s = fmt.strip()
            if not s:
                return "HH:mm:ss"

            # If time format contains date tokens, it's likely a full datetime format; derive a time-only format.
            if _has_date_tokens(s):
                is_12h = ("hh" in s) or ("%I" in s)
                has_seconds = ("ss" in s) or ("%S" in s)
                if is_12h:
                    return "hh:mm:ss A" if has_seconds else "hh:mm A"
                return "HH:mm:ss" if has_seconds else "HH:mm"

            # Valid time-only format -> keep as-is (respect user/system settings)
            return s

        def _format_dt_value(value: Any) -> Any:
            """
            Format datetime/date strings/objects using user settings or system(AdminConfig).
            Returns string for datetime/date, otherwise original.
            """
            if value is None:
                return value

            # Try parse ISO string
            if isinstance(value, str):
                s = value.strip()
                if not s:
                    return value
                parsed_dt: Optional[datetime] = None

                # 1) dateutil (best effort)
                try:
                    from dateutil import parser as date_parser
                    parsed_dt = date_parser.parse(s)
                except Exception:
                    parsed_dt = None

                # 2) Normalize common ISO variants and use stdlib fromisoformat
                if parsed_dt is None:
                    try:
                        iso = s
                        # Zulu
                        if iso.endswith("Z"):
                            iso = iso[:-1] + "+00:00"
                        # +0900 -> +09:00
                        iso = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", iso)
                        parsed_dt = datetime.fromisoformat(iso)
                    except Exception:
                        parsed_dt = None

                # 3) Regex fallback for strings like 2025-12-26T19:31:50.000+0900
                if parsed_dt is None:
                    m = re.match(
                        r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})[T\s]"
                        r"(?P<h>\d{2}):(?P<mi>\d{2}):(?P<s>\d{2})"
                        r"(?:\.(?P<ms>\d{1,6}))?"
                        r"(?P<tz>Z|[+-]\d{2}:?\d{2})?$",
                        s,
                    )
                    if m:
                        try:
                            y = int(m.group("y"))
                            mo = int(m.group("m"))
                            d = int(m.group("d"))
                            hh = int(m.group("h"))
                            mm_ = int(m.group("mi"))
                            ss_ = int(m.group("s"))
                            micros = 0
                            if m.group("ms"):
                                ms_raw = m.group("ms")
                                ms_padded = (ms_raw + "000000")[:6]
                                micros = int(ms_padded)
                            parsed_dt = datetime(y, mo, d, hh, mm_, ss_, micros)

                            tz_raw = m.group("tz")
                            if tz_raw and tz_raw != "Z":
                                tz_norm = tz_raw.replace(":", "")
                                sign = 1 if tz_norm[0] == "+" else -1
                                off_h = int(tz_norm[1:3])
                                off_m = int(tz_norm[3:5])
                                parsed_dt = pytz.FixedOffset(sign * (off_h * 60 + off_m)).localize(parsed_dt)
                            elif tz_raw == "Z":
                                parsed_dt = pytz.UTC.localize(parsed_dt)
                        except Exception:
                            parsed_dt = None

                if parsed_dt is None:
                    return value

                value = parsed_dt

            if isinstance(value, datetime):
                dt = value
                try:
                    if dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)
                    localized = dt.astimezone(user_tz)
                    # Decide whether to combine formats or use a single full datetime format.
                    # NOTE: Some deployments store a full datetime format in `time_format` by mistake.
                    # We normalize to date-only + time-only formats for human-friendly PDF display.
                    df_src = _normalize_date_format_for_display(date_fmt)
                    tf_src = _normalize_time_format_for_display(time_fmt)
                    df = _to_strftime(df_src)
                    tf = _to_strftime(tf_src)

                    dt_fmt = f"{df} {tf}".strip()
                    src_for_ms = f"{df_src} {tf_src}"

                    formatted = localized.strftime(dt_fmt)
                    formatted = _localize_formatted_datetime(formatted)
                    # If original format requested milliseconds (SSS), trim %f (microseconds) to 3 digits.
                    if isinstance(src_for_ms, str) and "SSS" in src_for_ms and "%f" in dt_fmt:
                        formatted = re.sub(r"(\d{6})", lambda m: m.group(1)[:3], formatted, count=1)
                    return formatted
                except Exception:
                    return str(value)

            # Keep date as date-only
            try:
                from datetime import date as date_cls
                if isinstance(value, date_cls) and not isinstance(value, datetime):
                    try:
                        return value.strftime(_to_strftime(date_fmt))
                    except Exception:
                        return str(value)
            except Exception:
                pass

            return value

        # --- Performance: detect datetime/date fields from model once per job ---
        try:
            from django.db.models import DateField, DateTimeField

            VIDEO_ANALYSIS_DATETIME_FIELDS = {
                f.name
                for f in getattr(VideoAnalysisModel, "_meta", None).fields
                if isinstance(f, (DateTimeField, DateField))
            }
        except Exception:
            VIDEO_ANALYSIS_DATETIME_FIELDS = {"created_at", "updated_at", "start_time", "end_time"}

        # --- Also handle flattened related fields (e.g. profile_device__scheduled_start_time) ---
        DATETIME_FIELD_HINTS = {
            "created_on",
            "modified_on",
            "created_at",
            "updated_at",
            "start_time",
            "end_time",
            "scheduled_start_time",
            "estimated_end_time",
            "approved_at",
            "rejected_at",
            "cancel_time",
            "completion_time",
            "repeat_until_date",
        }

        def _is_datetime_like_key(key: str) -> bool:
            """
            Detect date/datetime keys from flattened schema output by looking at last segment.
            Examples: profile_device__scheduled_start_time -> scheduled_start_time
            """
            if not key:
                return False
            last_raw = str(key).split("__")[-1]
            last = last_raw.lower()
            if last in DATETIME_FIELD_HINTS:
                return True
            # Also support common camelCase keys coming from some serializers (e.g. createdAt, startTime).
            # Normalize by stripping non-alphanumerics so "created_at" and "createdAt" both become "createdat".
            try:
                last_compact = re.sub(r"[^a-z0-9]+", "", last)
            except Exception:
                last_compact = last.replace("_", "")

            # Pre-compute / compare against compact hints (avoid over-matching generic "...at" like "format").
            # Note: we intentionally do NOT match bare "...at" because it's too ambiguous.
            if last_compact in {re.sub(r"[^a-z0-9]+", "", h) for h in DATETIME_FIELD_HINTS}:
                return True

            # Suffix heuristics
            if last.endswith(("_time", "_at", "_date")):
                return True
            if last_compact.endswith(("time", "date", "timestamp", "datetime")):
                return True
            if last_compact in {"createdat", "updatedat", "approvedat", "rejectedat", "cancelledat", "canceltime"}:
                return True
            return False

        # --- Optional: format datetime-like keys inside analysis JSON (bounded / key-based) ---
        ANALYSIS_DATETIME_KEYS = {
            "time",
            "timestamp",
            "datetime",
            "created_at",
            "updated_at",
            "detected_at",
            "start_time",
            "end_time",
        }
        _ANALYSIS_KEY_HINT_RE = re.compile(r"(time|date|timestamp)$", re.IGNORECASE)

        def _format_analysis_datetime_fields(obj: Any) -> Any:
            """
            Traverse only analysis payload and format fields that likely represent datetime/date.
            Avoids regex-scanning every string in the whole payload.
            """
            if obj is None:
                return obj
            if isinstance(obj, list):
                return [_format_analysis_datetime_fields(v) for v in obj]
            if isinstance(obj, dict):
                for k, v in list(obj.items()):
                    k_str = str(k)
                    lk = k_str.lower()
                    if lk in ANALYSIS_DATETIME_KEYS or _ANALYSIS_KEY_HINT_RE.search(lk):
                        obj[k] = _format_dt_value(v)
                    else:
                        obj[k] = _format_analysis_datetime_fields(v)
                return obj
            return obj

        def _format_nested_datetime_fields(obj: Any, depth: int = 0, max_depth: int = 4) -> Any:
            """
            Traverse nested dict/list payloads and format values where the KEY looks like datetime/date.
            This is used for nested objects like profile_device/camera/... in `detail`.
            Bounded by max_depth for safety/performance.
            """
            if obj is None:
                return obj
            if depth >= max_depth:
                return obj
            if isinstance(obj, list):
                return [_format_nested_datetime_fields(v, depth=depth + 1, max_depth=max_depth) for v in obj]
            if isinstance(obj, dict):
                for k, v in list(obj.items()):
                    k_str = str(k)
                    if _is_datetime_like_key(k_str):
                        obj[k] = _format_dt_value(v)
                    else:
                        obj[k] = _format_nested_datetime_fields(v, depth=depth + 1, max_depth=max_depth)
                return obj
            return obj

        processing_message = get_message(MESSAGE_ENUM.START_DOWNLOAD_FILE)
        TaskStatusService.update_status(
            download_task_id,
            status=TaskStatus.Status.PROCESSING,
            message=processing_message,
            progress=5.0,
            action="surveillance_profile_download_analysis_pdf",
            task_channel=f"survey_profile_{user.username}",
            trigger_source="surveillance.profile.download_analysis_pdf",
            related_model="surveillance.SurveillanceProfile",
            related_object_id=str(profile_id),
        )

        qs = SurveillanceProfileService.get_video_analyses_for_profile(profile_id)
        total = qs.count()
        if total <= 0:
            TaskStatusService.update_status(
                download_task_id,
                status=TaskStatus.Status.FAILED,
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                progress=0.0,
                error_code="no_analysis",
                error_details={"profile_id": profile_id},
            )
            return

        # Create temp ZIP
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_zip_path = temp_zip.name
        temp_zip.close()

        failed_ids = []

        with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, video_analysis in enumerate(qs.iterator(chunk_size=200), start=1):
                try:
                    # Build detail dict similar to GET /video-analysis/{id}
                    detail = VideoAnalysisOutSchema.from_queryset(video_analysis, many=False)
                    if video_analysis.analysis_path:
                        analysis_json = minio_client.get_json(video_analysis.analysis_path)
                        detail["analysis"] = analysis_json if analysis_json is not None else []
                    detail["purpose"] = "Surveillance" if user.language.code == "en" else "정찰" if user.language.code == "ko" else "การสอดส่อง" if user.language.code == "th" else "Surveillance"
                    if not detail.get("profile_device"):
                        detail["purpose"] = "Other" if user.language.code == "en" else "기타" if user.language.code == "ko" else "อื่นๆ" if user.language.code == "th" else "Other"
                    # Pass language for PDF i18n to mirror FE template labels.
                    try:
                        detail["_lang"] = getattr(getattr(user, "language", None), "code", None) or user.language.code
                    except Exception:
                        detail["_lang"] = detail.get("_lang") or "en"
                    # FE uses `profile_device__created_on` for "Profile Date"
                    try:
                        if getattr(video_analysis, "profile_device", None) and getattr(video_analysis.profile_device, "created_on", None):
                            detail["profile_device__created_on"] = _format_dt_value(video_analysis.profile_device.created_on)
                    except Exception:
                        # Best-effort: do not fail report generation due to missing/invalid profile_device datetime.
                        detail["profile_device__created_on"] = detail.get("profile_device__created_on")
                    detail["capture_altitude"] = video_analysis.profile_device.profile.mission.get_measurement('altitude').get_formatted_value() if video_analysis.profile_device.profile.mission.get_measurement('altitude') else None
                    detail["takeoff_altitude"] = video_analysis.profile_device.profile.mission.get_measurement('takeoff_altitude').get_formatted_value() if video_analysis.profile_device.profile.mission.get_measurement('takeoff_altitude') else None
                    detail["altitude_separation"] = video_analysis.profile_device.profile.mission.get_measurement('altitude_separation').get_formatted_value() if video_analysis.profile_device.profile.mission.get_measurement('altitude_separation') else None
                    detail["landing_time"] = video_analysis.profile_device.profile.actual_end_time
                    # Format datetime/date fields for VideoAnalysis payload (model-driven, fast)
                    for key in VIDEO_ANALYSIS_DATETIME_FIELDS:
                        if key in detail:
                            detail[key] = _format_dt_value(detail.get(key))

                    # Format flattened related fields (bounded, O(n) scan)
                    for k, v in list(detail.items()):
                        if _is_datetime_like_key(str(k)):
                            try:
                                detail[k] = _format_dt_value(v)
                            except Exception:
                                # Best-effort: do not fail the whole report due to one malformed datetime-ish field.
                                detail[k] = v

                    # Format datetime/date-like keys inside analysis JSON (bounded traversal)
                    analysis_payload = detail.get("analysis")
                    if isinstance(analysis_payload, (list, dict)):
                        detail["analysis"] = _format_analysis_datetime_fields(analysis_payload)

                    # Format datetime-like keys inside other nested objects (bounded traversal)
                    for k, v in list(detail.items()):
                        if k == "analysis":
                            continue
                        if isinstance(v, (dict, list)):
                            detail[k] = _format_nested_datetime_fields(v)
                    # Also cache video thumbnail boxes if they exist as detected images (handled in analysis loop),
                    # and cache any top-level video_path is kept as link (not downloaded).

                    html_report = VideoAnalysisReportService.build_video_analysis_report_html(
                        detail,
                        lang=detail.get("_lang"),
                    )
                    pdf_bytes = generate_pdf_report_template_chromium(html_report)
                    if pdf_bytes is None:
                        pdf_file = generate_pdf_report_template(
                            html_report,
                            font_config=font_config,
                            jpeg_quality=95,
                        )
                        try:
                            pdf_bytes = pdf_file.read()
                        finally:
                            try:
                                pdf_path = pdf_file.name
                                pdf_file.close()
                                if pdf_path and os.path.exists(pdf_path):
                                    os.unlink(pdf_path)
                            except Exception:
                                pass

                    video_file_name = "report"
                    if detail.get("video_path"):
                        video_file_name = str(detail["video_path"]).split("/")[-1] or "report"
                    safe_video = re.sub(r'[<>:"/\\|?*]', "_", video_file_name)
                    filename = f"DataAnalysis_{safe_video}_{video_analysis.id}.pdf"
                    zf.writestr(filename, pdf_bytes)

                    progress = 5.0 + (idx / total) * 85.0  # 5 → 90
                    TaskStatusService.update_status(
                        download_task_id,
                        status=TaskStatus.Status.PROCESSING,
                        message=f"Generating PDF {idx}/{total}",
                        progress=float(progress),
                        record_count=idx,
                    )
                except Exception as exc:
                    logger.exception(
                        "[DOWNLOAD][ANALYSIS] Failed to build PDF for video_analysis=%s: %s",
                        getattr(video_analysis, "id", None),
                        exc,
                    )
                    failed_ids.append(getattr(video_analysis, "id", None))
                    continue

        # Upload ZIP to MinIO (reuse pattern from MediaDataDownloadService)
        TaskStatusService.update_status(
            download_task_id,
            status=TaskStatus.Status.PROCESSING,
            message="Uploading ZIP file to storage...",
            progress=90.0,
        )

        download_bucket = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
        download_prefix = "downloads/"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"analysis_profile_{profile_id}_{timestamp}.zip"
        minio_path = f"{download_prefix}{zip_filename}"

        minio_client.client.fput_object(
            download_bucket,
            minio_path,
            temp_zip_path,
            content_type="application/zip",
        )

        download_url = minio_client.client.presigned_get_object(
            download_bucket,
            minio_path,
            expires=timedelta(hours=1),
        )
        file_url_relative = f"/{download_bucket}/{minio_path}"

        done_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS)
        TaskStatusService.update_status(
            download_task_id,
            status=TaskStatus.Status.SUCCESS,
            message=done_message,
            progress=100.0,
            data={
                "profile_id": profile_id,
                "total_items": total,
                "failed_items": len([x for x in failed_ids if x is not None]),
                "failed_ids": [x for x in failed_ids if x is not None],
                "minio_path": minio_path,
            },
            download_url=download_url,
            file_url=file_url_relative,
            filename=zip_filename,
            file_id=download_task_id,
            record_count=total,
        )

    except Exception as exc:
        logger.exception(
            "[DOWNLOAD][ANALYSIS] Error processing download task %s: %s",
            download_task_id,
            exc,
        )
        try:
            TaskStatusService.update_status(
                download_task_id,
                status=TaskStatus.Status.FAILED,
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                progress=0.0,
                error_code="download_error",
                error_details={"error": str(exc)},
            )
        except Exception:
            pass
    finally:
        try:
            close_old_connections()
        except Exception:
            pass
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.unlink(temp_zip_path)
            except Exception:
                pass


def _process_import_routes_simple_in_thread(
    name: str,
    purpose_id: int,
    route_ids: list,
    user_id: int,
    import_task_id: str,
    altitude: float = 150.0,
    takeoff_altitude: Optional[float] = None,
    altitude_separation: Optional[float] = None,
    cruise_speed: Optional[float] = None,
    hover_speed: float = 5.0,
    log_collection: bool = False,
    video_recording: bool = False,
    video_analysis: bool = False,
    note: Optional[str] = None,
    total_distance: Optional[float] = None,
    estimated_time: Optional[float] = None,
):
    """
    Process import routes to mission simple in background thread
    Updates TaskStatus để FE có thể poll status qua API
    """
    from surveillance.services.survey_mission_service import SurveyMissionService
    from common.utils import get_waypoint_speed
    from task_status.models import TaskStatus
    from task_status.services.task_status_service import TaskStatusService
    from core.user.models import CoreUser
    from common.constant import MESSAGE_ENUM, get_message
    
    try:
        logger.info(f"🔄 Starting import routes to mission simple processing for task {import_task_id}")
        
        # Get user
        user = CoreUser.objects.get(id=user_id)
        
        # Update status to processing
        processing_message = get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_IMPORT_STARTED)
        TaskStatusService.update_status(
            import_task_id,
            status=TaskStatus.Status.PROCESSING,
            message=processing_message,
            action='survey_mission_import_routes_simple',
            task_channel=f'survey_mission_{user.username}',
            trigger_source='survey.mission.import_routes_simple',
            progress=10.0,
        )
        
        # Gọi service method
        success, result = SurveyMissionService.import_routes_to_mission_simple(
            name=name,
            purpose_id=purpose_id,
            route_ids=route_ids,
            altitude=altitude,
            takeoff_altitude=takeoff_altitude,
            altitude_separation=altitude_separation,
            cruise_speed=cruise_speed if cruise_speed is not None else get_waypoint_speed(),
            hover_speed=hover_speed,
            log_collection=log_collection,
            video_recording=video_recording,
            video_analysis=video_analysis,
            note=note,
            total_distance=total_distance,
            estimated_time=estimated_time,
            created_by_user=user
        )
        
        if not success:
            error_msg = result if isinstance(result, str) else "Failed to create mission"
            logger.error(f"❌ Import routes to mission simple failed: {error_msg}")
            
            TaskStatusService.update_status(
                import_task_id,
                status=TaskStatus.Status.FAILED,
                message=error_msg,
                progress=0.0,
                error_code='import_failed',
                error_details={'error': error_msg},
            )
            return
        
        logger.info(f"✅ Import routes to mission simple completed - Task ID: {import_task_id}, Mission ID: {result.id}")
        
        success_message = get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_CREATED)
        TaskStatusService.update_status(
            import_task_id,
            status=TaskStatus.Status.SUCCESS,
            message=success_message,
            progress=100.0,
            data={
                'mission_id': result.id,
                'mission_name': result.name,
            },
            related_model='surveillance.SurveyMission',
            related_object_id=str(result.id),
        )
        
    except Exception as e:
        logger.exception(f"❌ Error processing import routes to mission simple for task {import_task_id}: {e}")
        
        try:
            user = CoreUser.objects.get(id=user_id)
            error_message = f"{get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED)}: {str(e)}"
            TaskStatusService.update_status(
                import_task_id,
                status=TaskStatus.Status.FAILED,
                message=error_message,
                progress=0.0,
                error_code='import_error',
                error_details={'error': str(e)},
            )
        except Exception as update_error:
            logger.error(f"❌ Error updating task status: {update_error}")
