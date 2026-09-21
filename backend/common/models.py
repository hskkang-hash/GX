# -*- coding: utf-8 -*-
"""P-224 — **칸을 못 더하는 표에 표식을 남기는 곁표 한 개.**

한 문장
-------
    남의 표(dj-core)의 행을 **고치지 않고**, 우리 표에 「저 행은 우리가 심은 것」을
    적어 둔다. 청구의 셈은 그 적어 둔 것만 읽는다.

왜 이 파일이 생겼나
-------------------
대표가 「청구 표식 칸을 **더해라**」라고 정했는데, 청구가 세는 표 넷 중 **셋이
dj-core**(`user.CoreUser` · `file_management.UserMediaFile` ·
`core.apikey_account.APIKey`)라 **칸을 못 더한다**(§0.4 금지구역 — 그 앱은
site-packages 안에 있고, 고쳐도 패키지를 올리면 사라진다). 세종 P-224 가 그래서
**곁표**로 갈랐다. 우리 카메라 표(`stream_monitors.StreamMonitor`)만 칸으로 간다.

    ★ 이 판단의 선례는 `common/migrations/0001_audit_logger_name_index.py` 다 —
      **표는 빌리고, 코드는 안 만진다.** 거기서는 남의 표에 인덱스만 얹었고,
      여기서는 남의 표를 **가리키기만** 한다.

왜 `common` 앱인가
------------------
읽는 자리가 `common/billing_marks.py` 하나이고, 그 파일을 **커널 셋**(K1·K2·K6)이
쓴다. `verify_layers` 허용표가 `backend/kernels/** → common.**` 이니 표식이 사는
자리도 L1 이어야 한다. 앱(`apps/dsm`)에 두면 커널이 앱을 보게 된다.

★ **이 표는 삭제하지 않는다** (P-222 · 삭제는 대표 자리).
  씨앗 행을 지우는 것이 아니라 **청구에서 빼는** 것이고, 그래서 여기 쌓이는 것은
  「무엇을 뺐는가」의 장부다. 장부가 줄면 왜 뺐는지 답할 수 없다.
"""
from django.db import models


class BillingMark(models.Model):
    """한 행이 **우리가 심은 것**임을 적어 두는 한 줄.

    ★ **왜 ContentType 이 아닌가.** `django.contrib.contenttypes` 의 FK 를 쓰면
      dj-core 표가 지워질 때 이 장부도 CASCADE 로 **같이 사라진다.** 그러면 「왜 이
      행이 청구에서 빠졌나」에 답할 근거가 행과 함께 없어진다. 여기 적는 것은
      **관계가 아니라 사실**이고, 사실은 가리키는 것이 사라져도 남아야 한다.
      (그리고 `model_label` 은 사람이 읽을 수 있다 — 숫자 id 는 못 읽는다.)

    ★ **`object_id` 는 문자열이다.** 세는 표의 pk 가 정수일 수도 uuid 일 수도 있다.
      읽는 쪽(`billing_marks.marked_unbillable_ids`)이 그 표의 pk 형으로 되돌린다.
    """

    #: `app_label.modelname` 소문자 — `model._meta.label_lower` 그대로.
    model_label = models.CharField(
        max_length=100, db_index=True,
        help_text="표 이름(app_label.modelname · 소문자). 가리키는 표가 사라져도 "
                  "이 줄은 남는다 — 여기 적는 것은 관계가 아니라 사실이다.")
    #: 그 표의 pk 를 문자열로.
    object_id = models.CharField(max_length=64)
    #: `live` · `probe` · `seed` · `drill`. 낱말의 정본은 `common/billing_marks.py`
    #: (그리고 그중 둘은 `common/probe_marker.py`)다 — 여기서 choices 로 못박지
    #: 않는 이유가 그것이다. 두 벌이 되면 한쪽을 고칠 때 다른 쪽은 안 고쳐진다.
    data_source = models.CharField(max_length=32, db_index=True)
    #: **왜 뺐는가.** 빈 사유는 면제와 구별되지 않는다 — 다음 사람이 코드를 안 읽고
    #: 답할 수 있어야 한다.
    reason = models.CharField(max_length=500, blank=True, default="")
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "common"
        db_table = "common_billing_mark"
        #: 한 행에 표식은 하나다. 둘이면 어느 쪽이 정본인지 아무도 못 답한다.
        unique_together = (("model_label", "object_id"),)
        verbose_name = "청구 표식"
        verbose_name_plural = "청구 표식"

    def __str__(self) -> str:
        return f"{self.model_label}#{self.object_id} = {self.data_source}"
