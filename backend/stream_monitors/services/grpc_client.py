#!/usr/bin/env python3
"""
gRPC Client for Frame Detection
Sends frame batches to gRPC server and receives processed frames.
"""

import grpc
import cv2
import numpy as np
import time
import uuid
from collections import deque
from typing import List, Tuple
from config import settings

# Import generated gRPC modules
try:
    # Try importing from current directory first
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    import frame_detection_pb2
    import frame_detection_pb2_grpc
except ImportError as e:
    print(f"Warning: gRPC modules not found: {e}")
    print("gRPC functionality will be disabled. To enable:")
    print("1. Ensure frame_detection_pb2.py and frame_detection_pb2_grpc.py exist")
    print("2. Generate them with: python -m grpc_tools.protoc --python_out=. --grpc_python_out=. frame_detection.proto")
    
    # Create dummy classes to prevent import errors
    class DummyFrameDetectionClient:
        def __init__(self, *args, **kwargs):
            pass
        def connect(self):
            return False
        def disconnect(self):
            pass
        def process_frame_batch(self, *args, **kwargs):
            return [], {}
    
    class DummyStreamProcessor:
        def __init__(self, *args, **kwargs):
            pass
        def add_frame(self, frame):
            return []
        def connect(self):
            return False
        def disconnect(self):
            pass
        def get_stats(self):
            return {}
    
    # Use dummy classes
    FrameDetectionClient = DummyFrameDetectionClient
    StreamProcessor = DummyStreamProcessor


