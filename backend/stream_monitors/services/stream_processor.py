import os
import cv2
import time
import threading
import numpy as np
import subprocess
import av
from typing import List, Tuple, Optional
from concurrent.futures import Future, ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

def read_rtsp_batch(rtsp_url: str, batch_size: int = 4) -> List[np.ndarray]:
    """Reads a batch of frames from RTSP using PyAV."""
    frames = []
    try:
        container = av.open(rtsp_url, options={
            "rtsp_transport": "tcp",           # reliable transport
            "fflags": "nobuffer",              # disable internal buffering
            "flags": "low_delay",              # reduce decoding latency
            "max_delay": "100000",             # microseconds = 100ms
            "stimeout": "3000000",             # connection timeout = 3s
            "rw_timeout": "3000000",           # read/write timeout = 3s
            "flush_packets": "1",              # flush incomplete packets fast
            "analyzeduration": "0",            # skip long probing
            "probesize": "32",                 # reduce startup probe data
            "reorder_queue_size": "0",         # disable reordering delay
            "ffmpeg_thread_queue_size": "64",  # small internal queue
            "packet_size": "4096"              # reduce UDP/TCP packet size
        })
        for frame in container.decode(video=0):
            img = frame.to_ndarray(format="bgr24")
            frames.append(img)
            if len(frames) >= batch_size:
                break
        container.close()
    except Exception as e:
        logger.warning(f"⚠️ Error reading RTSP frames: {e}")
    return frames

class StreamProcessor:
    def __init__(self, grpc_client, output_file: str, stream_resolution: Tuple[int, int], fps: int = 25, output_url: str = None):
        self.grpc_client = grpc_client
        self.output_file = output_file
        self.stream_resolution = stream_resolution
        self.fps = fps
        self.output_url = output_url
        self.stop_event = threading.Event()
        self.ffmpeg_process = None

    def _start_ffmpeg_stream(self) -> Optional[subprocess.Popen]:
        """
        Start FFmpeg process for streaming to output URL.
        
        Returns:
            subprocess.Popen: FFmpeg process or None if failed
        """
        if not self.output_url:
            logger.warning("⚠️ No output URL provided, skipping FFmpeg stream")
            return None
            
        try:
            logger.info(f"🚀 Starting FFmpeg stream to: {self.output_url}")
            
            # FFmpeg command for RTSP streaming
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{self.stream_resolution[0]}x{self.stream_resolution[1]}',
                '-r', str(self.fps),
                '-i', '-',  # Read from stdin
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-an',  # No audio
                '-f', 'rtsp',
                '-rtsp_transport', 'tcp',
                self.output_url
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

    def _reader_thread(self, input_url: str):
        frame_batch: List[np.ndarray] = []
        last_send_time = time.time()

        # Start FFmpeg stream if output URL is provided
        self.ffmpeg_process = self._start_ffmpeg_stream()
        if self.ffmpeg_process:
            logger.info(f"📡 FFmpeg stream output: {self.output_url}")
        else:
            logger.warning("⚠️ Failed to start FFmpeg stream")

        print("input_url: ", input_url)
        # cap = cv2.VideoCapture(input_url, cv2.CAP_FFMPEG)
        # cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # cap.set(cv2.CAP_PROP_FPS, self.fps)
        logger.info(f"📡 RTSP reader started for {input_url}")
        while not self.stop_event.is_set():
            # ret, frame = cap.read()
            # if not ret:
            #     logger.warning("⚠️ Frame read failed, retrying RTSP...")
            #     cap.release()
            #     time.sleep(2)
            #     cap = cv2.VideoCapture(input_url, cv2.CAP_FFMPEG)
            #     continue

            # frame_batch.append(frame)

            frames = read_rtsp_batch(input_url, batch_size=1)
            if not frames:
                logger.warning("⚠️ Frame read failed, retrying RTSP...")
                time.sleep(2)
                continue

            # Accumulate into batch
            frame_batch.extend(frames)
            now = time.time()
            if len(frame_batch) >= 5 or (now - last_send_time) >= 1.0:
                # print("frame_batch: ", len(frame_batch))
                try:
                    logger.debug(f"🧠 Sending batch of {len(frame_batch)} frames to gRPC...")
                    processed_frames, metadata = self.grpc_client.process_frame_batch(frame_batch)
                    logger.debug(f"✅ gRPC batch processed: {metadata}")
                    # print("processed_frames: ", len(processed_frames))
                    for pf in processed_frames:
                        if self.ffmpeg_process and self.ffmpeg_process.stdin:
                            try:
                                # stream_frame = cv2.resize(pf, self.stream_resolution)
                                self.ffmpeg_process.stdin.write(pf.tobytes())
                                self.ffmpeg_process.stdin.flush()
                            except BrokenPipeError:
                                logger.warning("📡 FFmpeg stream disconnected")
                                self.ffmpeg_process = None
                            except Exception as e:
                                logger.error(f"📡 FFmpeg stream error: {e}")
                                self.ffmpeg_process = None
                except ConnectionError as e:
                    logger.error(f"❌ gRPC connection lost: {e}")
                    # Try to reconnect
                    if self.grpc_client.connect():
                        logger.info("✅ Reconnected to gRPC server")
                        try:
                            processed_frames, metadata = self.grpc_client.process_frame_batch(frame_batch)
                            for pf in processed_frames:
                                # Write to file
                                # writer.write(pf)
                                
                                # Send to FFmpeg stream if available
                                if self.ffmpeg_process and self.ffmpeg_process.stdin:
                                    try:
                                        stream_frame = cv2.resize(pf, self.stream_resolution)
                                        self.ffmpeg_process.stdin.write(stream_frame.tobytes())
                                        self.ffmpeg_process.stdin.flush()
                                    except (BrokenPipeError, Exception) as e:
                                        logger.warning(f"📡 FFmpeg stream error during retry: {e}")
                                        self.ffmpeg_process = None
                        except Exception as retry_e:
                            logger.error(f"❌ gRPC retry failed: {retry_e}")
                    else:
                        logger.error("❌ Failed to reconnect to gRPC server")
                except Exception as e:
                    logger.error(f"❌ gRPC batch processing failed: {e}")
                finally:
                    frame_batch.clear()
                    last_send_time = now

            time.sleep(0.001)

        # cap.release()
        # writer.release()
        
        # Close FFmpeg stream
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.wait(timeout=5)
                logger.info("📡 FFmpeg stream closed")
            except:
                self.ffmpeg_process.kill()
                logger.info("📡 FFmpeg stream terminated")
        
        logger.info("🧹 Reader thread stopped, resources released.")

    def start(self, input_url: str):
        # Ensure gRPC client is connected before starting
        if not self.grpc_client.connected:
            logger.info("🔌 Connecting to gRPC server...")
            if not self.grpc_client.connect():
                logger.error("❌ Failed to connect to gRPC server")
                raise ConnectionError("Could not connect to gRPC server")
            logger.info("✅ Connected to gRPC server")
        
        thread = threading.Thread(target=self._reader_thread, args=(input_url,), daemon=False)
        thread.start()
        # Return both reader (self) and processor_thread for compatibility with calling code
        return self, thread

    def stop(self):
        self.stop_event.set()
        
        # Close FFmpeg stream
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.wait(timeout=5)
                logger.info("📡 FFmpeg stream closed")
            except:
                self.ffmpeg_process.kill()
                logger.info("📡 FFmpeg stream terminated")
        
        # Disconnect gRPC client
        if self.grpc_client and self.grpc_client.connected:
            self.grpc_client.disconnect()
            logger.info("🔌 Disconnected from gRPC server")
