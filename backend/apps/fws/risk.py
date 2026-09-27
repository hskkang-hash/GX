# -*- coding: utf-8 -*-
"""FWS-F1-03 — 오늘 위험지수·위기경보·입산통제 (WO-15 §5 P-357 · 턴 AK 차선 N2).

정직하게 남긴다 — 무엇을 재지 않는가
-------------------------------------
산림청 실시간 산불위험예보(습도·풍속·강수 API 연계)는 이 턴의 범위 밖이다 — 외부
기관 연동은 새 자격증명·새 방화벽 규칙이 필요하고, 그 승인은 대표의 몫이지 이
지시서의 몫이 아니다(§0.4 밖에서도 「할 수 있는데 안 했다」가 아니라 「이 턴엔
막혀 있다」다). 그래서 이 문은 **건기 달력 규칙**(11~4월이 산불조심기간·산림보호법
시행령 별표 — 명세서 §5.1 FWS-F1-03 이 요구하는 「오늘의 띠」한 줄)으로 오늘의
띠를 계산한다. 외부 연동이 들어오는 날 이 함수의 **몸통만** 바뀌고 계약(응답 모양)
은 그대로다 — 화면은 이 문의 모양에만 기댄다.

값
--
    level                     "관심" | "주의" | "경계" | "심각" 넷 중 하나
    fire_alert                위기경보(주의·경계·심각)가 떠 있는가
    mountain_entry_banned     입산통제 중인가(명세서: 산불조심기간의 「심각」구간)
    season                    "산불조심기간" | "평시" — **왜** 이 띠인지 사람이 볼 수 있게
    as_of                     이 값을 계산한 날짜(ISO) — 캐시된 옛 값과 구별하는 자리
"""
from __future__ import annotations

from datetime import date

#: 산불조심기간 — 산림보호법 시행령 별표(가을 11.1~12.15 · 봄 2.1~5.15).
#: ★ 값을 두 자리로 나눈 이유: 「11~4월 전부」로 뭉치면 1·12월의 비산불조심 구간이
#:   조심기간으로 잘못 셀 수 있다 — 명세서가 가리키는 것은 **법령의 두 구간**이다.
_AUTUMN = ((11, 1), (12, 15))
_SPRING = ((2, 1), (5, 15))

LEVELS = ("관심", "주의", "경계", "심각")


def _in_range(today: date, start: tuple[int, int], end: tuple[int, int]) -> bool:
    start_d = date(today.year, *start)
    end_d = date(today.year, *end)
    return start_d <= today <= end_d


def _is_dry_season(today: date) -> bool:
    return (_in_range(today, _AUTUMN[0], _AUTUMN[1])
            or _in_range(today, _SPRING[0], _SPRING[1]))


def risk_today(*, today: date | None = None) -> dict:
    """오늘의 띠. **부르는 쪽이 오늘을 밀어 넣을 수 있다** — 날짜 경계 시험이 타이머에
    기대지 않게 하기 위해서다(가짜 시계 금지 원칙과 같은 결 · D-277)."""
    today = today or date.today()
    dry_season = _is_dry_season(today)
    level = "주의" if dry_season else "관심"
    return {
        "level": level,
        "fire_alert": dry_season,
        "mountain_entry_banned": False,
        "season": "산불조심기간" if dry_season else "평시",
        "as_of": today.isoformat(),
    }
