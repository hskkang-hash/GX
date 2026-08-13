"""
Utility module for flexible datetime parsing for terminals.
Leverages core.common.search.dynamic_search.flexible_datetime_parser for date/datetime.

Supported formats:
    Date: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, Month DD YYYY, DD Month YYYY, YYYY/MM/DD, YY/MM/DD
    Time: HH:MM, HH:MM AM/PM, HH:MM:SS, HH:MM:SS AM/PM
"""

import re
from datetime import time as dt_time, date, datetime
from typing import Optional, Union

from core.common.search.dynamic_search import flexible_datetime_parser as _core_datetime_parser


def flexible_time_parser(value: Optional[Union[str, dt_time, datetime]]) -> Optional[dt_time]:
    """
    Parse time string với hỗ trợ đa định dạng.
    
    Supported: HH:MM, HH:MM AM/PM, HH:MM:SS, HH:MM:SS AM/PM
    
    Args:
        value: Time string hoặc time/datetime object
        
    Returns:
        datetime.time object hoặc None
    """
    if not value:
        return None
    
    if isinstance(value, dt_time):
        return value
    
    if isinstance(value, datetime):
        return value.time()
    
    if not isinstance(value, str):
        return None
    
    value = value.strip()
    
    # Time-only patterns (reuse logic from dynamic_search.py)
    time_patterns = [
        # 12 hour full: HH:MM:SS AM/PM
        (r'^(\d{1,2}):(\d{1,2}):(\d{1,2})\s*(AM|PM|am|pm|A\.M\.|P\.M\.)$', True, True),
        # 12 hour: HH:MM AM/PM
        (r'^(\d{1,2}):(\d{1,2})\s*(AM|PM|am|pm|A\.M\.|P\.M\.)$', True, False),
        # 24 hour full: HH:MM:SS
        (r'^(\d{1,2}):(\d{1,2}):(\d{1,2})$', False, True),
        # 24 hour: HH:MM
        (r'^(\d{1,2}):(\d{1,2})$', False, False),
    ]
    
    for pattern, is_12h, has_seconds in time_patterns:
        match = re.match(pattern, value, re.IGNORECASE)
        if match:
            groups = match.groups()
            hour = int(groups[0])
            minute = int(groups[1])
            second = 0
            
            if is_12h:
                if has_seconds:
                    second = int(groups[2])
                    am_pm = groups[3].upper().replace('.', '')
                else:
                    am_pm = groups[2].upper().replace('.', '')
                
                # Validate 12-hour format
                if hour < 1 or hour > 12:
                    return None
                
                # Convert to 24 hour
                if am_pm == 'PM' and hour != 12:
                    hour += 12
                elif am_pm == 'AM' and hour == 12:
                    hour = 0
            else:
                if has_seconds:
                    second = int(groups[2])
            
            # Validate ranges
            if hour > 23 or minute > 59 or second > 59:
                return None
            
            return dt_time(hour, minute, second)
    
    return None


def flexible_date_parser(value: Optional[Union[str, date, datetime]]) -> Optional[date]:
    """
    Parse date string với hỗ trợ đa định dạng.
    Sử dụng core.common.search.dynamic_search.flexible_datetime_parser.
    
    Supported: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, Month DD YYYY, DD Month YYYY, YYYY/MM/DD, YY/MM/DD
    
    Args:
        value: Date string hoặc date/datetime object
        
    Returns:
        datetime.date object hoặc None
    """
    if not value:
        return None
    
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    
    if isinstance(value, datetime):
        return value.date()
    
    if not isinstance(value, str):
        return None
    
    # Use core parser
    parsed = _core_datetime_parser(value)
    
    if isinstance(parsed, datetime):
        return parsed.date()
    elif isinstance(parsed, date):
        return parsed
    
    return None


def flexible_datetime_parser(value: Optional[Union[str, datetime, date]]) -> Optional[datetime]:
    """
    Parse datetime string với hỗ trợ đa định dạng.
    Wrapper của core.common.search.dynamic_search.flexible_datetime_parser.
    
    Args:
        value: Datetime string hoặc datetime/date object
        
    Returns:
        datetime object hoặc None
    """
    if not value:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, date):
        return datetime.combine(value, dt_time.min)
    
    if not isinstance(value, str):
        return None
    
    parsed = _core_datetime_parser(value)
    
    if isinstance(parsed, datetime):
        return parsed
    elif isinstance(parsed, date):
        return datetime.combine(parsed, dt_time.min)
    
    return None
