import logging
import json
from django.forms import Form
from ninja_extra import api_controller, route
from ninja import Schema, Path, Query, Form, File
from typing import List, Optional, Dict, Any
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator
from django.utils.translation import gettext as _
from common.utils import SchemaUtils
from devices.models import Library
from devices.schemas.schemas_djantic_in import LibraryCreateSchema, LibraryUpdateSchema, AddToGroupsSchema
from devices.schemas.schemas_djantic_out import LibraryOutSchema, LibraryListOutSchema, AddToGroupsResponse
from devices.services import library_service
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import build_dynamic_query_from_queryset
from common.constant import MESSAGE_ENUM, get_message
from ninja.files import UploadedFile
from django.contrib.contenttypes.models import ContentType
from core.file_management.helper import FileHelper
from core.file_management.models import UserMediaFileItem, UserMediaFile
from core.role.permission import path_permission
import time
from core.common.search.dynamic_search import apply_dynamic_filters
from django.db.models import OuterRef, Subquery, Count, Max, F, Case, When, BooleanField, Exists, CharField,Sum
from django.db import connection, reset_queries
from django.conf import settings
from common.utils import add_records_to_groups

logger = logging.getLogger(__name__)

# Schema examples cho swagger UI
LIBRARY_CREATE_EXAMPLE = {
    "name": "Drone Template XYZ",
    "status": "active",
    "active": True,
    "main_type_id": 1,
    "sub_type": "standard",
    "dimensions": {
        "frame_size": "100 x 50 x 30 mm"
    }
}

LIBRARY_UPDATE_EXAMPLE = {
    "name": "Updated Drone Template",
    "status": "active",
    "active": True,
    "main_type_id": 2
}

