import asyncio
import json, time, os
from signalrcore.hub_connection_builder import HubConnectionBuilder
import logging
logger = logging.getLogger(__name__)

class SignalRClient:
    def __init__(self):
        self.hub_url = os.environ.get('SIGNALR_HUB_URL', 'http://localhost:5000/web-hub')
        
        self.connection = HubConnectionBuilder()\
            .with_url(self.hub_url)\
            .with_automatic_reconnect({
                "type": "interval",
                "keep_alive_interval": 10,
                "reconnect_interval": 5,
                "max_attempts": 5
            })\
            .build()
        
        self.connection.on_open(lambda: self._on_connection_open())
        self.connection.on_close(lambda: self._on_connection_close())
        self.connection.on_error(lambda data: self._on_error(data))
        
        self.drones = []
        self.connect()
    
    
    def connect(self):
        print("Attempting to connect...")
        self.connection.start()
        print("Connected successfully.")
    
    def disconnect(self):
        print("Disconnecting...")
        self.connection.stop()
        print("Disconnected.")

    def handle_drone_state_update(self, drone_states):
        """Handle Event DroneStateUpdate from server"""
        self.drones = drone_states
        print(f"Received {len(drone_states)} drones:")
    
    def get_online_drones(self):
        """Call method GetOnlineDrones on hub"""
        self.drones = [] 
        self.connection.send("GetOnlineDrones", []) 
        self.connection.on("OnlineDronesResult", self.handle_drone_state_update)
        time.sleep(0.3) 
        return self.drones



# Singleton instance
signalr_client = SignalRClient() 