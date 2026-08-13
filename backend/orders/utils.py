import datetime
from datetime import datetime, timedelta
from django.utils import timezone


def get_order_message(terminal, lang, receive_days, is_expired):
    if is_expired:
        if lang == "en":
            return f"""We're sorry, your order has exceeded the storage period and has been processed accordingly. We sincerely apologize for the inconvenience."""
        elif lang == "ko":
            return f"""주문이 저장 기간을 초과하여 적절하게 처리되었습니다. 불편을 드려 죄송합니다."""
    else:
        if lang == "en":
            return f"""Your order has not been received for an extended period, so it has been moved to our warehouse at {terminal}.\n Please pick up your package at this address from Monday to Friday, between 8:00 AM and 5:00 PM.\n If the package is not collected within {receive_days} days from the date it was returned to the warehouse, we will proceed to handle it according to our company's policy."""
        elif lang == "ko":
            return f"""주문이 오랜 기간 동안 수신되지 않았으므로 우리 창고에 있습니다 {terminal}.\n 월요일부터 금요일까지 오전 8시부터 오후 5시까지 패키지를 수령하세요.\n 패키지가 반환된 날로부터 {receive_days}일 내에 수령되지 않으면 회사의 정책에 따라 처리합니다."""


def is_date_outdated(order_date: str, days_available: int, language: str) -> bool:
    """
    Check if a date is outdated based on the number of available days.

    Args:
        order_date (datetime): The date to check
        days_available (int): Number of days the order is valid for

    Returns:
        bool: True if the date is outdated, False otherwise
    """
    if order_date is None:
        return False
    if isinstance(order_date, str):
        order_date = datetime.strptime(
            order_date, "%m-%d-%Y %H:%M:%S" if language == "en" else "%Y-%m-%d %H:%M:%S"
        )
    # Get current time in timezone-aware format
    today = timezone.now()

    # If order_date is naive, make it timezone-aware
    if timezone.is_naive(order_date):
        order_date = timezone.make_aware(order_date)

    expiration_date = order_date + timedelta(days=days_available)
    return today > expiration_date
