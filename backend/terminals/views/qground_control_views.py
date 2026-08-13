import zipfile
import io
import requests
import os
import uuid
import threading
import logging
from typing import List
from django.http import HttpResponse
from ninja_extra import api_controller, route
from ninja.files import UploadedFile 
from ninja.errors import ValidationError
from ninja import Schema, Path, Query, Form, File
from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from delivery.schemas.schemas_djantic_out import RouteOutSchema
from common.constant import MESSAGE_ENUM, get_message
from terminals.services.qground_control_service import QGroundControlService
from terminals.schemas.schemas_djantic_in import MavlinkCommandQuerySchema, MavlinkFrameQuerySchema, QGroundControlPlanExportSchema
from task_status.models import TaskStatus
from task_status.services.task_status_service import TaskStatusService
from terminals.tasks import _process_import_plan_in_thread
from common.utils import get_gcs_api_headers

logger = logging.getLogger(__name__)


@api_controller('/qground-control', tags=['QGroundController Plan Import/Export'])
class QGroundControlController:
    """Controller cho QGroundControl Plan Import/Export operations"""
    
    def __init__(self):
        self.service = QGroundControlService()
    
    @route.post("/import-plan", auth=CustomJWTAuth())
    def import_plan_file(self, request, file: UploadedFile = File(...)):
        """
        Import file .plan từ QGroundController
        Queue import as background task with WebSocket notifications
        Returns immediately with task_id for tracking
        
        Args:
            file: File .plan được upload
            
        Returns:
            BaseResponse với task_id để track progress qua socket
        """
        try:
            # Validate file extension
            if not file.name.endswith('.plan'):
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.INVALID_PLAN_FORMAT,
                    success=False
                )
            
            # Validate file size (max 50MB)
            if file.size > 50 * 1024 * 1024:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.PLAN_FILE_TOO_LARGE,
                    success=False
                )
            
            # Generate unique task ID for import tracking
            import_task_id = str(uuid.uuid4())
            task_type = "qground_control_import_plan"
            user = request.user
            
            # Read file content into memory for background processing
            file_content = file.read()
            file_name = file.name
            
            # Persist initial task status for client-side polling
            pending_message = get_message(MESSAGE_ENUM.IMPORT_PLAN_SUCCESS)  # Có thể tạo message riêng cho pending
            TaskStatusService.create_or_update(
                task_id=import_task_id,
                task_type=task_type,
                category=TaskStatus.Category.UPLOAD,
                user=user,
                status="pending",
                message=pending_message,
                action="qground_control_import_plan",
                task_channel=f"terminals_{user.username}",
                trigger_source="qground_control.import_plan",
                related_model="terminals.Routes",
            )
            
            # Start background thread for import processing
            import_thread = threading.Thread(
                target=_process_import_plan_in_thread,
                args=(file_content, file_name, import_task_id, user.id),
                daemon=True
            )
            import_thread.start()
            
            return BaseResponse(
                status_code=200,
                message=pending_message,
                data={
                    'task_id': import_task_id,
                    'status': 'pending',
                    'message': pending_message
                }
            )
                
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"{MESSAGE_ENUM.IMPORT_PLAN_FAILED}: {str(e)}",
                success=False
            )

    @route.post("/import-plans", auth=CustomJWTAuth())
    def import_plan_files(self, request, files: List[UploadedFile] = File(...), route_service_id: int | None = Form(None)):
        """
        Import nhiều file .plan từ QGroundController.
        Mỗi file được xử lý giống hệt endpoint /import-plan: tạo TaskStatus + chạy background thread.
        
        Args:
            files: Danh sách file .plan được upload (multipart)
        
        Returns:
            BaseResponse với danh sách task_id để track progress cho từng file
        """
        try:
            if not files:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.INVALID_PLAN_FORMAT,
                    success=False
                )
            
            user = request.user
            task_type = "qground_control_import_plan"
            pending_message = get_message(MESSAGE_ENUM.IMPORT_PLAN_SUCCESS)
            
            accepted = []
            rejected = []
            
            for file in files:
                # Validate file extension
                if not file.name.endswith('.plan'):
                    rejected.append({
                        "file_name": getattr(file, "name", None),
                        "error": MESSAGE_ENUM.INVALID_PLAN_FORMAT,
                    })
                    continue
                
                # Validate file size (max 50MB)
                if file.size > 50 * 1024 * 1024:
                    rejected.append({
                        "file_name": getattr(file, "name", None),
                        "error": MESSAGE_ENUM.PLAN_FILE_TOO_LARGE,
                    })
                    continue
                
                import_task_id = str(uuid.uuid4())
                if route_service_id:
                    service = int(route_service_id)
                else:
                    service = None
                # Read file content into memory for background processing
                file_content = file.read()
                file_name = file.name
                
                # Persist initial task status for client-side polling
                TaskStatusService.create_or_update(
                    task_id=import_task_id,
                    task_type=task_type,
                    category=TaskStatus.Category.UPLOAD,
                    user=user,
                    status="pending",
                    message=pending_message,
                    action="qground_control_import_plan",
                    task_channel=f"terminals_{user.username}",
                    trigger_source="qground_control.import_plan",
                    related_model="terminals.Routes",
                )
                
                # Start background thread for import processing
                import_thread = threading.Thread(
                    target=_process_import_plan_in_thread,
                    args=(file_content, file_name, import_task_id, user.id, service),
                    daemon=True
                )
                import_thread.start()
                
                accepted.append({
                    "file_name": file_name,
                    "task_id": import_task_id,
                    "status": "pending",
                    "message": pending_message,
                })
            
            if not accepted:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.IMPORT_PLAN_FAILED,
                    data={
                        "accepted": [],
                        "rejected": rejected,
                        "total_files": len(files),
                        "accepted_count": 0,
                        "rejected_count": len(rejected),
                    },
                    success=False
                )
            
            return BaseResponse(
                status_code=200,
                message=pending_message,
                data={
                    "accepted": accepted,
                    "rejected": rejected,
                    "total_files": len(files),
                    "accepted_count": len(accepted),
                    "rejected_count": len(rejected),
                }
            )
        
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"{MESSAGE_ENUM.IMPORT_PLAN_FAILED}: {str(e)}",
                success=False
            )
    
    @route.post("/export-plan", auth=CustomJWTAuth())
    def export_routes_to_plans(self, request, data: QGroundControlPlanExportSchema):
        """
        Export routes thành các file .plan cho QGroundController
        
        Args:
            data: Schema chứa danh sách route IDs cần export
            
        Returns:
            ZIP file chứa các file .plan
        """
        try:
            # Validate route IDs
            if not data.route_ids:
                return BaseResponse(
                    status_code=400,
                    message="At least one route ID must be provided",
                    success=False
                )
            
            # Export routes to plans
            exported_files = self.service.export_routes_to_plans(data.route_ids)
            
            if not exported_files:
                return BaseResponse(
                    status_code=404,
                    message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                    success=False
                )
            
            # Create ZIP file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename, content in exported_files:
                    zip_file.writestr(filename, content)
            
            # Prepare response
            zip_buffer.seek(0)
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )
            response['Content-Disposition'] = 'attachment; filename="qground_control_plans.zip"'
            response['Content-Length'] = len(zip_buffer.getvalue())
            
            return response
            
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                success=False
            )
    
    @route.get("/export-single-plan/{route_id}", auth=CustomJWTAuth())
    def export_single_route_to_plan(self, request, route_id: int):
        """
        Export một route thành file .plan đơn lẻ
        
        Args:
            route_id: ID của route cần export
            
        Returns:
            File .plan đơn lẻ
        """
        try:
            # Export single route to plan
            exported_files = self.service.export_routes_to_plans([route_id])
            
            if not exported_files:
                return BaseResponse(
                    status_code=404,
                    message=f"Route with ID {route_id} not found",
                    success=False
                )
            
            # Get the single exported file
            filename, content = exported_files[0]
            
            # Prepare response
            response = HttpResponse(
                content,
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(content)
            
            return response
            
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                success=False
            )

    @route.get("/mavlink-frames", auth=CustomJWTAuth())
    def get_mavlink_frames(self, request, query: MavlinkFrameQuerySchema = Query(...)):
        """
        Lấy danh sách MAVLink frames từ FLIGHTBRID
        
        Args:
            query: Query parameters cho phân trang và tìm kiếm
            
            Returns:
            BaseResponse với danh sách MAVLink frames
        """
        try:
            # Get FLIGHTBRID_URL from environment
            flightbrid_url = os.getenv('FLIGHTBRID_URL')
            if not flightbrid_url:
                return BaseResponse(
                    status_code=500,
                    message="FLIGHTBRID_URL not configured",
                    success=False
                )
            
            # Prepare query parameters
            params = {
                'page': query.page,
                'pageSize': query.pageSize
            }
            
            # Add searchTerm if provided
            if query.searchTerm:
                params['searchTerm'] = query.searchTerm
            
            # Add category if provided
            if query.category:
                params['category'] = query.category
            
            # Call API to FLIGHTBRID
            headers = get_gcs_api_headers()
            
            # Debug: Log headers (hide API key)
            logger.debug(f"[GCS_API] Calling: {flightbrid_url}/api/drone/mavlink-frames")
            logger.debug(f"[GCS_API] Headers: {dict((k, '***' if k == 'Authorization' else v) for k, v in headers.items())}")
            
            response = requests.get(
                f"{flightbrid_url}/api/drone/mavlink-frames",
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return BaseResponse(
                    status_code=200,
                    message="Lấy danh sách MAVLink frames thành công",
                    data=data
                )
            else:
                logger.error(f"[GCS_API] Error {response.status_code} from FLIGHTBRID: {response.text}")
                logger.error(f"[GCS_API] Request URL: {flightbrid_url}/api/drone/mavlink-frames")
                logger.error(f"[GCS_API] Has Authorization header: {'Authorization' in headers}")
                return BaseResponse(
                    status_code=response.status_code,
                    message=f"Error from FLIGHTBRID: {response.text}",
                    success=False
                )
                
        except requests.exceptions.Timeout:
            return BaseResponse(
                status_code=408,
                message="Request timeout to FLIGHTBRID",
                success=False
            )
        except requests.exceptions.ConnectionError:
            return BaseResponse(
                status_code=503,
                message="Cannot connect to FLIGHTBRID",
                success=False
            )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Error retrieving MAVLink frames: {str(e)}",
                success=False
            )

    @route.get("/mavlink-commands", auth=CustomJWTAuth())
    def get_mavlink_commands(self, request, query: MavlinkCommandQuerySchema = Query(...)):
        """
        Lấy danh sách MAVLink commands từ FLIGHTBRID
        
        Args:
            query: Query parameters cho phân trang và tìm kiếm
            
            Returns:
            BaseResponse với danh sách MAVLink commands
        """
        try:
            # Get FLIGHTBRID_URL from environment
            flightbrid_url = os.getenv('FLIGHTBRID_URL')
            if not flightbrid_url:
                return BaseResponse(
                    status_code=500,
                    message="FLIGHTBRID_URL not configured",
                    success=False
                )
            
            # Prepare query parameters
            params = {
                'page': query.page,
                'pageSize': query.pageSize
            }
            
            # Add searchTerm if provided
            if query.searchTerm:
                params['searchTerm'] = query.searchTerm
            
            # Add category if provided
            if query.category:
                params['category'] = query.category
            
            # Call API to FLIGHTBRID
            headers = get_gcs_api_headers()
            
            # Debug: Log headers (hide API key)
            logger.debug(f"[GCS_API] Calling: {flightbrid_url}/api/drone/mavlink-commands")
            logger.debug(f"[GCS_API] Headers: {dict((k, '***' if k == 'Authorization' else v) for k, v in headers.items())}")
            
            response = requests.get(
                f"{flightbrid_url}/api/drone/mavlink-commands",
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return BaseResponse(
                    status_code=200,
                    message="Lấy danh sách MAVLink commands thành công",
                    data=data
                )
            else:
                logger.error(f"[GCS_API] Error {response.status_code} from FLIGHTBRID: {response.text}")
                logger.error(f"[GCS_API] Request URL: {flightbrid_url}/api/drone/mavlink-commands")
                logger.error(f"[GCS_API] Has Authorization header: {'Authorization' in headers}")
                return BaseResponse(
                    status_code=response.status_code,
                    message=f"Error from FLIGHTBRID: {response.text}",
                    success=False
                )
                
        except requests.exceptions.Timeout:
            return BaseResponse(
                status_code=408,
                message="Request timeout to FLIGHTBRID",
                success=False
            )
        except requests.exceptions.ConnectionError:
            return BaseResponse(
                status_code=503,
                message="Cannot connect to FLIGHTBRID",
                success=False
            )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Error retrieving MAVLink commands: {str(e)}",
                success=False
            )
