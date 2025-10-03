"""
Tag Simulator for Access Process Backend
Generates TAG data in the format: TAG,<tag_id>,<cnt>,<timestamp>
Example: TAG,fa451f0755d8,197,20251003140059.456
"""

import time
import random
import threading
import socket
from datetime import datetime
from typing import Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TagSimulator:
    def __init__(self, tag_ids: List[str] = None, output_method: str = "socket", 
                 host: str = "localhost", port: int = 8888):
        """
        Initialize Tag Simulator
        
        Args:
            tag_ids: List of tag IDs to simulate (minimum 3)
            output_method: "socket", "file", or "stdout"
            host: Socket host for socket output
            port: Socket port for socket output
        """
        self.tag_ids = tag_ids or [
            "fa451f0755d8",
            "ab123c4567ef", 
            "cd789e0123fa"
        ]
        
        if len(self.tag_ids) < 3:
            raise ValueError("Minimum 3 tag IDs required")
            
        self.output_method = output_method
        self.host = host
        self.port = port
        self.counters: Dict[str, int] = {tag_id: 0 for tag_id in self.tag_ids}
        self.running = False
        self.thread = None
        self.socket_conn = None
        self.file_handle = None
        
    def get_timestamp(self) -> str:
        """Generate timestamp in format: YYYYMMDDHHMMSS.mmm"""
        now = datetime.now()
        return now.strftime("%Y%m%d%H%M%S.%f")[:-3] 
    
    def generate_tag_data(self, tag_id: str) -> str:
        """Generate tag data string in required format"""
        self.counters[tag_id] += 1
        timestamp = self.get_timestamp()
        return f"TAG,{tag_id},{self.counters[tag_id]},{timestamp}"
    
    def setup_output(self):
        """Setup output method (socket, file, or stdout)"""
        if self.output_method == "socket":
            try:
                self.socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_conn.connect((self.host, self.port))
                logger.info(f"Connected to socket {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect to socket: {e}")
                raise
                
        elif self.output_method == "file":
            self.file_handle = open("tag_output.log", "a", encoding="utf-8")
            logger.info("Opened file output: tag_output.log")
            
        elif self.output_method == "stdout":
            logger.info("Using stdout output")
            
        else:
            raise ValueError("Invalid output method. Use 'socket', 'file', or 'stdout'")
    
    def send_data(self, data: str):
        """Send data using configured output method"""
        try:
            if self.output_method == "socket" and self.socket_conn:
                self.socket_conn.send((data + "\n").encode())
                
            elif self.output_method == "file" and self.file_handle:
                self.file_handle.write(data + "\n")
                self.file_handle.flush()
                
            elif self.output_method == "stdout":
                print(data)
                
        except Exception as e:
            logger.error(f"Failed to send data: {e}")
    
    def cleanup_output(self):
        """Cleanup output connections/files"""
        if self.socket_conn:
            self.socket_conn.close()
            logger.info("Socket connection closed")
            
        if self.file_handle:
            self.file_handle.close()
            logger.info("File handle closed")
    
    def simulate_tags(self):
        """Main simulation loop"""
        logger.info("Starting tag simulation...")
        
        while self.running:
            try:
                tag_id = random.choice(self.tag_ids)
                tag_data = self.generate_tag_data(tag_id)
                
                self.send_data(tag_data)
                logger.info(f"Sent: {tag_data}")
                
                time.sleep(random.uniform(1, 5))
                
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                break
    
    def start(self):
        if self.running:
            logger.warning("Simulator is already running")
            return
            
        try:
            self.setup_output()
            self.running = True
            self.thread = threading.Thread(target=self.simulate_tags)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Tag simulator started")
            
        except Exception as e:
            logger.error(f"Failed to start simulator: {e}")
            self.running = False
            raise
    
    def stop(self):
        if not self.running:
            logger.warning("Simulator is not running")
            return
            
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
        self.cleanup_output()
        logger.info("Tag simulator stopped")
    
    def get_status(self) -> Dict:
        """Get current simulator status"""
        return {
            "running": self.running,
            "tag_ids": self.tag_ids,
            "counters": self.counters.copy(),
            "output_method": self.output_method,
            "host": self.host if self.output_method == "socket" else None,
            "port": self.port if self.output_method == "socket" else None
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Tag Simulator for Access Process")
    parser.add_argument("--output", choices=["socket", "file", "stdout"], 
                       default="stdout", help="Output method")
    parser.add_argument("--host", default="localhost", help="Socket host")
    parser.add_argument("--port", type=int, default=8888, help="Socket port")
    parser.add_argument("--tags", nargs="+", 
                       default=["fa451f0755d8", "ab123c4567ef", "cd789e0123fa"],
                       help="Tag IDs to simulate")
    
    args = parser.parse_args()
    
    simulator = TagSimulator(
        tag_ids=args.tags,
        output_method=args.output,
        host=args.host,
        port=args.port
    )
    
    try:
        simulator.start()
        logger.info("Press Ctrl+C to stop the simulator")
        
        while simulator.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        simulator.stop()


if __name__ == "__main__":
    main()
