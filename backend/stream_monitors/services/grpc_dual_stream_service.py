#!/usr/bin/env python3
"""
gRPC Dual Stream Service
Based on stream_detector_grpc_dual.py and start_dual_stream.sh functionality.
Connects to gRPC server, processes streams, captures frames, sends for processing,
receives results, and restreams with dual output (file + stream).
"""

import cv2
import numpy as np
import time
import os
import subprocess
import threading
import logging
from collections import deque
from typing import Optional, Dict, Any, List
from config import settings

# Import gRPC client
try:
    from stream_monitors.services.grpc_client import FrameDetectionClient
except ImportError:
    # Fallback if gRPC client not available
    FrameDetectionClient = None

logger = logging.getLogger(__name__)


def _publish_detection_events(stream_monitor_id, metadata) -> None:
    """`metadata['detections']` 를 K1 이벤트로 넘긴다 (D-284 (1)).

    ★ 실패해도 스트림을 죽이지 않는다. 그러나 **조용히 넘어가지도 않는다** —
      D-284 가 세운 원칙이 정확히 그것이다: *"조용한 성공이 가장 나쁘다."*
      여기서 삼키는 것은 예외이지 **사실**이 아니다. 무엇이 몇 건이었는지 전부 로그에 남는다.

    ★ 커널을 늦게 import 하는 이유
      이 모듈은 Django 앱 로딩 중에도 import 되고, 커널은 `apps.get_model` 을 쓴다.
      최상위에서 끌어오면 앱 레지스트리가 준비되기 전에 닿을 수 있다. 지연 import 는
      순환을 피하려는 편법이 아니라 **로딩 순서에 대한 사실**이다.
    """
    detections = (metadata or {}).get('detections') or []
    if not any(detections):
        # "검출 0건"과 "못 받았다"는 다르다. 0건은 정상이므로 조용히 지난다 —
        # 다만 metadata 에 키가 아예 없으면 그것은 배선이 끊어진 것이다.
        if 'detections' not in (metadata or {}):
            logger.error(
                "❌ [K1] metadata 에 'detections' 키가 없다 — grpc_client 가 검출을 "
                "다시 버리고 있다(D-284 회귀). stream=%s", stream_monitor_id)
        return

    try:
        from stream_monitors.services.detection_event_bridge import publish_detections

        result = publish_detections(
            stream_monitor_id=stream_monitor_id,
            detections_per_frame=detections,
            reason=("AI 검출 파이프라인(gRPC dual stream) — 콜백에는 요청자가 없다. "
                    "이벤트의 소유는 스트림이 정한다 (D-281)"),
        )
    except Exception as exc:  # noqa: BLE001 — 스트림은 계속 흘러야 한다
        logger.error(
            "❌ [K1] 이벤트 기록 실패 stream=%s: %s — **영상은 계속 흐른다.** "
            "이 줄이 보이면 검출은 있었는데 남지 않은 것이다", stream_monitor_id, exc)
        return

    # 분모와 술어를 함께 적는다 (D-271). 만든 것만 세면 버린 것이 안 보인다.
    logger.info(
        "📌 [K1] stream=%s 검출 %s건 → 이벤트 신규 %s · 접힘 %s · 알림대상 %s "
        "(미매핑 %s · 문턱미달 %s · 반려 %s)",
        stream_monitor_id, result.total_seen, result.created, result.folded,
        result.to_notify, sum(result.unmapped_labels.values()),
        result.below_confidence, len(result.rejected))
    for why in result.rejected:
        logger.warning("⚠️ [K1] 커널이 반려: %s", why)


