# 잠자는 기능 ㉠ 314건을 **갈랐다** — 한 건도 지우지 않았다 (D-388)

**실행 2026-09-13** · 도구 `scripts/classify_dormant.py` (규칙 9종 · 자기시험 양성 9 + 음성 1)

모수는 `scripts/verify_dormant.py` 가 센 **그 목록**이다 — 두 벌로 세면 두 수가 갈라진다.

> ⚠ **[정정 2026-09-14 · D-393] 이 문서의 수는 낡았다. 지우지 않고 덧붙인다.**
> ㉮ 41건 중 **셋**(`config/celery.py` 의 시그널 훅)은 **처음부터 배선돼 있었다** —
> `@worker_process_init.connect` 등을 판정기가 못 봤다. 모수를 고친 뒤 [실측]:
> **㉠ 314 → 311 · ㉮ 41 → 38 · 우리 관할 188 → 185.**
> 자세한 것은 `docs/agent/evidence/D-393/recount.md` 다.
> ★ 이것은 「켜졌다」가 아니라 **「자고 있지 않았다」**이다 — 우리가 한 일이 없다.

## 1. 네 칸 [실측]

```
㉠ 호출 없음  314건
  §0.4 금지구역        126건   (delivery·orders·terminals — 가르되 우리가 못 고친다)
  우리 관할            188건
     ㉮ 켜야 할 것        41건   모듈은 운영이 import 하는데 그 함수만 아무도 안 부른다
     ㉯ 지워야 할 것       5건   아무도 그 모듈을 import 하지 않는다
     ㉰ 정상            132건   dynamic 1 · method 91 · server-hook 9 · test-file 31
     ? 판정 불가         10건   시험만 부른다 — 발판인지 잠든 자산인지 도구가 못 가른다
```

★ 넷째 칸을 만든 이유: 모르는 것을 셋 중 하나에 밀어 넣으면 **추측이 실측 행세**를 한다(D-290·D-301).

## 2. ㉮ 켜야 할 것 — **세종께 드리는 목록** (켤 순서는 그쪽이 정한다)

```
  backend/common/ast_call_trace.py::models_touched
  backend/common/base_model.py::process_request
  backend/common/base_model.py::set_use_group
  backend/common/cache_signal_protection.py::cleanup_rate_limits
  backend/common/cache_signal_protection.py::protected_signal
  backend/common/inbound_api_key.py::inbound_key_routes
  backend/common/tenant_tripwire.py::build_baseline
  backend/common/tenant_tripwire.py::scan_static
  backend/common/universal_optimization.py::handle_multilanguage_cache_invalidation
  backend/common/universal_optimization.py::invalidate_cross_system
  backend/common/utils.py::create_multipart_schema
  backend/common/utils.py::generate_item_code
  backend/common/utils.py::generate_order_code
  backend/config/celery.py::close_db_connections_after_task
  backend/config/celery.py::close_db_connections_before_task
  backend/config/celery.py::init_worker_process
  backend/dashboard/shemas/schemas_djantic_out.py::get_weather_by_coordinates
  backend/devices/utils.py::sort_terminal_by_location
  backend/media_data/services/media_data_detect_service.py::get_server_ipv4_address
  backend/operation_settings/auth.py::get_token_scopes
  backend/operation_settings/auth.py::has_scope
  backend/operation_settings/auth.py::is_oauth2_authenticated
  backend/operation_settings/auth.py::oauth2_required
  backend/operation_settings/auth.py::scope_required
  backend/optimization/tasks/cache_warming_tasks.py::warm_specific_data
  backend/report_template/utils.py::clean_template_for_pdf
  backend/report_template/utils.py::download_and_install_korean_fonts
  backend/report_template/utils.py::test_korean_font_support
  backend/stream_monitors/services/frame_detection_pb2_grpc.py::add_FrameDetectionServiceServicer_to_server
  backend/stream_monitors/services/grpc_dual_stream_service.py::get_grpc_dual_stream_status
  backend/stream_monitors/services/grpc_dual_stream_service.py::start_grpc_dual_stream
  backend/stream_monitors/services/grpc_dual_stream_service.py::stop_grpc_dual_stream
  backend/stream_monitors/utils/redis_client.py::clear_webrtc_state
  backend/stream_monitors/utils/redis_client.py::delete_recording_status
  backend/stream_monitors/utils/redis_client.py::list_recording_statuses
  backend/stream_monitors/utils/redis_client.py::set_recording_status
  backend/stream_monitors/utils/stream_utils.py::get_stream_url
  backend/surveillance/signals.py::video_analysis_post_save
  backend/third_api/common/utils.py::anyang_service_key_required
  backend/third_api/common/utils.py::validate_required_fields
  backend/third_api/schema.py::resolve_api_key_name
```

## 3. ㉯ 지워야 할 것 — **한 건도 지우지 않았다** (D-388 지시 그대로)

```
  backend/stream_monitors/services/record_service.py::control_record
  backend/stream_monitors/services/record_service.py::get_recording_status_by_code
  backend/stream_monitors/services/video_record_service.py::get_status
  backend/stream_monitors/services/video_record_service.py::pause
  backend/stream_monitors/services/video_record_service.py::resume
```

두 모듈(`record_service.py` · `video_record_service.py`)은 **backend 전체에서 import 0회**다 [실측: grep].

## 4. ? 판정 불가 — 시험만 부르는 것

```
  backend/common/api_contract.py::classify_permission_routes
  backend/common/cache_signal_protection.py::defer_stats
  backend/common/cache_signal_protection.py::reset_defer_state
  backend/common/ops_tasks.py::ops_status
  backend/common/performance_optimizer.py::enable_request_caching
  backend/common/performance_optimizer.py::get_performance_stats
  backend/common/performance_optimizer.py::optimized_queryset_evaluation
  backend/common/performance_optimizer.py::optimized_schema_processing
  backend/common/tenant_scope.py::summarize
  backend/common/tenant_tripwire.py::scan_runtime
```

## 5. 판정기를 세 번 고쳤다 — **세 번 다 판정기가 틀렸다** (D-350)

① 저장소 전체의 `*.md`·`*.json` 을 「문자열 배선」의 근거로 읽었다 → **우리 증거 파일이
   적어 둔 함수 이름**(dormant.json·decisions.yaml)이 배선으로 잡혀 80건이 가짜였다.
   **문서가 이름을 적은 것은 배선이 아니다.**
② 클래스가 **자기 파일 안에서** 등장하는 것까지 「살아 있다」로 세어, 규칙이 아무것도
   가르지 못하고 188건 전부가 ㉰정상으로 나왔다. 0건 네 칸은 분류가 아니라 도장이다.
③ `gunicorn.conf.py` 의 서버 훅 아홉(`post_fork`·`worker_exit`…)을 **㉯지워야**에 넣었다.
   지웠으면 워커 수명주기가 통째로 사라진다 — 이 도구가 낼 수 있는 **가장 비싼 오답**이다.
   규칙 `server-hook` 을 더하고 그 사례를 자기시험 표본으로 박았다 (D-310).

★ 그리고 ㉠ 판정기의 틈 하나를 [실측]으로 기록한다: `verify_dormant._is_test` 는
  `tests/` 와 `test_*.py` 만 시험으로 본다 — **`test.py`·`tests.py` 는 안 걸린다.**
  여기서는 `test-file` 규칙으로 메웠고, **래칫(기준선)은 건드리지 않았다.**
