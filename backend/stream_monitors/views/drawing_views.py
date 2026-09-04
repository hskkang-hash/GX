"""
API views for drawing functionality
"""
from ninja_extra import api_controller, route
from core.role.permission import path_permission
from core.common.base_response import BaseResponse
from common.constant import MESSAGE_ENUM
from ninja_jwt.authentication import JWTAuth

from stream_monitors.schemas.schemas_djantic_in import (
    DrawingSessionCreateInSchema, DrawingSessionUpdateInSchema,
    DrawingElementCreateInSchema, DrawingElementUpdateInSchema
)
from stream_monitors.schemas.schemas_djantic_out import (
    DrawingSessionOutSchema, DrawingSessionDetailOutSchema,
    DrawingElementOutSchema
)
from stream_monitors.services.drawing_services import DrawingService
from core.api.v1.auth import CustomJWTAuth


@api_controller('/drawing', tags=['Drawing'])
class DrawingAPI:

    @route.get('/sessions', auth=CustomJWTAuth())
    @path_permission('stream_monitors.view_drawingsession')
    def get_drawing_sessions(self, request, stream_monitor_id: int = None):
        """Get all drawing sessions"""
        try:
            sessions = DrawingService.get_drawing_sessions(stream_monitor_id)
            sessions_out = DrawingSessionOutSchema.from_queryset(sessions, many=True)

            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DRAWING_SESSIONS_SUCCESS, "Drawing sessions retrieved successfully"),
                data=sessions_out
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to retrieve drawing sessions: {str(e)}"
            )

    @route.post('/sessions', auth=JWTAuth())
    @path_permission('stream_monitors.add_drawingsession')
    def create_drawing_session(self, request, data: DrawingSessionCreateInSchema):
        """Create a new drawing session"""
        try:
            success, result = DrawingService.create_drawing_session(
                name=data.name,
                stream_monitor_id=data.stream_monitor_id,
                user=request.user
            )

            if success:
                session_out = DrawingSessionOutSchema.from_queryset(result, many=False)
                return BaseResponse(
                    status_code=201,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_DRAWING_SESSION_SUCCESS, "Drawing session created successfully"),
                    data=session_out
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=result
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to create drawing session: {str(e)}"
            )

    @route.get('/sessions/{session_id}', auth=CustomJWTAuth())
    @path_permission('stream_monitors.view_drawingsession')
    def get_drawing_session_detail(self, request, session_id: int):
        """Get detailed information about a drawing session"""
        try:
            result = DrawingService.get_drawing_session_detail(session_id)

            if result:
                session_out = DrawingSessionOutSchema.from_queryset(result['session'], many=False)
                elements_out = DrawingElementOutSchema.from_queryset(result['elements'], many=True)

                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DRAWING_SESSION_DETAIL_SUCCESS, "Drawing session detail retrieved successfully"),
                    data={
                        'session': session_out,
                        'elements': elements_out,
                        'participant_count': len(result['participants'])
                    }
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=404,
                    message="Drawing session not found"
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to retrieve drawing session detail: {str(e)}"
            )

    @route.put('/sessions/{session_id}', auth=JWTAuth())
    @path_permission('stream_monitors.change_drawingsession')
    def update_drawing_session(self, request, session_id: int, data: DrawingSessionUpdateInSchema):
        """Update a drawing session"""
        try:
            update_data = {k: v for k, v in data.dict().items() if v is not None}
            success, result = DrawingService.update_drawing_session(
                session_id=session_id,
                user=request.user,
                **update_data
            )

            if success:
                session_out = DrawingSessionOutSchema.from_queryset(result, many=False)
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_DRAWING_SESSION_SUCCESS, "Drawing session updated successfully"),
                    data=session_out
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=result
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to update drawing session: {str(e)}"
            )

    @route.delete('/sessions/{session_id}', auth=JWTAuth())
    @path_permission('stream_monitors.delete_drawingsession')
    def delete_drawing_session(self, request, session_id: int):
        """Delete a drawing session"""
        try:
            success, message = DrawingService.delete_drawing_session(
                session_id=session_id,
                user=request.user
            )

            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=message
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED)
            )

    @route.post('/sessions/{session_id}/join', auth=JWTAuth())
    @path_permission('stream_monitors.view_drawingsession')
    def join_drawing_session(self, request, session_id: int):
        """Join a drawing session"""
        try:
            success, result = DrawingService.join_drawing_session(
                session_id=session_id,
                user=request.user
            )

            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.JOIN_DRAWING_SESSION_SUCCESS, "Joined drawing session successfully"),
                    data={'websocket_url': f'/ws/drawing/session/{session_id}/'}
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=result
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to join drawing session: {str(e)}"
            )

    @route.post('/sessions/{session_id}/leave', auth=JWTAuth())
    @path_permission('stream_monitors.view_drawingsession')
    def leave_drawing_session(self, request, session_id: int):
        """Leave a drawing session"""
        try:
            success, message = DrawingService.leave_drawing_session(
                session_id=session_id,
                user=request.user
            )

            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.LEAVE_DRAWING_SESSION_SUCCESS, "Left drawing session successfully")
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=message
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to leave drawing session: {str(e)}"
            )

    @route.post('/sessions/{session_id}/clear', auth=JWTAuth())
    @path_permission('stream_monitors.change_drawingsession')
    def clear_session_elements(self, request, session_id: int):
        """Clear all drawing elements in a session"""
        try:
            success, message = DrawingService.clear_session_elements(
                session_id=session_id,
                user=request.user
            )

            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.CLEAR_DRAWING_ELEMENTS_SUCCESS, "Drawing elements cleared successfully")
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=message
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to clear drawing elements: {str(e)}"
            )

    @route.post('/elements', auth=JWTAuth())
    @path_permission('stream_monitors.add_drawingelement')
    def create_drawing_element(self, request, data: DrawingElementCreateInSchema):
        """Create a new drawing element"""
        try:
            success, result = DrawingService.create_drawing_element(
                session_id=data.session_id,
                element_type=data.element_type,
                data=data.data,
                user=request.user
            )

            if success:
                element_out = DrawingElementOutSchema.from_queryset(result, many=False)
                return BaseResponse(
                    status_code=201,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_DRAWING_ELEMENT_SUCCESS, "Drawing element created successfully"),
                    data=element_out
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=result
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to create drawing element: {str(e)}"
            )

    @route.put('/elements/{element_id}', auth=JWTAuth())
    @path_permission('stream_monitors.change_drawingelement')
    def update_drawing_element(self, request, element_id: int, data: DrawingElementUpdateInSchema):
        """Update a drawing element"""
        try:
            success, result = DrawingService.update_drawing_element(
                element_id=element_id,
                data=data.data,
                user=request.user
            )

            if success:
                element_out = DrawingElementOutSchema.from_queryset(result, many=False)
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_DRAWING_ELEMENT_SUCCESS, "Drawing element updated successfully"),
                    data=element_out
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=result
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=f"Failed to update drawing element: {str(e)}"
            )

    @route.delete('/elements/{element_id}', auth=JWTAuth())
    @path_permission('stream_monitors.delete_drawingelement')
    def delete_drawing_element(self, request, element_id: int):
        """Delete a drawing element"""
        try:
            success, message = DrawingService.delete_drawing_element(
                element_id=element_id,
                user=request.user
            )

            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
                )
            else:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=message
                )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED)
            )
