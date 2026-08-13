import os
import sys
import django
import logging
from typing import Dict, Any, Optional, Tuple
from unittest.mock import patch

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from delivery.services.drone_state_service import DroneStateAnalyzer
from common.drone_state_constants import DroneStatusCode
from devices.models import Device

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DroneStateTest:
    def __init__(self):
        self.analyzer = DroneStateAnalyzer()
        self.test_unit_id = "2_3964623730366239_UDP:0.0.0.0:14556"

    def test_get_drone_state(self) -> None:
        """Test basic state analysis"""
        logger.info(f"Testing state analysis for drone: {self.test_unit_id}")
        
        state_code, message = self.analyzer.analyze_and_update_drone_state(self.test_unit_id)
        
        if state_code:
            logger.info(f"Successfully updated drone state:")
            logger.info(f"State: {state_code}")
            logger.info(f"Message: {message}")
        else:
            logger.error(f"Failed to analyze drone state: {message}")

    def test_get_recent_logs(self) -> None:
        """Test retrieving recent logs"""
        logger.info(f"Testing log retrieval for drone: {self.test_unit_id}")
        
        logs, error_msg = self.analyzer.get_recent_logs(self.test_unit_id)
        
        if error_msg:
            logger.error(f"Error getting logs: {error_msg}")
            return
            
        logger.info(f"Retrieved {len(logs)} logs")
        if logs:
            latest_log = logs[0]
            logger.info("Latest log details:")
            logger.info(f"Timestamp: {latest_log.get('timestamp')}")
            logger.info(f"Message Type: {latest_log.get('msgType')}")
            logger.info(f"Battery Level: {latest_log.get('BatteryLevel')}%")
            logger.info(f"System Status: {latest_log.get('SystemStatus')}")
            logger.info(f"Flight Mode: {latest_log.get('FlightMode')}")
            logger.info(f"Current Mission: {latest_log.get('CurrentMissionId')}")
            
            # Log additional details based on message type
            msg_type = latest_log.get('msgType')
            if msg_type == 'VIBRATION':
                logger.info(f"Vibration (X,Y,Z): {latest_log.get('VibrationX')}, {latest_log.get('VibrationY')}, {latest_log.get('VibrationZ')}")
            elif msg_type == 'RAW_IMU':
                logger.info(f"IMU (X,Y,Z): {latest_log.get('Xacc')}, {latest_log.get('Yacc')}, {latest_log.get('Zacc')}")
            elif msg_type == 'SCALED_IMU2':
                logger.info(f"Temperature: {latest_log.get('Temperature')}")
            elif msg_type in ['GLOBAL_POSITION_INT', 'LOCAL_POSITION_NED']:
                logger.info(f"Position: lat={latest_log.get('latitude')}, lon={latest_log.get('longitude')}")
                logger.info(f"Altitude: {latest_log.get('altitude')}, Speed: {latest_log.get('groundSpeed')}")

    def test_check_conditions(self) -> None:
        """Test various condition checks"""
        logger.info(f"Testing condition checks for drone: {self.test_unit_id}")
        
        # Get logs first
        logs, error_msg = self.analyzer.get_recent_logs(self.test_unit_id)
        if error_msg:
            logger.error(f"Error getting logs: {error_msg}")
            return
            
        if not logs:
            logger.warning("No logs found for testing conditions")
            return
            
        latest_log = logs[0]
        
        # Test each condition
        logger.info("Testing retirement conditions...")
        needs_retirement = self.analyzer.check_retirement_conditions(self.test_unit_id)
        logger.info(f"Needs retirement: {needs_retirement}")
        
        logger.info("Testing maintenance conditions...")
        needs_maintenance = self.analyzer.needs_maintenance(latest_log, logs)
        logger.info(f"Needs maintenance: {needs_maintenance}")
        
        logger.info("Testing mission status...")
        is_on_mission = self.analyzer.is_on_mission(latest_log)
        logger.info(f"Is on mission: {is_on_mission}")
        
        logger.info("Testing availability...")
        is_available = self.analyzer.is_available(latest_log)
        logger.info(f"Is available: {is_available}")

    def test_check_all_drones_state(self) -> None:
        """Test checking all drones state"""
        logger.info("Testing check_all_drones_state method...")

        # Test with actual database
        logger.info("Testing with actual database...")
        results = self.analyzer.check_all_drones_state()
        
        # Log results
        logger.info("Results from actual database:")
        logger.info(f"Success count: {len(results['success'])}")
        logger.info(f"Error count: {len(results['error'])}")
        logger.info(f"Not found count: {len(results['not_found'])}")

        # Test specific cases for each drone in success
        if results['success']:
            logger.info("\nTesting successful drones:")
            for unit_id in results['success'][:3]:  # Test first 3 successful drones
                state_code, message = self.analyzer.analyze_and_update_drone_state(unit_id)
                logger.info(f"Drone {unit_id}:")
                logger.info(f"- State: {state_code}")
                logger.info(f"- Message: {message}")

        # Test error cases
        if results['error']:
            logger.info("\nTesting error cases:")
            for unit_id in results['error'][:3]:  # Test first 3 error cases
                logger.info(f"Checking error case for {unit_id}")
                if unit_id.startswith('device_'):
                    logger.info(f"- Device ID error case (no unit_id): {unit_id}")
                else:
                    state_code, message = self.analyzer.analyze_and_update_drone_state(unit_id)
                    logger.info(f"- Error case result: {state_code}, {message}")

        # Test with mock data
        logger.info("\nTesting with mock data...")
        try:
            # Mock Device.objects.all()
            mock_devices = [
                type('Device', (), {'id': 1, 'unit_id': 'test_drone_1'}),
                type('Device', (), {'id': 2, 'unit_id': None}),  # Test case for missing unit_id
                type('Device', (), {'id': 3, 'unit_id': 'test_drone_3'})
            ]
            
            with patch('devices.models.Device.objects.all', return_value=mock_devices):
                mock_results = self.analyzer.check_all_drones_state()
                
                logger.info("Results from mock data:")
                logger.info(f"Success count: {len(mock_results['success'])}")
                logger.info(f"Error count: {len(mock_results['error'])}")
                logger.info(f"Not found count: {len(mock_results['not_found'])}")
                
                # Verify error case for device with no unit_id
                if 'device_2' in mock_results['error']:
                    logger.info("Successfully detected device with missing unit_id")
                
        except Exception as e:
            logger.error(f"Error in mock testing: {str(e)}")

        # Test error handling
        logger.info("\nTesting error handling...")
        try:
            with patch('devices.models.Device.objects.all', side_effect=Exception("Test database error")):
                error_results = self.analyzer.check_all_drones_state()
                logger.info("Successfully handled database error")
        except Exception as e:
            logger.error(f"Error in error handling test: {str(e)}")

    def run_all_tests(self) -> None:
        """Run all test methods"""
        logger.info("Starting drone state analysis tests...")
        
        logger.info("\n1. Testing basic state analysis...")
        self.test_get_drone_state()
        
        logger.info("\n2. Testing log retrieval...")
        self.test_get_recent_logs()
        
        logger.info("\n3. Testing condition checks...")
        self.test_check_conditions()
        
        
        
        
        logger.info("\nAll tests completed.")
    
    def run_single_test(self) -> None:
        """Run only the main test without multiple iterations"""
        logger.info("Starting single drone state analysis test...")
        
        # Test with actual database only
        logger.info("Testing with actual database...")
        results = self.analyzer.check_all_drones_state()
        
        # Log results
        logger.info("Results from actual database:")
        logger.info(f"Success count: {len(results['success'])}")
        logger.info(f"Error count: {len(results['error'])}")
        logger.info(f"Not found count: {len(results['not_found'])}")
        
        logger.info("\nAll tests completed.")

def main():
    try:
        tester = DroneStateTest()
        # Use single test to avoid multiple iterations
        tester.run_single_test()
        # Uncomment below to run all tests
        # tester.run_all_tests()
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")

if __name__ == "__main__":
    main() 