@api_controller('/libraries-management', tags=['Libraries Management (Templates)'])
class LibraryAPI:
    @route.get('', auth=CustomJWTAuth())
    @path_permission("read", path_override="/library")
    def list_libraries(self):
        total_start_time = time.time()

        old_debug = settings.DEBUG
        settings.DEBUG = True
        reset_queries()

        request = self.context.request
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        query_start_time = time.time()
        exclude_fields = []
        libraries = Library.objects.all()\
            .select_related('main_type',
                           'manufacturer_information',
                           'avatar',
                           )\
            .prefetch_related('file_attachments')\
            .order_by('-id')

        libraries = libraries.annotate(model=F('manufacturer_information__model_number'),
                                   manufacturer=F('manufacturer_information__manufacturer'),
                                   in_use=Count('devices'),main_type__name = F('main_type__name'))

        libraries = apply_dynamic_filters(libraries, request, exclude_fields, request.GET.get('sort_obj'))

        query_time = time.time() - query_start_time

        paging_start_time = time.time()

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(libraries, page_size)
        pages = paginator.page(current_page)

        paging_time = time.time() - paging_start_time

        conversion_start_time = time.time()

        data = LibraryListOutSchema.from_queryset(pages.object_list, many=True)

        conversion_time = time.time() - conversion_start_time

        queries = connection.queries
        sql_count = len(queries)
        total_sql_time = sum(float(q['time']) for q in queries)

        slow_queries = [q for q in queries if float(q['time']) > 0.01]

        total_time = time.time() - total_start_time

        settings.DEBUG = old_debug

        return BaseResponse(status_code=200,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_LIBRARY_SUCCESS),
                            data = data,
                            total_pages=paginator.num_pages,
                            total_items=paginator.count,
                            current_page=current_page,
                            )

    @route.get('/{id}', auth=CustomJWTAuth())
    @path_permission("read", path_override="/library")
    def detail_library(self, id: int, edit: bool=False):
        try:

            library = Library.objects.filter(id=id).first()
            data = library_service.LibraryService.get_complete_data(library=library,
                                                                   user_units=None,
                                                                   edit=edit)

            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIBRARY_DETAIL_SUCCESS),
                data=data  # Đã sẵn sàng để trả về, không cần chuyển đổi
            )
        except Library.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Library"),
                data=None
            )

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/library")
    def create_library(self,
                     request,
                     data: str = Form(..., description="JSON string của LibraryCreateSchema"),
                     avatar: Optional[UploadedFile] = File(None),
                     files: Optional[List[UploadedFile]] = File(None)):
        """
        Tạo mới library template với avatar và các file đính kèm.

        ## Request Parameters

        | Parameter | Type | Description |
        |-----------|------|-------------|
        | data | Form (JSON string) | Dữ liệu library theo format LibraryCreateSchema |
        | avatar | File | Hình ảnh đại diện (không bắt buộc) |
        | files | List[File] | Các file đính kèm (không bắt buộc) |

        ## Schema dữ liệu (LibraryCreateSchema)

        Gửi dữ liệu trong trường `data` theo định dạng JSON với cấu trúc tương tự Device nhưng không có serial_number và unit_id:

        ```json
        {
          "name": "string",                     // Tên template (bắt buộc)
          "status": "active",                   // Trạng thái (mặc định: "active")
          "active": true,                       // Trạng thái hoạt động (mặc định: true)
          "main_type_id": 1,                    // ID của main_type (không bắt buộc)
          "sub_type": "standard",               // Loại phụ (mặc định: "standard")
          "created_by_id": null,                // ID người tạo (không bắt buộc)

          // Các trường khác tương tự Device...
        }
        ```

        ## Response

        ```json
        {
          "success": true,
          "status_code": 200,
          "message": "Create library successfully",
          "data": { /* Library data */ }
        }
        ```
        """

        try:
            # Parse JSON data
            data_dict = json.loads(data)

            # Validate với schema
            try:
                schema = LibraryCreateSchema(**data_dict)
                validated_data = schema.dict(exclude_unset=True)
            except Exception as e:
                return BaseResponse(success=False, status_code=422, message=str(e))

            # check registration number is unique
            manufacturer_info = validated_data.get('manufacturer_information')
            if manufacturer_info and isinstance(manufacturer_info, dict):
                registration_number = manufacturer_info.get('registration_number')
                if registration_number:
                    if Library.objects.filter(manufacturer_information__registration_number=registration_number).exists():
                        return BaseResponse(success=False, status_code=400, message=MESSAGE_ENUM.get(MESSAGE_ENUM.LIBRARY_REGISTRATION_NUMBER_ALREADY_EXISTS))
            # Create library with basic data
            library = library_service.LibraryService.create(validated_data, request)
            # Handle avatar upload if provided
            if avatar:
                try:
                    avatar_file = FileHelper.user_upload_s3(request.user, avatar, is_avatar=True, only_image=True)
                    if avatar_file:
                        library.avatar = avatar_file
                    library.save()
                except Exception as e:
                    return BaseResponse(success=False, status_code=400, message=str(e))

            # Handle files upload if provided
            if files and len(files) > 0:
                try:
                    library_content_type = ContentType.objects.get_for_model(library)
                    for file in files:
                        media_file = FileHelper.user_upload_s3(request.user, file)
                        if media_file:
                            # Create file attachment
                            UserMediaFileItem.objects.create(
                                user_media_file=media_file,
                                content_type=library_content_type,
                                object_id=library.id
                            )
                except Exception as e:
                    return BaseResponse(success=False, status_code=400, message=str(e))

            # Get complete data with files
            response_data = library_service.LibraryService.get_complete_data(library)
            return BaseResponse(status_code=200, message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_LIBRARY_SUCCESS), data=response_data)
        except ValidationError as e:
            # In chi tiết lỗi
            print("Validation error:", e)
            print("Error details:", e.errors())
            # Trả về response lỗi
            return {"success": False, "errors": e.errors()}
        except json.JSONDecodeError:
            return BaseResponse(success=False, status_code=400, message=str(_("Invalid JSON data")))

    @route.post("/{id}", auth=CustomJWTAuth())
    @path_permission("update", path_override="/library")
    def update_library(self,
                     id: int,
                     request,
                     data: str = Form(None),
                     avatar: Optional[UploadedFile] = File(None),
                     delete_avatar: bool = Form(False, description="Xóa avatar cũ"),
                     files: Optional[List[UploadedFile]] = File(None),
                     replace_files: bool = Form(False, description="Nếu xóa tất cả file cũ để tải mới thì True"),
                     files_to_remove: str = Form(None, description="Danh sách ID file cần xóa, định dạng array: 1,2,3, sử dụng khi xóa 1 phần của file cũ")):
        """
        Cập nhật library template với avatar và file đính kèm.
        """
        try:
            # Parse JSON data
            data_dict = json.loads(data) if data else {}

            # Validate với schema
            try:
                schema = LibraryUpdateSchema(**data_dict)
                validated_data = schema.dict(exclude_unset=True, exclude_none=True)
            except Exception as e:
                return BaseResponse(success=False, status_code=422, message=str(e))

            # check registration number is unique (excluding current library)
            manufacturer_info = validated_data.get('manufacturer_information')
            if manufacturer_info and isinstance(manufacturer_info, dict):
                registration_number = manufacturer_info.get('registration_number')
                if registration_number:
                    if Library.objects.filter(manufacturer_information__registration_number=registration_number).exclude(id=id).exists():
                        return BaseResponse(success=False, status_code=400, message=MESSAGE_ENUM.get(MESSAGE_ENUM.LIBRARY_REGISTRATION_NUMBER_ALREADY_EXISTS))

            # Update library with basic data
            library = library_service.LibraryService.update(id, validated_data)

            # Handle avatar upload if provided
            if avatar:
                # Remove old avatar if exists
                if library.avatar:
                    library.avatar.delete()
                    library.save()

                # Upload new avatar
                avatar_file = FileHelper.user_upload_s3(request.user, avatar, is_avatar=True, only_image=True)
                if avatar_file:
                    library.avatar = avatar_file
                    library.save()
            if delete_avatar:
                library.avatar.delete()
                library.avatar = None
                library.save()
            # Xử lý xóa tất cả file đính kèm cũ nếu replace_files=True
            library_content_type = ContentType.objects.get_for_model(library)

            if replace_files:
                # Xóa tất cả file đính kèm cũ
                UserMediaFileItem.objects.filter(
                    content_type=library_content_type,
                    object_id=library.id
                ).delete()
            # Xử lý xóa các file cụ thể nếu có files_to_remove và replace_files=False
            elif files_to_remove:
                try:
                    # Chuyển đổi chuỗi JSON thành list (nếu là chuỗi) hoặc sử dụng trực tiếp (nếu đã là list)
                    file_ids = files_to_remove
                    if isinstance(file_ids, str):
                        file_ids = file_ids.split(',')

                    if isinstance(file_ids, list) and len(file_ids) > 0:
                        # Xóa các file đính kèm cụ thể
                        UserMediaFileItem.objects.filter(
                            content_type=library_content_type,
                            object_id=library.id,
                            user_media_file_id__in=file_ids
                        ).delete()
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    # Log lỗi nhưng không làm gián đoạn quá trình cập nhật
                    print(f"Error processing files_to_remove: {str(e)}")
                    pass

            # Handle files upload if provided
            if files and len(files) > 0:
                for file in files:
                    media_file = FileHelper.user_upload_s3(request.user, file)
                    if media_file:
                        # Create file attachment
                        UserMediaFileItem.objects.create(
                            user_media_file=media_file,
                            content_type=library_content_type,
                            object_id=library.id
                        )

            # Get complete data with files
            response_data = library_service.LibraryService.get_complete_data(library)
            return BaseResponse(status_code=200, message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_LIBRARY_SUCCESS), data=response_data)
        except Library.DoesNotExist:
            return BaseResponse(status_code=404, message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Library"), data=None)
        except ValidationError as e:
            print("Validation error:", e)
            print("Error details:", e.errors())
            return {"success": False, "errors": e.errors()}
        except json.JSONDecodeError:
            return BaseResponse(success=False, status_code=400, message=str(_("Invalid JSON data")))

    @route.delete("/libraries/{ids}", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/library")
    def delete_library(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
            for id in id_list:
                library_service.LibraryService.delete(id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None,
            )
        except Library.DoesNotExist:
            return BaseResponse(status_code=404, message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Library"), data=None)
        except Exception:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None,
            )

    @route.delete("/{id}/detach-file/{file_id}", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/library")
    def detach_file(self, id: int, file_id: int):
        try:
            # Check if library exists
            library = Library.objects.get(id=id)

            # Check if file exists and is attached to this library
            library_content_type = ContentType.objects.get_for_model(library)
            attachment = UserMediaFileItem.objects.filter(
                user_media_file_id=file_id,
                content_type=library_content_type,
                object_id=library.id
            ).first()

            if not attachment:
                return BaseResponse(
                    status_code=404,
                    message=str(_("Attachment not found")),
                    data=None
                )

            # Delete the attachment (not the file itself)
            attachment.delete()

            return BaseResponse(
                status_code=200,
                message=str(_("File detached successfully")),
                data=None
            )
        except Library.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Library"),
                data=None
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=str(_("Failed to detach file: ")) + str(e)
            )

    @route.put("/{ids}/change-status", auth=CustomJWTAuth())
    @path_permission("update", path_override="/library")
    def change_status(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
        except ValueError:
            return BaseResponse.with_message(
                success=False,
                status_code=400,
                message="Invalid ID format. Please provide comma-separated integers."
            )
        libraries = Library.objects.filter(id__in=id_list)
        for library in libraries:
            library.active = not library.active
            library.save()
        return BaseResponse(status_code=200,message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_LIBRARY_SUCCESS))
