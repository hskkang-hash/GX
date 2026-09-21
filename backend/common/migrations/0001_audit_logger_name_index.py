"""감사 표의 `logger_name` 인덱스 — **DB 에만 있던 것을 마이그레이션으로 내린다** (P-205).

무엇을 막나
-----------
턴 X 에 대표 결정으로 이 인덱스를 **운영 DB 에 직접** 넣고 다시 쟀다:

    전 : Parallel Seq Scan · Rows Removed by Filter 47,203(워커마다) · Execution Time 42.227 ms
    후 : Index Only Scan   · 54행 직행 · 버린 행 0                    · Execution Time  0.242 ms

그런데 **마이그레이션에는 없었다.** 그러면 스테이징·재생성 DB 는 인덱스 **없이** 태어나고,
`CoreLoggingMiddleware` 가 요청마다 감사 한 행을 쓰는 이 표는 거기서 **날마다 느려진다** —
「지금 DB 에서는 빠르다」가 「다른 데서도 빠르다」를 뜻하지 않는다. 이 파일이 그 간격이다.

왜 `common` 앱인가 — **표는 빌리고, 코드는 안 만진다**
------------------------------------------------------
`logger_auditlogs` 는 dj-core(`core.logger.AuditLogs`)의 표이고 **§0.4 금지구역**이다.
site-packages 안의 그 앱에 마이그레이션을 끼워 넣는 것은 남의 자산을 고치는 일이고,
패키지를 올리면 사라진다. 그래서 **우리 앱의 마이그레이션**이 **남의 표에 인덱스만** 만든다.
dj-core 파일은 한 자도 안 고친다 — `dependencies` 로 그 앱의 첫 마이그레이션을 **읽을 뿐**이다.
(`logger_name` · `create_datetime` 두 칸은 `logger.0001_initial` 에서 함께 생긴다.)

세 가지가 일부러 이렇게 되어 있다
---------------------------------
① `atomic = False` — `CREATE INDEX CONCURRENTLY` 는 **트랜잭션 안에서 못 돈다**
   (`CREATE INDEX CONCURRENTLY cannot run inside a transaction block`).
   Django 는 마이그레이션마다 트랜잭션을 여니, 이 한 벌만 안 열게 한다.
   CONCURRENTLY 를 쓰는 이유는 감사 표가 **쓰기 길목**이라 잠그면 전 요청이 멈추기 때문이다.
② `IF NOT EXISTS` — **이미 인덱스가 있는 DB(지금 개발 DB)에서 no-op** 이어야 한다.
   없으면 이 마이그레이션은 있는 DB 에서 `relation already exists` 로 죽고,
   그 죽음은 「스키마가 어긋났다」처럼 보이지만 실은 **두 번 적용한 것**이다.
③ 역방향 `DROP INDEX CONCURRENTLY IF EXISTS` — 되돌릴 수 있는 변경만 둔다.
   `IF EXISTS` 는 인덱스 없이 태어난 DB 를 되감을 때를 위한 것이다.

⚠ 실패한 CONCURRENTLY 는 **INVALID 인덱스를 남긴다**(플래너가 안 쓰고 자리만 먹는다).
  `IF NOT EXISTS` 는 이름만 보므로 그 찌꺼기도 「있다」로 읽는다. 이 인덱스가 있는데도
  Seq Scan 이 나오면 먼저 `pg_index.indisvalid` 를 본다 — 그때는 `DROP INDEX` 뒤 재적용이다.
"""
from django.db import migrations

INDEX_NAME = "gx_audit_logger_dt_idx"
TABLE_NAME = "logger_auditlogs"

FORWARD_SQL = f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME}
    ON {TABLE_NAME} (logger_name, create_datetime);
"""

REVERSE_SQL = f"""
DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME};
"""


class Migration(migrations.Migration):
    # CONCURRENTLY 는 트랜잭션 밖에서만 돈다 (위 ①).
    atomic = False

    # `--fake-initial` 이 이 마이그레이션을 「이미 적용됐다」로 건너뛰지 못하게 한다.
    # 건너뛰면 django_migrations 에는 줄이 서고 인덱스는 안 생긴다 — 거짓 초록이다.
    initial = False

    dependencies = [
        # dj-core 의 표가 먼저 있어야 인덱스를 얹는다. **읽기 의존일 뿐** 그 앱을 고치지 않는다.
        ("logger", "0001_initial"),
    ]

    operations = [
        # 모델 상태는 건드리지 않는다(`state_operations` 없음) — dj-core 모델 선언은 우리 것이 아니다.
        # 그래서 `makemigrations --check` 가 이 인덱스를 「모델에 없는 변경」으로 다시 만들라고 하지 않는다.
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
