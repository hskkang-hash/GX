import requests
import logging
from django.conf import settings
from stream_monitors.models import StreamMonitor, StreamMonitorAIModel

logger = logging.getLogger(__name__)


def get_stream_url(stream_monitor_instance, is_ai_model: bool = False):
    """
    Get the stream URL for a stream monitor instance.
    
    Args:
        stream_monitor_instance: StreamMonitor instance
        is_ai_model: Whether to use AI model stream
        
    Returns:
        str: Stream URL or empty string if failed
    """
    try:
        # Call API to get stream
        api_url = f"{settings.STREAM_URL}/stream/api/streams/{stream_monitor_instance.code}/hls"
        headers = {
            'accept': 'application/json'
        }

        response = requests.get(
            api_url,
            headers=headers,
            timeout=10,
            verify=False
        )

        response_data = response.json()
        # Return the stream_url from response
        stream_hls_endpoint = response_data.get('stream_hls_endpoint', None)
        if stream_hls_endpoint:
            if is_ai_model:
                stream_hls_endpoint = stream_hls_endpoint.replace(".m3u8", "_ai.m3u8")
            return f"{settings.STREAM_URL}/hls/{stream_hls_endpoint}"
        else:
            return ""
        
    except StreamMonitor.DoesNotExist:
        logger.error(f"StreamMonitor with code {stream_monitor_instance.code} not found")
        return ""
    except requests.RequestException as e:
        logger.error(f"Failed to get stream for {stream_monitor_instance.code}: {str(e)}")
        return ""
    except Exception as e:
        logger.error(f"Failed to start stream monitor {stream_monitor_instance.code}: {str(e)}")
        return ""
