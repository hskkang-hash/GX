import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dateutil import parser as date_parser

from django.core.paginator import EmptyPage
from common.pagination import OptimizedPaginator
from django.http import HttpRequest
from ninja import File, UploadedFile, Form
from ninja_extra import api_controller, route
from ninja.errors import ValidationError

from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from core.common.schema_utils import DynamicSchema
from core.role.permission import path_permission
from core.file_management.helper import FileHelper
from common.constant import MESSAGE_ENUM, get_message

from handover.models import HandoverShift, HandoverDocument, HandoverContent, HandoverNotice, HandoverNoticeComment
from handover.services.handover_shift_service import HandoverShiftService
from handover.services.handover_document_service import HandoverDocumentService, parse_date_flexible, normalize_date_to_iso, parse_date_range_with_validation
from handover.services.handover_content_service import HandoverContentService
from handover.services.handover_notice_service import HandoverNoticeService
from handover.services.handover_notice_comment_service import HandoverNoticeCommentService
from handover.schemas.schemas_djantic_in import (
    HandoverShiftCreateInSchema, HandoverShiftUpdateInSchema, WorkShiftConfigInSchema,
    HandoverDocumentCreateInSchema, HandoverDocumentDeleteInSchema,
    HandoverContentCreateInSchema, HandoverContentUpdateInSchema, HandoverContentsBatchInSchema,
    HandoverContentDeleteInSchema, HandoverDutyDetailInSchema,
    HandoverNoticeCreateInSchema, HandoverNoticeDeleteInSchema, HandoverNoticeProcessInSchema,
    HandoverNoticeRestoreInSchema, DownloadManagementInSchema, DownloadNoticeInSchema,
    HandoverNoticeCommentCreateInSchema, HandoverNoticeCommentUpdateInSchema, HandoverNoticeCommentDeleteInSchema
)
from handover.schemas.schemas_djantic_out import (
    HandoverShiftOutSchema, HandoverDocumentOutSchema, HandoverDocumentListOutSchema,
    HandoverContentOutSchema, HandoverDutyDetailOutSchema,
    HandoverNoticeOutSchema, HandoverNoticeDetailOutSchema, HandoverNoticeCommentOutSchema
)

logger = logging.getLogger(__name__)


