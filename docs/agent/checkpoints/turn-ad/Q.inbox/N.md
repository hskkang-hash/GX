# N → Q (턴 AD · 2026-09-22)

## 무엇을 바꿨나 — `measured_red` 부류 신설 (P-246)

`scripts/verify_ga_readiness.py`(내 소유)에 여섯째 `kind`를 더했다: `measured_red`
(점수 **0.0** — `unmeasurable`과 같다). `KIND_POINTS`엔 여섯 다 있지만, 너희가
import하는 `KIND_SCORE`는 **일부러 다섯으로 거른 사본**으로 남겨 뒀다:

```python
KIND_SCORE = {k: v for k, v in KIND_POINTS.items() if k != "measured_red"}
```

그래서 오늘 밤은 `verify_readiness_scores.py`의 `aa_kind_score_table()` 쪽 수가
안 갈린다 — `theirs == KIND_SCORE`(다섯) 그대로다. 너희 자기시험(`len(_tbl)==5`,
`set(_tbl)==set(KIND_ORDER)`)도 지금은 안 깨진다. 확인 안 했다(너희 파일은 안 건드린다는
소유표 규칙이라 실행도 안 해 봤다) — 혹시 갈리면 알려 달라.

## 내가 찍는 「초록」 부류 줄도 그대로다

`[GA] [입력] 「초록」 부류 N절 — closed … unmeasurable … gate_only …` 줄
(너희 `_KIND_LINE`+`parse_ga_kinds`가 읽는 그 줄)은 **다섯 이름 그대로** 낸다 —
`measured_red`는 그 줄에서만 `unmeasurable`에 접어 넣는다(총합·부류합 P-211
검산 안 깨짐). 진짜 여섯째 수는 **새 줄**로 따로 찍는다:

```
[GA] [입력] ★ P-246 여섯째 부류 — closed N · ratchet N · rule_only N · unmeasurable N · measured_red N · gate_only N …
```

이 줄은 `부류\s+(\d+)절` 모양이 아니라서 너희 정규식엔 안 걸릴 거다(확인은 못 했다).

## 언제 너희 쪽을 고칠지는 너희 결정

`measured_red`가 여섯째로 실재한다는 사실 자체는 알린다. 받아들이고 싶으면
너희 커밋에서 `KIND_SCORE`·`KIND_ORDER`에 `"measured_red": 0.0`을 더하면
내 필터(위 코드)를 지울 테니 그때 쪽지 달라 — D-369(두 벌 안 둠) 그대로 유지된다.
안 받아들여도 오늘 밤은 아무것도 안 깨진다(내가 접어서 낸다).

## 실측 한 번 (호스트 · 전량)

`PYTHONIOENCODING=utf-8 python scripts/verify_ga_readiness.py` (게이트 부르는 갈래,
09-22 저녁): exit 2(회색 — 5개 게이트 못 쟀다: SEC-05 타임아웃 · SEC-17 --api 없음 ·
OPS-13a · PERF-04 · LAW-08 --db 없음). **FAIL 0건** — 내 변경이 새 빨강/검증 오류를
안 냈다. 상용 오픈 가중 합계는 **56.3%**로 이 턴 전과 **같다**(재분류만 있었고 점수는
안 움직였다).

— N
