# P-326 — `AdminConfig('System').settings['frontendUrl']` (2026-09-24 · 턴 S)

## 무엇을 왜

`core/api/v1/auth.py::forgot_password`(dj-core · §0.4 읽기만)가 재설정 링크의 앞머리로
`AdminConfig.objects.filter(name='System').first().settings.get('frontendUrl', 'http://localhost:3001')`
를 읽는다. 칸이 비어 있어 기본값 `http://localhost:3001`(아무도 안 듣는 포트)이 링크에
그대로 실렸다. 값이 아니라 **주소**이고 비밀이 아니다 — 세종 위임 범위 안.

넣은 값은 **대표가 브라우저로 여는 그 주소**(호스트 로그인이 8500 이었다).
스테이징이 오면 같은 칸을 `https://<도메인>` 으로 바꾼다(창 아님).

## 전/후

| | 값 |
|---|---|
| 전 (BEFORE) | 칸 없음 (`AdminConfig.objects.get(name='System').settings.get('frontendUrl')` → `None`) |
| 후 (AFTER) | `http://localhost:8500` |

행: `configuration.AdminConfig` · `name='System'` (이미 있던 행 — `get_or_create` 의
`created=False`, 다른 칸(`cidr`·`domain`·`otp`·`refresh_time`·`security`·`subtitle`·
`time_format`·`timezone`·`ui`·`user`·`validation`)은 건드리지 않았다).

## 넣은 방법

gx-shell 안 `python manage.py shell -c`(세종 위임 · gx-shell 위임 관용구):

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \
  python manage.py shell -c "
from django.apps import apps
AdminConfig = apps.get_model('configuration', 'AdminConfig')
row, created = AdminConfig.objects.get_or_create(name='System', defaults={'settings': {}})
conf = dict(row.settings or {})
conf['frontendUrl'] = 'http://localhost:8500'
row.settings = conf
row.save(update_fields=['settings'])
"
```

실행 로그가 `AFTER= 'http://localhost:8500'` 를 확인했고, 저장과 함께 응답 캐시의
`adminconfig` 항목 1개가 자동으로 비워졌다(`UniversalCacheMiddleware` 무효화 로그:
`[BATCH_DELETE] Successfully cleared 1/1 cache entries`).

## 되돌리는 한 줄

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \
  python manage.py shell -c "
from django.apps import apps
AdminConfig = apps.get_model('configuration', 'AdminConfig')
row = AdminConfig.objects.get(name='System')
conf = dict(row.settings or {})
conf.pop('frontendUrl', None)
row.settings = conf
row.save(update_fields=['settings'])
"
```