class GrpcDualStreamService:
    """
    gRPC-based dual stream service that processes frames through gRPC server.
    Based on stream_detector_grpc_dual.py functionality.
    """

    # Class variable to track running processes
    _running_processes = {}  # {stream_monitor_id: process_info}

    @classmethod
    def start_grpc_dual_stream(cls, stream_monitor_id: str, input_url: str,
                              output_file: str = None, stream_url: str = None,
                              fps: int = 25, stream_resolution: tuple = (1280, 720),
                              grpc_server: str = settings.AI_GRPC_URL,
                              batch_size: int = 6, batch_interval: float = 1.0) -> Dict[str, Any]:
        """
        Start a gRPC dual output stream process.

        Args:
            stream_monitor_id: ID of the stream monitor
            input_url: Input RTSP stream URL
            output_file: Output file path for saving (optional)
            stream_url: RTSP/RTMP URL for streaming (optional)
            fps: Target frames per second (default: 25)
            stream_resolution: Resolution for streaming (width, height)
            grpc_server: gRPC server address (default: settings.AI_GRPC_URL)
            batch_size: Number of frames per batch (default: 6)
            batch_interval: Time interval between batches in seconds (default: 1.0)

        Returns:
            dict: Process information and status
        """
        try:
            # Check if process is already running
            if stream_monitor_id in cls._running_processes:
                logger.warning(f"gRPC dual stream already running for {stream_monitor_id}")
                return {
                    'success': False,
                    'error': 'Stream already running',
                    'process_id': None
                }

            # Start the gRPC dual stream process in background thread
            process_thread = threading.Thread(
                target=cls._process_grpc_dual_stream,
                args=(stream_monitor_id, input_url, output_file, stream_url,
                      fps, stream_resolution, grpc_server, batch_size, batch_interval),
                daemon=True
            )
            process_thread.start()

            # Store process info
            process_info = {
                'thread': process_thread,
                'stream_monitor_id': stream_monitor_id,
                'input_url': input_url,
                'output_file': output_file,
                'stream_url': stream_url,
                'grpc_server': grpc_server,
                'started_at': time.time(),
                'status': 'starting'
            }
            cls._running_processes[stream_monitor_id] = process_info

            logger.info(f"🚀 Started gRPC dual stream for {stream_monitor_id}")
            logger.info(f"  Input: {input_url}")
            logger.info(f"  Output file: {output_file}")
            logger.info(f"  Stream URL: {stream_url}")
            logger.info(f"  gRPC Server: {grpc_server}")

            return {
                'success': True,
                'stream_monitor_id': stream_monitor_id,
                'input_url': input_url,
                'output_file': output_file,
                'stream_url': stream_url,
                'grpc_server': grpc_server,
                'status': 'starting'
            }

        except Exception as e:
            logger.error(f"❌ Failed to start gRPC dual stream for {stream_monitor_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stream_monitor_id': stream_monitor_id
            }

    @classmethod
    def stop_grpc_dual_stream(cls, stream_monitor_id: str) -> Dict[str, Any]:
        """
        Stop a running gRPC dual stream process.

        Args:
            stream_monitor_id: ID of the stream monitor

        Returns:
            dict: Stop status information
        """
        try:
            if stream_monitor_id not in cls._running_processes:
                return {
                    'success': False,
                    'error': 'No running stream found',
                    'stream_monitor_id': stream_monitor_id
                }

            process_info = cls._running_processes[stream_monitor_id]
            process_info['status'] = 'stopping'

            logger.info(f"🛑 Stopping gRPC dual stream for {stream_monitor_id}")

            return {
                'success': True,
                'stream_monitor_id': stream_monitor_id,
                'status': 'stopping'
            }

        except Exception as e:
            logger.error(f"❌ Failed to stop gRPC dual stream for {stream_monitor_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stream_monitor_id': stream_monitor_id
            }

    @classmethod
    def get_grpc_dual_stream_status(cls, stream_monitor_id: str) -> Dict[str, Any]:
        """
        Get the status of a gRPC dual stream process.

        Args:
            stream_monitor_id: ID of the stream monitor

        Returns:
            dict: Process status information
        """
        if stream_monitor_id not in cls._running_processes:
            return {
                'success': False,
                'error': 'No running stream found',
                'stream_monitor_id': stream_monitor_id,
                'status': 'not_running'
            }

        process_info = cls._running_processes[stream_monitor_id]
        return {
            'success': True,
            'stream_monitor_id': stream_monitor_id,
            'status': process_info.get('status', 'unknown'),
            'input_url': process_info.get('input_url'),
            'output_file': process_info.get('output_file'),
            'stream_url': process_info.get('stream_url'),
            'grpc_server': process_info.get('grpc_server'),
            'started_at': process_info.get('started_at'),
            'running_time': time.time() - process_info.get('started_at', time.time())
        }

    @classmethod
    def _process_grpc_dual_stream(cls, stream_monitor_id: str, input_url: str,
                                 output_file: str, stream_url: str, fps: int,
                                 stream_resolution: tuple, grpc_server: str,
                                 batch_size: int, batch_interval: float):
        """
        Main processing loop for gRPC dual output stream.
        Based on stream_detector_grpc_dual.py process_stream method.
        """
        cap = None
        writer = None
        ffmpeg_process = None
        grpc_client = None

        try:
            logger.info(f"🎬 Starting gRPC dual stream processing for {stream_monitor_id}")
            logger.info(f"Connecting to stream: {input_url}")
            logger.info(f"Connecting to gRPC server: {grpc_server}")

            # Update status
            if stream_monitor_id in cls._running_processes:
                cls._running_processes[stream_monitor_id]['status'] = 'running'

            # Initialize gRPC client
            try:
                if FrameDetectionClient:
                    grpc_client = FrameDetectionClient(server_address=grpc_server)
                    if not grpc_client.connect():
                        logger.warning(f"⚠️ Could not connect to gRPC server at {grpc_server}")
                        logger.warning("⚠️ Continuing without gRPC processing...")
                        grpc_client = None
                    else:
                        logger.info(f"✅ Connected to gRPC server at {grpc_server}")
                else:
                    logger.warning("⚠️ gRPC client not available, processing without gRPC")
                    grpc_client = None
            except Exception as e:
                logger.warning(f"⚠️ gRPC client initialization failed: {str(e)}")
                logger.warning("⚠️ Continuing without gRPC processing...")
                grpc_client = None

            # Set OpenCV backend for better RTSP support
            import os
            os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|buffer_size;1024|analyzeduration;1000000|probesize;1000000'

            # Open input stream with enhanced RTSP settings
            cap = cv2.VideoCapture(input_url)

            # Set comprehensive RTSP properties for stability
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering for real-time processing
            cap.set(cv2.CAP_PROP_FPS, fps)  # Set target FPS
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

            # Additional RTSP-specific settings
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # Test the capture with timeout
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                if cap.isOpened():
                    # Test if we can actually read a frame
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        logger.info(f"✅ Successfully opened and tested input stream: {input_url}")
                        break
                    else:
                        logger.warning(f"⚠️ Stream opened but cannot read frames, retrying... ({retry_count + 1}/{max_retries})")
                        cap.release()
                        time.sleep(2)
                        cap = cv2.VideoCapture(input_url)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        cap.set(cv2.CAP_PROP_FPS, fps)
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                else:
                    logger.warning(f"⚠️ Could not open stream, retrying... ({retry_count + 1}/{max_retries})")
                    time.sleep(2)
                    cap = cv2.VideoCapture(input_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, fps)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

                retry_count += 1

            # Get stream properties
            if cap is not None:
                actual_fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            else:
                # Use FFmpeg input, get properties from stream resolution
                actual_fps = fps
                width, height = 1280, 720  # Default resolution

            logger.info(f"📺 Stream opened successfully!")
            logger.info(f"Resolution: {width}x{height}")
            logger.info(f"FPS: {actual_fps if actual_fps > 0 else 'Unknown (using target: ' + str(fps) + ')'}")
            logger.info(f"Batch size: {batch_size} frames")
            logger.info(f"Batch interval: {batch_interval} seconds")

            # Use actual FPS if available, otherwise use target FPS
            if actual_fps <= 0 or actual_fps > 120:
                actual_fps = fps

            # Setup file writer if output file is provided
            if output_file:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(
                    output_file,
                    fourcc,
                    actual_fps,
                    (width, height)
                )

                if not writer.isOpened():
                    logger.warning(f"⚠️ Could not open output writer for {output_file}")
                    logger.warning("Continuing without file output...")
                    writer = None
                else:
                    logger.info(f"📁 File output: {output_file}")

            # Start FFmpeg stream if stream URL is provided
            if stream_url:
                ffmpeg_process = cls._start_ffmpeg_stream(stream_url, stream_resolution, fps)
                if ffmpeg_process:
                    logger.info(f"📡 Stream output: {stream_url}")
                else:
                    logger.warning("⚠️ Failed to start streaming")
                    stream_url = None

            # Initialize frame processing
            frame_count = 0
            processed_count = 0
            frame_times = deque(maxlen=30)
            last_time = time.time()
            last_sample_time = time.time()
            processed_frames_queue = deque()

            # gRPC batch processing
            frame_batch = []
            batch_start_time = time.time()

            logger.info("🔄 Processing stream... Press Ctrl+C to stop.")

            while True:
                # Check if we should stop
                if stream_monitor_id in cls._running_processes:
                    if cls._running_processes[stream_monitor_id]['status'] == 'stopping':
                        logger.info(f"🛑 Stopping gRPC dual stream for {stream_monitor_id}")
                        break
                else:
                    # Process was removed from tracking, stop
                    break

                # Read frame from either OpenCV or FFmpeg
                if cap is not None:
                    # Use OpenCV
                    ret, frame = cap.read()

                    if not ret or frame is None:
                        logger.warning("⚠️ Failed to read frame. Attempting to reconnect...")

                        # Release current capture
                        cap.release()
                        time.sleep(2)  # Wait a bit longer for reconnection

                        # Try to reconnect with enhanced settings for H.264
                        cap = cv2.VideoCapture(input_url, cv2.CAP_FFMPEG)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        cap.set(cv2.CAP_PROP_FPS, fps)
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        cap.set(cv2.CAP_PROP_TIMEOUT, 10000)  # 10 second timeout

                        # Test the reconnection
                        if cap.isOpened():
                            test_ret, test_frame = cap.read()
                            if test_ret and test_frame is not None and test_frame.size > 0:
                                logger.info("✅ Successfully reconnected to stream")
                            else:
                                logger.warning("⚠️ Reconnected but still cannot read frames")
                                time.sleep(1)
                                continue
                        else:
                            logger.warning("⚠️ Failed to reconnect to stream")
                            time.sleep(1)
                            continue

                    # Validate frame before processing
                    if frame is not None and (frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0):
                        logger.warning("⚠️ Invalid frame received, skipping...")
                        continue
                else:
                    # No valid input source available
                    logger.warning("⚠️ No valid input source available, skipping frame...")
                    time.sleep(0.1)
                    continue

                frame_count += 1

                # Add frame to batch for gRPC processing
                current_time = time.time()
                if grpc_client:
                    frame_batch.append(frame.copy())

                    # Process batch when it reaches batch_size or time interval
                    if (len(frame_batch) >= batch_size or
                        (current_time - batch_start_time) >= batch_interval):

                        try:
                            # Process frame batch through gRPC
                            processed_frames, metadata = grpc_client.process_frame_batch(frame_batch)

                            # Add processed frames to queue
                            for processed_frame in processed_frames:
                                processed_frames_queue.append(processed_frame)
                                processed_count += 1

                            logger.info(f"📊 Processed batch: {len(frame_batch)} frames -> {len(processed_frames)} results")

                            # ── 검출을 K1 이벤트로 넘긴다 (W2-2 · D-284 (1)) ──────────
                            #
                            # ★ 여기가 검출이 **처음으로 남는** 자리다. 이 줄 전까지
                            #   DetectionEvent 는 정의 1건 · 사용 0건이었다.
                            #   AI 서버는 이미 detections 를 돌려주고 있었고
                            #   클라이언트가 버리고 있었을 뿐이다 (proto 실측).
                            #
                            # 배선을 try 안 **별도 블록**에 둔다: 이벤트 기록이 실패해도
                            # 영상 스트림은 계속 흘러야 한다. 반대로 이벤트 기록의 실패를
                            # 조용히 삼키지도 않는다 — 위 gRPC 예외와 **다른 로그**를 남긴다.
                            # 한 덩어리로 묶으면 "AI 가 죽은 것"과 "저장이 죽은 것"이
                            # 같은 줄로 보이고, 그러면 어느 쪽을 고쳐야 하는지 알 수 없다.
                            _publish_detection_events(stream_monitor_id, metadata)

                        except Exception as e:
                            logger.error(f"❌ gRPC batch processing error: {str(e)}")
                            # Continue with original frames if gRPC fails

                        # Reset batch
                        frame_batch = []
                        batch_start_time = current_time

                # Use processed frame if available, otherwise use original
                output_frame = frame
                if processed_frames_queue:
                    output_frame = processed_frames_queue.popleft()

                # Resize frame for streaming if needed
                stream_frame = output_frame.copy()
                if stream_url and ffmpeg_process:
                    stream_frame = cv2.resize(stream_frame, stream_resolution)

                # Write to file if writer is available
                if writer is not None:
                    writer.write(output_frame)

                # Send to FFmpeg stream if process is available
                if ffmpeg_process and ffmpeg_process.stdin:
                    try:
                        ffmpeg_process.stdin.write(stream_frame.tobytes())
                        ffmpeg_process.stdin.flush()
                    except BrokenPipeError:
                        logger.warning("📡 FFmpeg stream disconnected")
                        ffmpeg_process = None
                    except Exception as e:
                        logger.error(f"📡 FFmpeg stream error: {e}")
                        ffmpeg_process = None

                # Save sample frames if requested (every 5 minutes)
                if (current_time - last_sample_time) > 300:  # 5 minutes
                    sample_filename = f"grpc_sample_{int(time.time())}.jpg"
                    cv2.imwrite(sample_filename, output_frame)
                    logger.info(f"📸 Saved sample frame: {sample_filename}")
                    last_sample_time = current_time

                # Calculate FPS
                current_time = time.time()
                frame_times.append(current_time - last_time)
                last_time = current_time

                if len(frame_times) > 0:
                    avg_frame_time = sum(frame_times) / len(frame_times)
                    current_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
                else:
                    current_fps = 0

                # Log status every 30 frames
                if frame_count % 30 == 0:
                    stream_status = "✓" if ffmpeg_process else "✗"
                    file_status = "✓" if writer else "✗"
                    grpc_status = "✓" if grpc_client else "✗"
                    logger.info(f"📊 Frames: {frame_count} | Processed: {processed_count} | "
                              f"FPS: {current_fps:.1f} | Queue: {len(processed_frames_queue)} | "
                              f"File: {file_status} | Stream: {stream_status} | gRPC: {grpc_status}")

        except Exception as e:
            logger.error(f"❌ Error in gRPC dual stream processing for {stream_monitor_id}: {str(e)}")

        finally:
            # Cleanup
            logger.info(f"🧹 Cleaning up gRPC dual stream for {stream_monitor_id}")

            if cap is not None:
                cap.release()

            # Cleanup completed

            if writer is not None:
                writer.release()
                logger.info(f"📁 File saved: {output_file}")

            if ffmpeg_process:
                try:
                    ffmpeg_process.stdin.close()
                    ffmpeg_process.wait(timeout=5)
                    logger.info("📡 FFmpeg stream closed")
                except:
                    ffmpeg_process.kill()
                    logger.info("📡 FFmpeg stream terminated")

            if grpc_client:
                grpc_client.disconnect()
                logger.info("🔌 gRPC client disconnected")

            # Remove from running processes
            if stream_monitor_id in cls._running_processes:
                del cls._running_processes[stream_monitor_id]

            logger.info(f"✅ gRPC dual stream cleanup completed for {stream_monitor_id}")

    @classmethod
    def _start_ffmpeg_stream(cls, stream_url: str, stream_resolution: tuple, fps: int) -> Optional[subprocess.Popen]:
        """
        Start FFmpeg process for streaming.
        Based on stream_detector_grpc_dual.py start_ffmpeg_stream method.
        """
        try:
            logger.info(f"🚀 Starting FFmpeg stream to: {stream_url}")

            # FFmpeg command for streaming
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{stream_resolution[0]}x{stream_resolution[1]}',
                '-r', str(fps),
                '-i', '-',  # Read from stdin
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-an',  # No audio
                '-f', 'rtsp',
                '-rtsp_transport', 'tcp',
                stream_url
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            logger.info(f"✅ FFmpeg stream started (PID: {process.pid})")
            return process

        except Exception as e:
            logger.error(f"❌ Failed to start FFmpeg stream: {e}")
            return None