class FrameDetectionClient:
    """gRPC client for frame detection service."""
    
    def __init__(self, server_address=settings.AI_GRPC_URL):
        """
        Initialize the gRPC client.
        
        Args:
            server_address: gRPC server address (default: settings.AI_GRPC_URL)
        """
        self.server_address = server_address
        self.channel = None
        self.stub = None
        self.connected = False
        
    def connect(self):
        """Connect to the gRPC server."""
        try:
            self.channel = grpc.insecure_channel(self.server_address)
            self.stub = frame_detection_pb2_grpc.FrameDetectionServiceStub(self.channel)
            
            # Test connection
            grpc.channel_ready_future(self.channel).result(timeout=5)
            self.connected = True
            print(f"Connected to gRPC server at {self.server_address}")
            return True
            
        except grpc.RpcError as e:
            print(f"Failed to connect to gRPC server: {e}")
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the gRPC server."""
        if self.channel:
            self.channel.close()
            self.connected = False
            print("Disconnected from gRPC server")
    
    def process_frame_batch(self, frames: List[np.ndarray], timestamps: List[int] = None) -> Tuple[List[np.ndarray], dict]:
        """
        Process a batch of frames through the gRPC service.
        
        Args:
            frames: List of frames (numpy arrays)
            timestamps: List of timestamps for each frame (optional)
            
        Returns:
            Tuple of (processed_frames, metadata)
        """
        if not self.connected:
            raise ConnectionError("Not connected to gRPC server")
        
        if timestamps is None:
            timestamps = [int(time.time() * 1000000)] * len(frames)  # microseconds
        
        # Create frame batch request
        batch_id = str(uuid.uuid4())
        request = frame_detection_pb2.FrameBatch()
        request.batch_id = batch_id
        request.timestamp = int(time.time() * 1000000)
        
        # Add frames to request
        for i, frame in enumerate(frames):
            # Encode frame as JPEG
            _, encoded_img = cv2.imencode('.jpg', frame)
            frame_data = encoded_img.tobytes()
            
            # Create frame proto
            frame_proto = frame_detection_pb2.Frame()
            frame_proto.image_data = frame_data
            frame_proto.width = frame.shape[1]
            frame_proto.height = frame.shape[0]
            frame_proto.timestamp = timestamps[i]
            frame_proto.format = 'jpeg'
            
            request.frames.append(frame_proto)
        
        try:
            # Send request to server
            start_time = time.time()
            response = self.stub.ProcessFrames(request)
            processing_time = time.time() - start_time
            
            # Extract processed frames
            processed_frames = []
            for frame_with_detections in response.processed_frames:
                # Decode processed frame
                nparr = np.frombuffer(frame_with_detections.frame.image_data, np.uint8)
                processed_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                processed_frames.append(processed_img)
            
            # Create metadata
            metadata = {
                'batch_id': response.batch_id,
                'processing_time_ms': response.processing_time_ms,
                'client_processing_time': processing_time,
                'frames_processed': len(processed_frames),
                'server_timestamp': response.timestamp
            }
            
            return processed_frames, metadata
            
        except grpc.RpcError as e:
            print(f"gRPC error: {e}")
            raise
        except Exception as e:
            print(f"Processing error: {e}")
            raise


class StreamProcessor:
    """Stream processor that uses gRPC for frame detection."""
    
    def __init__(self, server_address=settings.AI_GRPC_URL, batch_size=6, batch_interval=1.0):
        """
        Initialize the stream processor.
        
        Args:
            server_address: gRPC server address
            batch_size: Number of frames per batch (default: 6)
            batch_interval: Time interval between batches in seconds (default: 1.0)
        """
        self.client = FrameDetectionClient(server_address)
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.frame_buffer = deque(maxlen=batch_size * 2)  # Keep some extra frames
        self.timestamp_buffer = deque(maxlen=batch_size * 2)
        self.last_batch_time = 0
        self.total_batches = 0
        self.total_frames = 0
        
    def add_frame(self, frame: np.ndarray, timestamp: int = None) -> List[np.ndarray]:
        """
        Add a frame to the processor and return processed frames if batch is ready.
        
        Args:
            frame: Input frame
            timestamp: Frame timestamp (optional)
            
        Returns:
            List of processed frames (empty if batch not ready)
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000000)
        
        # Add frame to buffer
        self.frame_buffer.append(frame.copy())
        self.timestamp_buffer.append(timestamp)
        
        current_time = time.time()
        
        # Check if we should process a batch
        if (len(self.frame_buffer) >= self.batch_size and 
            current_time - self.last_batch_time >= self.batch_interval):
            
            # Select frames for batch (take the most recent ones)
            batch_frames = list(self.frame_buffer)[-self.batch_size:]
            batch_timestamps = list(self.timestamp_buffer)[-self.batch_size:]
            
            try:
                # Process batch through gRPC
                processed_frames, metadata = self.client.process_frame_batch(
                    batch_frames, batch_timestamps
                )
                
                self.total_batches += 1
                self.total_frames += len(processed_frames)
                self.last_batch_time = current_time
                
                print(f"Batch {self.total_batches}: Processed {len(processed_frames)} frames "
                        f"in {metadata['processing_time_ms']}ms")
                
                return processed_frames
                
            except Exception as e:
                print(f"Error processing batch: {e}")
                return []
        
        return []
    
    def connect(self):
        """Connect to the gRPC server."""
        return self.client.connect()
    
    def disconnect(self):
        """Disconnect from the gRPC server."""
        self.client.disconnect()
    
    def get_stats(self):
        """Get processing statistics."""
        return {
            'total_batches': self.total_batches,
            'total_frames': self.total_frames,
            'buffer_size': len(self.frame_buffer),
            'last_batch_time': self.last_batch_time
        }


def main():
    """Test the gRPC client with sample frames."""
    import argparse
    
    parser = argparse.ArgumentParser(description='gRPC Frame Detection Client Test')
    parser.add_argument('--server', default=settings.AI_GRPC_URL, help='gRPC server address')
    parser.add_argument('--batch-size', type=int, default=6, help='Batch size (default: 6)')
    parser.add_argument('--interval', type=float, default=1.0, help='Batch interval in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    # Create processor
    processor = StreamProcessor(
        server_address=args.server,
        batch_size=args.batch_size,
        batch_interval=args.interval
    )
    
    # Connect to server
    if not processor.connect():
        print("Failed to connect to server")
        return
    
    try:
        # Generate test frames
        print("Generating test frames...")
        for i in range(20):  # Generate 20 test frames
            # Create a random test frame
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Add some content to make it interesting
            cv2.putText(frame, f"Frame {i+1}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Process frame
            processed_frames = processor.add_frame(frame)
            
            if processed_frames:
                print(f"Received {len(processed_frames)} processed frames")
                # Save first processed frame as example
                cv2.imwrite(f"test_grpc_output_{i}.jpg", processed_frames[0])
            
            time.sleep(0.1)  # Simulate frame rate
        
        print(f"Final stats: {processor.get_stats()}")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        processor.disconnect()


if __name__ == '__main__':
    main()
