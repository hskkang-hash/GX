"""
Service layer for drawing functionality
"""
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from ninja.errors import ValidationError
import logging

from stream_monitors.models import (
    DrawingSession, DrawingElement, DrawingParticipant, StreamMonitor
)
from common.constant import MESSAGE_ENUM

logger = logging.getLogger(__name__)
User = get_user_model()


class DrawingService:
    """Service class for managing drawing sessions and elements"""
    
    @classmethod
    @transaction.atomic
    def create_drawing_session(cls, name: str, stream_monitor_id: int, user):
        """Create a new drawing session"""
        try:
            # Validate stream monitor exists
            try:
                stream_monitor = StreamMonitor.objects.get(id=stream_monitor_id, is_active=True)
            except StreamMonitor.DoesNotExist:
                raise ValidationError("Stream monitor not found or inactive")
            
            # Create drawing session
            session = DrawingSession.objects.create(
                name=name,
                stream_monitor=stream_monitor,
                created_by=user
            )
            
            # Add creator as participant
            DrawingParticipant.objects.create(
                session=session,
                user=user,
                is_online=True
            )
            
            return (True, session)
            
        except Exception as e:
            logger.error(f"Error creating drawing session: {e}")
            return (False, str(e))
    
    @classmethod
    @transaction.atomic
    def update_drawing_session(cls, session_id: int, user, **update_data):
        """Update drawing session"""
        try:
            session = DrawingSession.objects.get(id=session_id, is_active=True)
            
            # Check if user has permission to update
            if session.created_by != user:
                raise ValidationError("You don't have permission to update this session")
            
            # Update session
            for field, value in update_data.items():
                if hasattr(session, field):
                    setattr(session, field, value)
            
            session.save()
            return (True, session)
            
        except DrawingSession.DoesNotExist:
            return (False, "Drawing session not found")
        except Exception as e:
            logger.error(f"Error updating drawing session: {e}")
            return (False, str(e))
    
    @classmethod
    @transaction.atomic
    def delete_drawing_session(cls, session_id: int, user):
        """Delete drawing session"""
        try:
            session = DrawingSession.objects.get(id=session_id, is_active=True)
            
            # Check if user has permission to delete
            if session.created_by != user:
                raise ValidationError("You don't have permission to delete this session")
            
            # Soft delete session
            session.is_active = False
            session.save()
            
            # Mark all elements as deleted
            DrawingElement.objects.filter(session=session).update(is_deleted=True)
            
            return (True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS))
            
        except DrawingSession.DoesNotExist:
            return (False, "Drawing session not found")
        except Exception as e:
            logger.error(f"Error deleting drawing session: {e}")
            return (False, str(e))
    
    @classmethod
    def get_drawing_sessions(cls, stream_monitor_id: int = None):
        """Get all drawing sessions, optionally filtered by stream monitor"""
        try:
            queryset = DrawingSession.objects.filter(is_active=True).select_related(
                'created_by', 'stream_monitor'
            ).annotate(
                participant_count=Count('participants', filter=Q(participants__is_online=True))
            ).order_by('-created_at')
            
            if stream_monitor_id:
                queryset = queryset.filter(stream_monitor_id=stream_monitor_id)
            
            return queryset
            
        except Exception as e:
            logger.error(f"Error getting drawing sessions: {e}")
            return DrawingSession.objects.none()
    
    @classmethod
    def get_drawing_session_detail(cls, session_id: int):
        """Get detailed information about a drawing session"""
        try:
            session = DrawingSession.objects.select_related(
                'created_by', 'stream_monitor'
            ).annotate(
                participant_count=Count('participants', filter=Q(participants__is_online=True))
            ).get(id=session_id, is_active=True)
            
            # Get active elements
            elements = DrawingElement.objects.filter(
                session=session,
                is_deleted=False
            ).select_related('created_by').order_by('created_at')
            
            # Get online participants
            participants = DrawingParticipant.objects.filter(
                session=session,
                is_online=True
            ).select_related('user').order_by('joined_at')
            
            return {
                'session': session,
                'elements': elements,
                'participants': participants
            }
            
        except DrawingSession.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting drawing session detail: {e}")
            return None
    
    @classmethod
    @transaction.atomic
    def create_drawing_element(cls, session_id: int, element_type: str, data: dict, user):
        """Create a new drawing element"""
        try:
            # Validate session exists and is active
            session = DrawingSession.objects.get(id=session_id, is_active=True)
            
            # Create element
            element = DrawingElement.objects.create(
                session=session,
                element_type=element_type,
                data=data,
                created_by=user
            )
            
            return (True, element)
            
        except DrawingSession.DoesNotExist:
            return (False, "Drawing session not found")
        except Exception as e:
            logger.error(f"Error creating drawing element: {e}")
            return (False, str(e))
    
    @classmethod
    @transaction.atomic
    def update_drawing_element(cls, element_id: int, data: dict, user):
        """Update drawing element"""
        try:
            element = DrawingElement.objects.get(
                id=element_id,
                is_deleted=False,
                session__is_active=True
            )
            
            # Update element data
            element.data = data
            element.save()
            
            return (True, element)
            
        except DrawingElement.DoesNotExist:
            return (False, "Drawing element not found")
        except Exception as e:
            logger.error(f"Error updating drawing element: {e}")
            return (False, str(e))
    
    @classmethod
    @transaction.atomic
    def delete_drawing_element(cls, element_id: int, user):
        """Delete drawing element"""
        try:
            element = DrawingElement.objects.get(
                id=element_id,
                is_deleted=False,
                session__is_active=True
            )
            
            # Soft delete element
            element.is_deleted = True
            element.save()
            
            return (True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS))
            
        except DrawingElement.DoesNotExist:
            return (False, "Drawing element not found")
        except Exception as e:
            logger.error(f"Error deleting drawing element: {e}")
            return (False, str(e))
    
    @classmethod
    @transaction.atomic
    def clear_session_elements(cls, session_id: int, user):
        """Clear all elements in a drawing session"""
        try:
            session = DrawingSession.objects.get(id=session_id, is_active=True)
            
            # Mark all elements as deleted
            updated_count = DrawingElement.objects.filter(
                session=session,
                is_deleted=False
            ).update(is_deleted=True)
            
            return (True, f"Cleared {updated_count} elements")
            
        except DrawingSession.DoesNotExist:
            return (False, "Drawing session not found")
        except Exception as e:
            logger.error(f"Error clearing session elements: {e}")
            return (False, str(e))
    
    @classmethod
    @transaction.atomic
    def join_drawing_session(cls, session_id: int, user):
        """Join a drawing session as participant"""
        try:
            session = DrawingSession.objects.get(id=session_id, is_active=True)
            
            # Get or create participant
            participant, created = DrawingParticipant.objects.get_or_create(
                session=session,
                user=user,
                defaults={'is_online': True}
            )
            
            if not created:
                participant.is_online = True
                participant.save()
            
            return (True, participant)
            
        except DrawingSession.DoesNotExist:
            return (False, "Drawing session not found")
        except Exception as e:
            logger.error(f"Error joining drawing session: {e}")
            return (False, str(e))
    
    @classmethod
    @transaction.atomic
    def leave_drawing_session(cls, session_id: int, user):
        """Leave a drawing session"""
        try:
            session = DrawingSession.objects.get(id=session_id, is_active=True)
            
            # Update participant status
            participant = DrawingParticipant.objects.get(session=session, user=user)
            participant.is_online = False
            participant.save()
            
            return (True, "Left session successfully")
            
        except (DrawingSession.DoesNotExist, DrawingParticipant.DoesNotExist):
            return (False, "Session or participation not found")
        except Exception as e:
            logger.error(f"Error leaving drawing session: {e}")
            return (False, str(e))