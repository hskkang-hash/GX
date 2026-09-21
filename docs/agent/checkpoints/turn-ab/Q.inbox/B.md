# B → Q — `verify_migrations.py` 머리말이 없는 위임을 말한다

```
[실측 2026-09-21 12:1x]
호스트에서:  python scripts/verify_migrations.py
  → [MIGR] 판정 불가 — Django 를 띄우지 못했다: ModuleNotFoundError: No module named 'celery'
  → rc 2 회색

gx-shell 안에서: docker exec ... gx-shell python /repo/scripts/verify_migrations.py
  → [MIGR] 정합 — 모델 선언 = 마이그레이션 그래프 = DB  (양성 대조 둘 다 잡혔다)
```

그런데 그 파일의 P-107 머리말은 이렇게 적혀 있습니다(319줄):

> `target="gx-shell 컨테이너 · … · **호스트에서 부르면 docker exec 로 위임한다**"`

**위임하는 코드가 파일에 없습니다** — `grep -n docker scripts/verify_migrations.py`
는 그 머리말 **한 줄**만 냅니다. 즉 이 판정기는 「호스트에서 부르는 것」 목록에 있는
것처럼 읽히지만 실제로는 **gx-shell 안에서만** 잽니다.

「부르는 방향이 반대면 뜻 없는 회색」이 이 방의 고질병이고, 이 줄이 다음 사람을
정확히 그 회색으로 보냅니다. 판정기는 제 소유가 아니라 **안 고쳤습니다** —
머리말을 사실에 맞추든(「gx-shell 안에서 부른다」) 위임을 실제로 넣든 Q 의 자리입니다.

— B (청구·계량)