@api_controller("/handover/shift", tags=["Handover Shift"])
class HandoverShiftController:
    """Controller for HandoverShift operations"""

    @route.get("", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def list_shifts(self, request: HttpRequest):
        """Lấy danh sách ca làm việc"""
        try:
            queryset = HandoverShiftService.get_list(user=request.user)
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            shifts = HandoverShiftOutSchema.from_queryset(queryset, many=True)
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_HANDOVER_SHIFT_SUCCESS),
                data=shifts
            )
        except Exception as exc:
            logger.exception("Error getting handover shifts: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/handover")
    def create_shift(self, request: HttpRequest, data: HandoverShiftCreateInSchema):
        """Tạo ca làm việc mới"""
        try:
            success, shift = HandoverShiftService.create(data.dict(), request.user)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_SHIFT_SUCCESS),
                    data=HandoverShiftOutSchema.from_queryset(shift, many=False)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_SHIFT_FAILED),
                    data=None
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error creating handover shift: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.put("", auth=CustomJWTAuth())
    @path_permission("update", path_override="/handover")
    def update_shift(self, request: HttpRequest, data: HandoverShiftUpdateInSchema):
        """Cập nhật ca làm việc"""
        try:
            success, shift = HandoverShiftService.update(data.dict(), request.user)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.UPDATE_HANDOVER_SHIFT_SUCCESS),
                    data=HandoverShiftOutSchema.from_queryset(shift, many=False)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.UPDATE_HANDOVER_SHIFT_FAILED),
                    data=None
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error updating handover shift: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.delete("", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/handover")
    def delete_shift(self, request: HttpRequest, id: int):
        """Xóa ca làm việc"""
        try:
            success, message = HandoverShiftService.delete(id)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                    data=None
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                    data={'error': message},
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error deleting handover shift: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("/work-shift-config", auth=CustomJWTAuth())
    @path_permission("update", path_override="/handover")
    def work_shift_config(self, request: HttpRequest, data: WorkShiftConfigInSchema):
        """Cấu hình hàng loạt ca làm việc"""
        try:
            success, results = HandoverShiftService.batch_config(data.dict(), request.user)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.CONFIG_HANDOVER_SHIFT_SUCCESS),
                    data=results
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.CONFIG_HANDOVER_SHIFT_FAILED),
                    data=results
                )
        except Exception as exc:
            logger.exception("Error configuring work shifts: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )


@api_controller("/handover/management", tags=["Handover Management"])
class HandoverManagementController:
    """Controller for HandoverDocument operations (V1)"""

    @route.get("", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def list_management(self, request: HttpRequest):
        """Lấy danh sách handover documents với logic giống old feature"""
        try:
            page_size = int(request.GET.get("page_size", 25))
            current_page = int(request.GET.get("current_page", 1))
            
            # Lấy date range từ query params (giống logic cũ)
            from datetime import timedelta
            from django.utils import timezone as django_timezone
            import datetime as dt
            
            # Tạo mutable copy của request.GET để pop các key
            params = request.GET.copy()

            # Xử lý riêng filter theo ngày để hỗ trợ cả search dạng "19" lẫn "2025-11-19"
            date_filter_raw = params.get('date')
            date_filter_day: Optional[str] = None
            date_filter_exact: Optional[str] = None
            date_filter_substring: Optional[str] = None
            if date_filter_raw is not None:
                raw_str = str(date_filter_raw).strip()
                normalized_str = raw_str.replace('/', '-')
                separator_count = normalized_str.count('-')
                if normalized_str.isdigit() and len(normalized_str) <= 2:
                    date_filter_day = normalized_str.zfill(2)
                elif separator_count >= 2:
                    try:
                        parsed_date_value = parse_date_flexible(normalized_str)
                        date_filter_exact = parsed_date_value.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        date_filter_substring = normalized_str
                else:
                    date_filter_substring = normalized_str
            
            # Lấy start_date_time và end_date_time với default (giống logic cũ)
            start_date_time = params.get('start_date_time', django_timezone.now() - timedelta(weeks=1))
            end_date_time = params.get('end_date_time', django_timezone.now())
            
            # Nếu có date_start và date_end thì dùng chúng thay thế (giống logic cũ)
            date_start = params.get('date_start', None)
            date_end = params.get('date_end', None)

            total_content = params.get('total_content', None)
            creator__full_name = params.get('creator__full_name', None)
            created_time_start = params.get('created_time_start', None)
            created_time_end = params.get('created_time_end', None)
            
            parsed_date_start: Optional[date] = None
            parsed_date_end: Optional[date] = None

            if date_start:
                try:
                    parsed_date_start = parse_date_flexible(str(date_start))
                except (ValueError, TypeError):
                    parsed_date_start = None

            if date_end:
                try:
                    parsed_date_end = parse_date_flexible(str(date_end))
                except (ValueError, TypeError):
                    parsed_date_end = None

            if parsed_date_start and parsed_date_end:
                start_date_time = date_start
                end_date_time = date_end
            
            # Pop các key này ra khỏi request để không bị sai khi filter
            filtered_params = params.copy()
            filtered_params.pop('start_date_time', None)
            filtered_params.pop('end_date_time', None)
            filtered_params.pop('date_start', None)
            filtered_params.pop('date_end', None)

            if parsed_date_start and parsed_date_end:
                filtered_params['date__gte'] = parsed_date_start.strftime('%Y-%m-%d')
                filtered_params['date__lte'] = parsed_date_end.strftime('%Y-%m-%d')

            if date_filter_day:
                filtered_params.pop('date', None)
            elif date_filter_exact:
                filtered_params['date'] = date_filter_exact
            elif date_filter_substring:
                filtered_params['date'] = date_filter_substring
            
            # Cập nhật request.GET với params đã xử lý
            request.GET = filtered_params
            
            queryset = HandoverDocumentService.get_list(
                user=request.user,
                start_date_time=start_date_time,
                end_date_time=end_date_time
            )
            
            # Áp dụng dynamic filters và sort (queryset có thể dùng apply_dynamic_filters)
            # apply_dynamic_filters sẽ filter và sort documents trong queryset
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            
            # Nếu có date range, cần kết hợp với empty shifts
            sort_key = None
            sort_desc = False
            sort_obj_raw = request.GET.get("sort_obj")
            if sort_obj_raw:
                try:
                    ordering_criteria = json.loads(sort_obj_raw)
                    if ordering_criteria and len(ordering_criteria) > 0:
                        sort_key = ordering_criteria[0].get("key")
                        sort_desc = ordering_criteria[0].get("value", "asc") == "desc"
                except Exception:
                    pass

            if start_date_time and end_date_time:
                # Parse dates với validation để đảm bảo end_date >= start_date
                import pandas as pd
                try:
                    start_date, end_date = parse_date_range_with_validation(start_date_time, end_date_time, request.user)
                    date_range = pd.date_range(start=start_date, end=end_date)
                    date_list = date_range.strftime("%Y-%m-%d").tolist()
                except Exception:
                    date_list = []
                
                if date_filter_day:
                    date_list = [d for d in date_list if d.endswith(f"-{date_filter_day}")]
                elif date_filter_exact:
                    date_list = [d for d in date_list if d == date_filter_exact]
                elif date_filter_substring:
                    date_list = [d for d in date_list if date_filter_substring in d]

                if sort_key == 'date':
                    date_list = sorted(date_list, reverse=sort_desc)

                # Lấy documents đã được filter và sort từ queryset
                documents_list = list(queryset.values())
                
                # Lấy empty shifts cho các date chưa có document
                empty_shifts = HandoverDocumentService.get_empty_shifts(
                    user=request.user,
                    start_date_time=start_date_time,
                    end_date_time=end_date_time,
                    existing_documents=documents_list
                )
                # Group documents theo date
                documents_by_date = {}
                for doc in documents_list:
                    doc_date = doc.get('date') or doc.get('date_create_shift')
                    doc_date = normalize_date_to_iso(doc_date)
                    if not doc_date:
                        continue
                    
                    if doc_date not in documents_by_date:
                        documents_by_date[doc_date] = []
                    documents_by_date[doc_date].append(doc)
                
                # Group empty_shifts theo date (đã có sẵn format {"date": date, "data": [...]})
                empty_shifts_by_date = {}
                for empty_shift in empty_shifts:
                    shift_date = empty_shift.get('date')
                    shift_date = normalize_date_to_iso(shift_date)
                    if shift_date:
                        empty_shifts_by_date[shift_date] = empty_shift
                # Gộp documents và empty shifts theo ngày (giống logic cũ)
                # Đảm bảo thứ tự ngày từ nhỏ đến lớn
                combined_data = []
                for date_str in date_list:
                    # Lấy documents của date này và sort theo sort_key nếu có
                    date_documents = documents_by_date.get(date_str, [])

                    # Nếu có sort_obj, sort documents trong cùng một ngày
                    if sort_key and date_documents:
                        try:
                            def _normalize_sort_value(raw_value: Any):
                                """Ensure values are comparable during sorting."""
                                if isinstance(raw_value, list):
                                    return tuple(_normalize_sort_value(item) for item in raw_value)
                                if isinstance(raw_value, datetime):
                                    return raw_value
                                if isinstance(raw_value, date):
                                    return datetime.combine(raw_value, datetime.min.time())
                                if isinstance(raw_value, (int, float)):
                                    return raw_value
                                if raw_value is None:
                                    return ''
                                return str(raw_value).lower()

                            present_documents = []
                            missing_documents = []

                            for document in date_documents:
                                if document.get(sort_key) is None:
                                    missing_documents.append(document)
                                else:
                                    present_documents.append(document)

                            present_documents.sort(
                                key=lambda doc: _normalize_sort_value(doc.get(sort_key)),
                                reverse=sort_desc
                            )

                            # Đưa các phần tử thiếu sort_key xuống cuối danh sách
                            date_documents = present_documents + missing_documents
                        except Exception:
                            pass
                    
                    # Append documents của date này (đã được sort nếu có sort_obj)
                    combined_data.extend(date_documents)
                    
                    # Append empty shifts của date này (nếu có)
                    if date_str in empty_shifts_by_date and not total_content and not creator__full_name and not created_time_start and not created_time_end:
                        combined_data.append(empty_shifts_by_date[date_str])

                # Kết quả đã được sắp xếp theo ngày từ nhỏ đến lớn (do loop qua date_list)
                # và documents trong cùng một ngày đã được sort theo sort_key nếu có
                # Pagination trên list kết hợp đã được sort
                total_items = len(combined_data)
                total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 1
                
                start_idx = (current_page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_data = combined_data[start_idx:end_idx]

                def _parse_to_datetime(raw_value: Any) -> Optional[datetime]:
                    if raw_value in (None, "", " "):
                        return None
                    if isinstance(raw_value, datetime):
                        return raw_value
                    if isinstance(raw_value, date):
                        return datetime.combine(raw_value, datetime.min.time())
                    if isinstance(raw_value, str):
                        try:
                            return date_parser.parse(raw_value)
                        except (ValueError, TypeError):
                            return None
                    return None

                def _format_datetime_value(raw_value: Any) -> Any:
                    parsed_value = _parse_to_datetime(raw_value)
                    if parsed_value is None:
                        return raw_value
                    return parsed_value.isoformat() if isinstance(parsed_value, datetime) else parsed_value

                def _format_date_value(raw_value: Any) -> Any:
                    parsed_value = _parse_to_datetime(raw_value)
                    if parsed_value is None:
                        return raw_value
                    return parsed_value.date().isoformat() if isinstance(parsed_value, datetime) else parsed_value

                datetime_keys = {
                    'created_on', 'modified_on', 'start_date', 'end_date', 'created_time', 'updated_time'
                }
                date_keys = {'date', 'date_create_shift'}

                formatted_data = []
                for item in paginated_data:
                    if isinstance(item, dict) and item.get('id'):
                        formatted_item = item.copy()
                        for key in datetime_keys:
                            if key in formatted_item:
                                formatted_item[key] = _format_datetime_value(formatted_item[key])
                        for key in date_keys:
                            if key in formatted_item:
                                formatted_item[key] = _format_date_value(formatted_item[key])
                        formatted_data.append(formatted_item)
                    elif isinstance(item, dict) and 'date' in item:
                        formatted_item = item.copy()
                        formatted_item['date'] = _format_date_value(formatted_item.get('date'))
                        formatted_data.append(formatted_item)
                    else:
                        formatted_data.append(item)

                paginated_data = formatted_data
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.GET_LIST_HANDOVER_MANAGEMENT_SUCCESS),
                    data=paginated_data,
                    total_pages=total_pages,
                    total_items=total_items,
                    current_page=current_page
                )
            else:
                # Nếu không có date range, xử lý như cũ với queryset
                # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
                paginator = OptimizedPaginator(queryset, page_size)
                try:
                    pages = paginator.page(current_page)
                except EmptyPage:
                    current_page = paginator.num_pages or 1
                    pages = paginator.page(current_page)
                
                documents = HandoverDocumentOutSchema.from_queryset(pages.object_list, many=True)
                
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.GET_LIST_HANDOVER_MANAGEMENT_SUCCESS),
                    data=documents,
                    total_pages=paginator.num_pages,
                    total_items=paginator.count,
                    current_page=current_page
                )
        except Exception as exc:
            logger.exception("Error getting handover management: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/handover")
    def create_management(self, request: HttpRequest, data: HandoverDocumentCreateInSchema):
        """Tạo handover document mới"""
        try:
            success, document, error_info = HandoverDocumentService.create(data.dict(), request.user)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_MANAGEMENT_SUCCESS),
                    data=HandoverDocumentOutSchema.from_queryset(document, many=False)
                )
            else:
                # Kiểm tra nếu có message_key từ service
                if error_info and error_info.get('message_key'):
                    message = get_message(error_info['message_key'])
                else:
                    message = get_message(MESSAGE_ENUM.CREATE_HANDOVER_MANAGEMENT_FAILED)
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=message,
                    data=None
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error creating handover document: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.delete("", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/handover")
    def delete_management(self, request: HttpRequest, data: HandoverDocumentDeleteInSchema):
        """Xóa handover documents"""
        try:
            success, results = HandoverDocumentService.delete(data.ids, request.user)
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=results
            )
        except Exception as exc:
            logger.exception("Error deleting handover documents: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("/download-management", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def download_management(self, request: HttpRequest, data: DownloadManagementInSchema):
        """Queue download CSV handover management (background processing with WebSocket notifications)"""
        try:
            # Parse request.body để lấy các params search
            import copy
            from django.http import QueryDict
            request_copy = copy.copy(request)
            request_copy.GET = QueryDict(mutable=True)
            
            try:
                body_data = json.loads(request.body.decode('utf-8'))
                # Pop selected_field ra
                body_data.pop('selected_field', None)
                body_data.pop('get_delete_notice', None)
                # Thêm các params còn lại vào request.GET
                for key, value in body_data.items():
                    request_copy.GET[key] = value
            except Exception:
                pass
            
            result = HandoverDocumentService.download_management(
                data.start_date_time,
                data.end_date_time,
                request.user,
                request=request_copy
            )
            
            if result.get('success'):
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.START_DOWNLOAD_FILE),
                    data={
                        'task_id': result.get('download_task_id')
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=result.get('message', get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR)),
                    data=None
                )
        except Exception as exc:
            logger.exception("Error queueing handover management download: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )


@api_controller("/handover/content", tags=["Handover Content"])
class HandoverContentController:
    """Controller for HandoverContent operations"""

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/handover")
    def create_or_update_content(self, request: HttpRequest, data: HandoverContentCreateInSchema = None, update_data: HandoverContentUpdateInSchema = None):
        """Tạo hoặc cập nhật handover content"""
        try:
            if update_data:
                content_data = update_data.dict()
                content_data['content_id'] = update_data.content_id
            else:
                content_data = data.dict()
                content_data['handover_doc_id'] = data.handover_doc_id
            
            success, content = HandoverContentService.create_or_update(content_data, request.user)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_CONTENT_SUCCESS if not update_data else MESSAGE_ENUM.UPDATE_HANDOVER_CONTENT_SUCCESS),
                    data=HandoverContentOutSchema.from_queryset(content, many=False)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_CONTENT_FAILED if not update_data else MESSAGE_ENUM.UPDATE_HANDOVER_CONTENT_FAILED),
                    data=None
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error creating/updating handover content: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("/contents", auth=CustomJWTAuth())
    @path_permission("create", path_override="/handover")
    def batch_create_or_update_content(self, request: HttpRequest, data: HandoverContentsBatchInSchema):
        """Tạo/cập nhật hàng loạt handover content"""
        try:
            success, results = HandoverContentService.batch_create_or_update(data.handover_contents, request.user)
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.BATCH_UPDATE_HANDOVER_CONTENT_SUCCESS),
                data=results
            )
        except Exception as exc:
            logger.exception("Error batch creating/updating handover content: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.delete("", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/handover")
    def delete_content(self, request: HttpRequest, data: HandoverContentDeleteInSchema):
        """Xóa handover content"""
        try:
            success, message = HandoverContentService.delete(data.content_id, data.handover_doc_id)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                    data=None
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                    data={'error': message},
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error deleting handover content: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.get("/by-id-management", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def get_content_by_document(self, request: HttpRequest, id: int):
        """Lấy danh sách content của một handover document"""
        try:
            queryset = HandoverContentService.get_by_document(id)
            get_params = request.GET.copy()
            if 'id' in get_params:
                get_params.pop('id')
            request.GET = get_params
            
            # Áp dụng dynamic filters và sort
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            contents = HandoverContentOutSchema.from_queryset(queryset, many=True, auto_resolve_fields=True)
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_HANDOVER_CONTENT_SUCCESS),
                data=contents
            )
        except Exception as exc:
            logger.exception("Error getting handover content by document: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("/handover-duty-detail", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def handover_duty_detail(self, request: HttpRequest, data: HandoverDutyDetailInSchema):
        """Lấy chi tiết nhiều handover documents"""
        try:
            queryset = HandoverContentService.get_duty_detail(data.handover_ids)
            contents = HandoverDutyDetailOutSchema.from_queryset(queryset, many=True)
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_HANDOVER_DUTY_DETAIL_SUCCESS),
                data=contents
            )
        except Exception as exc:
            logger.exception("Error getting handover duty detail: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )


@api_controller("/handover/notice", tags=["Handover Notice"])
class HandoverNoticeController:
    """Controller for HandoverNotice operations"""

    @route.get("", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def list_notice(self, request: HttpRequest):
        """Lấy danh sách thông báo"""
        try:
            page_size = int(request.GET.get("page_size", 25))
            current_page = int(request.GET.get("current_page", 1))
            queryset = HandoverNoticeService.get_list(user=request.user)
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(queryset, page_size)
            pages = paginator.page(current_page)
            notices = HandoverNoticeOutSchema.from_queryset(pages.object_list, many=True)
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_HANDOVER_NOTICE_SUCCESS),
                data=notices,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page
            )
        except Exception as exc:
            logger.exception("Error getting handover notices: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/handover")
    def create_or_update_notice(self, request: HttpRequest, 
                                data: str = Form(..., description="JSON string của HandoverNoticeCreateInSchema"),
                                files: Optional[List[UploadedFile]] = File(None)):
        """Tạo hoặc cập nhật thông báo"""
        try:
            # Parse JSON data
            data_dict = json.loads(data)
            
            # Validate với schema
            try:
                schema = HandoverNoticeCreateInSchema(**data_dict)
                validated_data = schema.dict(exclude_unset=True)
            except Exception as e:
                return BaseResponse(
                    status_code=422,
                    success=False,
                    message=str(e),
                    data=None
                )
            
            # Xử lý file upload nếu có
            uploaded_files = []
            if files:
                for file in files:
                    file_obj = FileHelper.user_upload_s3(request.user, file, is_avatar=False, only_image=False)
                    if file_obj:
                        uploaded_files.append(file_obj)
            
            success, notice = HandoverNoticeService.create_or_update(
                validated_data, request.user, uploaded_files
            )
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_NOTICE_SUCCESS if not validated_data.get('notice_id') else MESSAGE_ENUM.UPDATE_HANDOVER_NOTICE_SUCCESS),
                    data=HandoverNoticeOutSchema.from_queryset(notice, many=False)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_NOTICE_FAILED if not validated_data.get('notice_id') else MESSAGE_ENUM.UPDATE_HANDOVER_NOTICE_FAILED),
                    data=None
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error creating/updating handover notice: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.delete("", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/handover")
    def delete_notice(self, request: HttpRequest, data: HandoverNoticeDeleteInSchema):
        """Xóa thông báo"""
        try:
            success, message = HandoverNoticeService.delete(data.id)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                    data=None
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                    data={'error': message},
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error deleting handover notice: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.get("/by-id-notice", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def get_notice_detail(self, request: HttpRequest, id: int):
        """Lấy chi tiết thông báo - chỉ lấy parent comments (replies sẽ được load khi click view more)"""
        try:
            notice = HandoverNoticeService.get_detail(id)
            # Sử dụng DynamicSchema.from_queryset với many=False để tự động lấy tất cả fields và prefetch_related
            notice_data = HandoverNoticeDetailOutSchema.from_queryset(notice, many=False)
            
            # Chỉ serialize parent comments (không có replies) - replies sẽ được load qua endpoint list_comments với parent_id
            if 'comments' in notice_data and notice.comments.exists():
                comments_data = HandoverNoticeCommentOutSchema.from_queryset(
                    notice.comments.all(), many=True
                )
                notice_data['comments'] = comments_data
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_HANDOVER_NOTICE_DETAIL_SUCCESS),
                data=notice_data
            )
        except HandoverNotice.DoesNotExist:
            return BaseResponse(
                status_code=404,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_NOTICE_NOT_FOUND),
                data=None
            )
        except Exception as exc:
            logger.exception("Error getting handover notice detail: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("/notice-process", auth=CustomJWTAuth())
    @path_permission("update", path_override="/handover")
    def process_notice(self, request: HttpRequest, data: HandoverNoticeProcessInSchema):
        """Đánh dấu xử lý thông báo"""
        try:
            success, notice = HandoverNoticeService.process(data.id, data.is_processed, request.user)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.PROCESS_HANDOVER_NOTICE_SUCCESS),
                    data=HandoverNoticeOutSchema.from_queryset(notice, many=False)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.PROCESS_HANDOVER_NOTICE_FAILED),
                    data=None
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error processing handover notice: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("/notice-restore", auth=CustomJWTAuth())
    @path_permission("update", path_override="/handover")
    def restore_notice(self, request: HttpRequest, data: HandoverNoticeRestoreInSchema):
        """Khôi phục thông báo đã xóa"""
        try:
            success, notice = HandoverNoticeService.restore(data.id)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.RESTORE_HANDOVER_NOTICE_SUCCESS),
                    data=HandoverNoticeOutSchema.from_queryset(notice, many=False)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.RESTORE_HANDOVER_NOTICE_FAILED),
                    data=None
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error restoring handover notice: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("/download-notice", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def download_notice(self, request: HttpRequest, data: DownloadNoticeInSchema):
        """Queue download CSV handover notice (processing notices - background processing with WebSocket notifications)"""
        try:
            if not data.selected_field:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message="Selected fields is empty",
                    data=None
                )
            # Parse request.body để lấy các params search
            import copy
            from django.http import QueryDict
            request_copy = copy.copy(request)
            request_copy.GET = QueryDict(mutable=True)
            
            
            body_data = json.loads(request.body.decode('utf-8'))
            # Pop selected_field ra
            body_data.pop('selected_field', None)
            body_data.pop('get_delete_notice', None)
            # Thêm các params còn lại vào request.GET
            for key, value in body_data.items():
                request_copy.GET[key] = value
            # Đảm bảo notice_status là 'processing' hoặc None cho processing notices
            # Endpoint này chỉ dùng cho processing notices (không phải processed)
            notice_status = 'processed' 
            result = HandoverNoticeService.download_notice(notice_status, data.get_delete_notice or False, data.selected_field, request.user, processed=False, request=request_copy)
            
            if result.get('success'):
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.START_DOWNLOAD_FILE),
                    data={
                        'task_id': result.get('download_task_id')
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=result.get('message', get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR)),
                    data=None
                )
        except Exception as exc:
            logger.exception("Error queueing handover notice download: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("/download-completed-notice", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def download_completed_notice(self, request: HttpRequest, data: DownloadNoticeInSchema):
        """Queue download CSV completed handover notice (processed notices - background processing with WebSocket notifications)"""
        try:
            if not data.selected_field:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message="Selected fields is empty",
                    data=None
                )
            
            # Parse request.body để lấy các params search
            import copy
            from django.http import QueryDict
            request_copy = copy.copy(request)
            request_copy.GET = QueryDict(mutable=True)
            
            try:
                body_data = json.loads(request.body.decode('utf-8'))
                # Pop selected_field ra
                body_data.pop('selected_field', None)
                body_data.pop('get_delete_notice', None)
                # Thêm các params còn lại vào request.GET
                for key, value in body_data.items():
                    request_copy.GET[key] = value
                request_copy.GET['deleted'] = 'true'
            except Exception:
                pass
            
            # Đảm bảo notice_status là 'processed' cho completed notices
            notice_status = 'processed'
            
            result = HandoverNoticeService.download_notice(
                notice_status,
                True,
                data.selected_field,
                request.user,
                processed=True,
                request=request_copy
            )
            
            if result.get('success'):
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.START_DOWNLOAD_FILE),
                    data={
                        'task_id': result.get('download_task_id')
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=result.get('message', get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR)),
                    data=None
                )
        except Exception as exc:
            logger.exception("Error queueing completed handover notice download: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )


@api_controller("/handover/notice-comment", tags=["Handover Notice Comment"])
class HandoverNoticeCommentController:
    """Controller for HandoverNoticeComment operations"""

    @route.get("", auth=CustomJWTAuth())
    @path_permission("read", path_override="/handover")
    def list_comments(self, request: HttpRequest, notice_id: int, page_number: int = 1, page_size: int = 25, parent_id: int = None):
        """Lấy danh sách bình luận
        - Nếu parent_id=None: Lấy parent comments của notice (id là notice_id)
        - Nếu parent_id có giá trị: Lấy replies của comment đó (id là notice_id, parent_id là comment_id)
        """
        try:
            if parent_id:
                # Lấy replies của một comment cụ thể
                queryset = HandoverNoticeCommentService.get_replies(parent_id)
            else:
                # Lấy parent comments của notice
                queryset = HandoverNoticeCommentService.get_list(notice_id, None)
            
            # Áp dụng dynamic filters và sort
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(queryset, page_size)
            try:
                pages = paginator.page(page_number)
            except EmptyPage:
                page_number = paginator.num_pages or 1
                pages = paginator.page(page_number)
            
            # Sử dụng DynamicSchema để tự động lấy các field đã annotate
            comments = HandoverNoticeCommentOutSchema.from_queryset(pages.object_list, many=True)
            
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_HANDOVER_NOTICE_COMMENT_SUCCESS),
                data={"items": comments},
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=page_number
            )
        except Exception as exc:
            logger.exception("Error getting handover notice comments: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/handover")
    def create_or_update_comment(self, request: HttpRequest, create_data: HandoverNoticeCommentCreateInSchema = None, update_data: HandoverNoticeCommentUpdateInSchema = None):
        """Tạo hoặc cập nhật bình luận"""
        try:
            if update_data:
                success, comment = HandoverNoticeCommentService.update(
                    update_data.comment_id, update_data.comment, request.user
                )
            else:
                success, comment = HandoverNoticeCommentService.create(
                    create_data.dict(), request.user
                )
            
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_NOTICE_COMMENT_SUCCESS if not update_data else MESSAGE_ENUM.UPDATE_HANDOVER_NOTICE_COMMENT_SUCCESS),
                    data=HandoverNoticeCommentOutSchema.from_queryset(comment, many=False)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.CREATE_HANDOVER_NOTICE_COMMENT_FAILED if not update_data else MESSAGE_ENUM.UPDATE_HANDOVER_NOTICE_COMMENT_FAILED),
                    data=None
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error creating/updating handover notice comment: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

    @route.delete("", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/handover")
    def delete_comment(self, request: HttpRequest, id: int):
        """Xóa bình luận"""
        try:
            success, message = HandoverNoticeCommentService.delete(id)
            if success:
                return BaseResponse(
                    status_code=200,
                    success=True,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                    data=None
                )
            else:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                    data={'error': message},
                )
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(e),
                data=None
            )
        except Exception as exc:
            logger.exception("Error deleting handover notice comment: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.HANDOVER_UNEXPECTED_ERROR),
                data=None
            )

