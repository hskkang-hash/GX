# -*- coding: utf-8 -*-
"""P-411 — **감사 행 ↔ 테넌트(group) 곁표 하나** (턴 AO 차선 O).

왜 이 표가 서나
---------------
FWS 의 몇 절(F3-18·U5-02·U5-03)이 `logger.AuditLogs`(dj-core 소유 · §0.4
금지구역)에 감사 한 줄로 기록하는데, 그 표에는 테넌트(group) 칸이 없어
통계·목록이 "이 감사 행을 쓴 사람 자신의 것만"으로 좁아 있었다(반쪽). 감사표는
고칠 수 없으므로(§0.4) `common.models.BillingMark`(`0002_p224_billing_mark`)와
같은 판단으로 **우리 표 하나**에 "그 감사 행 id 는 이 group 것"이라는 사실만
별도로 적는다 — 자세한 이유는 `common/models.py::AuditScope` 머리말.

★ 이 마이그레이션은 아무 행도 안 건드린다. 표 하나를 세울 뿐이다 — 씨앗을 심는
  일은 없다(BillingMark 의 seed 마이그레이션과 달리, 이 표는 **앞으로 쓰는
  행부터** 채워진다 — 과거 감사 행에 소급하지 않는다. 과거 행은 여전히
  "본인 것만" 셈으로 남는다 — 새로운 손실이 아니라 이전과 같은 반쪽이다).

`initial = False` 인 이유
-------------------------
`--fake-initial` 이 이 마이그레이션을 건너뛰지 못하게 한다(`0001_audit_logger_
name_index`·`0002_p224_billing_mark` 와 같은 줄 · 건너뛰면 표는 안 생기고
`django_migrations` 에만 줄이 서는 거짓 초록이 된다).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('common', '0004_p224_seed_account_marks_v_residual'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditScope',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('audit_id', models.PositiveBigIntegerField(db_index=True, help_text='logger.AuditLogs 행의 pk(FK 아님 — dj-core 표가 지워져도 이 표식은 남아야 한다)', unique=True)),
                ('tenant_group_id', models.PositiveIntegerField(db_index=True)),
                ('kind', models.CharField(blank=True, db_index=True, default='', max_length=64)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': '감사 테넌트 곁표',
                'verbose_name_plural': '감사 테넌트 곁표',
                'db_table': 'common_audit_scope',
            },
        ),
    ]
