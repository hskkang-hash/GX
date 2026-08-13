"""
Signals cho Terminal models để tự động schedule activation tasks
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

logger = logging.getLogger(__name__)


@receiver(post_save, sender='terminals.TerminalException')
def schedule_terminal_on_exception_change(sender, instance, created, **kwargs):
    """
    Signal để schedule activation tasks ngay khi exception được tạo hoặc cập nhật
    Giải quyết vấn đề: nếu user tạo exception sau khi task định kỳ đã chạy,
    exception sẽ được schedule ngay lập tức thay vì phải đợi đến lần chạy tiếp theo
    """
    try:
        from terminals.tasks import schedule_terminal_activation_for_terminal
        
        # Chỉ schedule nếu terminal tồn tại và không phải TEMP
        terminal = instance.terminal
        if terminal and not terminal.terminal_types.filter(code="TEMP").exists():
            # Schedule sau khi transaction commit để đảm bảo dữ liệu đã được lưu
            def schedule_after_commit():
                try:
                    # Schedule cho 7 ngày tiếp theo để đảm bảo bao phủ đủ
                    schedule_terminal_activation_for_terminal.delay(terminal.id, days_ahead=7)
                    logger.info(
                        "[TERMINAL][SIGNAL] Scheduled activation tasks for terminal %s (ID: %s) "
                        "after exception %s (ID: %s) was %s",
                        terminal.name,
                        terminal.id,
                        instance.exception_date,
                        instance.id,
                        "created" if created else "updated"
                    )
                except Exception as e:
                    logger.error(
                        "[TERMINAL][SIGNAL] Error scheduling terminal %s (ID: %s) after exception change: %s",
                        terminal.name,
                        terminal.id,
                        str(e)
                    )
            
            transaction.on_commit(schedule_after_commit)
    except Exception as e:
        logger.error(
            "[TERMINAL][SIGNAL] Error in schedule_terminal_on_exception_change: %s",
            str(e)
        )


@receiver(post_delete, sender='terminals.TerminalException')
def schedule_terminal_on_exception_delete(sender, instance, **kwargs):
    """
    Signal để schedule activation tasks ngay khi exception bị xóa
    """
    try:
        from terminals.tasks import schedule_terminal_activation_for_terminal
        
        # Lấy terminal_id trước khi instance bị xóa
        terminal_id = instance.terminal_id
        terminal = instance.terminal
        
        if terminal and not terminal.terminal_types.filter(code="TEMP").exists():
            # Schedule sau khi transaction commit
            def schedule_after_commit():
                try:
                    schedule_terminal_activation_for_terminal.delay(terminal_id, days_ahead=7)
                    logger.info(
                        "[TERMINAL][SIGNAL] Scheduled activation tasks for terminal %s (ID: %s) "
                        "after exception %s (ID: %s) was deleted",
                        terminal.name,
                        terminal_id,
                        instance.exception_date,
                        instance.id
                    )
                except Exception as e:
                    logger.error(
                        "[TERMINAL][SIGNAL] Error scheduling terminal %s (ID: %s) after exception delete: %s",
                        terminal.name if terminal else terminal_id,
                        terminal_id,
                        str(e)
                    )
            
            transaction.on_commit(schedule_after_commit)
    except Exception as e:
        logger.error(
            "[TERMINAL][SIGNAL] Error in schedule_terminal_on_exception_delete: %s",
            str(e)
        )


@receiver(post_save, sender='terminals.TerminalOperatingTime')
def schedule_terminal_on_operating_time_change(sender, instance, created, **kwargs):
    """
    Signal để schedule activation tasks ngay khi operating time được tạo hoặc cập nhật
    """
    try:
        from terminals.tasks import schedule_terminal_activation_for_terminal
        
        terminal = instance.terminal
        if terminal and not terminal.terminal_types.filter(code="TEMP").exists():
            def schedule_after_commit():
                try:
                    schedule_terminal_activation_for_terminal.delay(terminal.id, days_ahead=7)
                    logger.info(
                        "[TERMINAL][SIGNAL] Scheduled activation tasks for terminal %s (ID: %s) "
                        "after operating time %s (ID: %s) was %s",
                        terminal.name,
                        terminal.id,
                        instance.day_of_week.name if hasattr(instance, 'day_of_week') else 'N/A',
                        instance.id,
                        "created" if created else "updated"
                    )
                except Exception as e:
                    logger.error(
                        "[TERMINAL][SIGNAL] Error scheduling terminal %s (ID: %s) after operating time change: %s",
                        terminal.name,
                        terminal.id,
                        str(e)
                    )
            
            transaction.on_commit(schedule_after_commit)
    except Exception as e:
        logger.error(
            "[TERMINAL][SIGNAL] Error in schedule_terminal_on_operating_time_change: %s",
            str(e)
        )


@receiver(post_delete, sender='terminals.TerminalOperatingTime')
def schedule_terminal_on_operating_time_delete(sender, instance, **kwargs):
    """
    Signal để schedule activation tasks ngay khi operating time bị xóa
    """
    try:
        from terminals.tasks import schedule_terminal_activation_for_terminal
        
        terminal_id = instance.terminal_id
        terminal = instance.terminal
        
        if terminal and not terminal.terminal_types.filter(code="TEMP").exists():
            def schedule_after_commit():
                try:
                    schedule_terminal_activation_for_terminal.delay(terminal_id, days_ahead=7)
                    logger.info(
                        "[TERMINAL][SIGNAL] Scheduled activation tasks for terminal %s (ID: %s) "
                        "after operating time %s (ID: %s) was deleted",
                        terminal.name,
                        terminal_id,
                        instance.day_of_week.name if hasattr(instance, 'day_of_week') else 'N/A',
                        instance.id
                    )
                except Exception as e:
                    logger.error(
                        "[TERMINAL][SIGNAL] Error scheduling terminal %s (ID: %s) after operating time delete: %s",
                        terminal.name if terminal else terminal_id,
                        terminal_id,
                        str(e)
                    )
            
            transaction.on_commit(schedule_after_commit)
    except Exception as e:
        logger.error(
            "[TERMINAL][SIGNAL] Error in schedule_terminal_on_operating_time_delete: %s",
            str(e)
        )

