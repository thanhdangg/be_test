import asyncio
import argparse
import logging
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI

from tag_simulator import TagSimulator
from db import get_database
from paser import TagParser
from api import app as fastapi_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('access_process.log')
    ]
)

logger = logging.getLogger(__name__)


class AccessProcessBackend:
    """Main application class for Access Process Backend"""
    
    def __init__(self):
        self.simulator: Optional[TagSimulator] = None
        self.api_server = None
        self.db = None
        self.parser = None
        self.running = False
        self.start_time = datetime.now()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Access Process Backend...")
        
        try:
            self.db = get_database()
            logger.info("Database initialized")
            
            self.parser = TagParser(strict_mode=True)
            logger.info("Parser initialized")
            
            self._register_default_tags()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _register_default_tags(self):
        """Register default tags for simulation"""
        default_tags = [
            ("fa451f0755d8", "Helmet Tag for worker A"),
            ("ab123c4567ef", "Safety Tag for worker B"), 
            ("cd789e0123fa", "Equipment Tag for device C") 
        ]
        
        for tag_id, description in default_tags:
            if not self.db.is_tag_registered(tag_id):
                success = self.db.register_tag(tag_id, description)
                if success:
                    logger.info(f"Registered default tag: {tag_id} - {description}")
                else:
                    logger.warning(f"Failed to register default tag: {tag_id}")
    
    def start_simulator(self, output_method: str = "socket", 
                       host: str = "localhost", port: int = 8888,
                       tag_ids: list = None):
        """Start the tag simulator"""
        try:
            if not tag_ids:
                tag_ids = ["fa451f0755d8", "ab123c4567ef", "cd789e0123fg"]
            
            self.simulator = TagSimulator(
                tag_ids=tag_ids,
                output_method=output_method,
                host=host,
                port=port
            )
            
            self.simulator.start()
            logger.info(f"Tag simulator started with {len(tag_ids)} tags")
            
        except Exception as e:
            logger.error(f"Failed to start simulator: {e}")
            raise
    
    def start_api_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the API server"""
        try:
            config = uvicorn.Config(
                app=fastapi_app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
            
            self.api_server = uvicorn.Server(config)
            logger.info(f"API server starting on {host}:{port}")
            
            server_thread = threading.Thread(
                target=self._run_api_server,
                daemon=True
            )
            server_thread.start()
            
            time.sleep(2)
            logger.info("API server started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise
    
    def _run_api_server(self):
        """Run API server in thread"""
        try:
            asyncio.run(self.api_server.serve())
        except Exception as e:
            logger.error(f"API server error: {e}")
    
    def start_full_system(self, config: dict):
        """Start the complete system with given configuration"""
        logger.info("Starting full Access Process Backend system...")
        
        try:
            self.initialize()
            
            self.start_api_server(
                host=config.get("api_host", "0.0.0.0"),
                port=config.get("api_port", 8000)
            )
            
            if config.get("enable_simulator", True):
                self.start_simulator(
                    output_method=config.get("simulator_output", "socket"),
                    host=config.get("simulator_host", "localhost"),
                    port=config.get("simulator_port", 8888),
                    tag_ids=config.get("tag_ids")
                )
            
            self.running = True
            logger.info("Full system started successfully")
            
            self._print_system_info(config)
            
        except Exception as e:
            logger.error(f"Failed to start full system: {e}")
            self.stop()
            raise
    
    def _print_system_info(self, config: dict):
        """Print system startup information"""
        print("\n" + "="*60)
        print("ACCESS PROCESS BACKEND - SYSTEM STARTED")
        print("="*60)
        print(f"Start time: {self.start_time}")
        print(f"API Server: http://{config.get('api_host', '0.0.0.0')}:{config.get('api_port', 8000)}")
        print(f"API Docs: http://{config.get('api_host', '0.0.0.0')}:{config.get('api_port', 8000)}/docs")
        print(f"Socket Server: {config.get('simulator_host', 'localhost')}:{config.get('simulator_port', 8888)}")
        
        if config.get("enable_simulator", True):
            tag_ids = config.get("tag_ids", ["fa451f0755d8", "ab123c4567ef", "cd789e0123fg"])
            print(f"Simulator: Enabled ({len(tag_ids)} tags)")
            print(f"Tag IDs: {', '.join(tag_ids)}")
        else:
            print("Simulator: Disabled")
        
        print("\nAvailable endpoints:")
        print("  GET  /                     - Root endpoint")
        print("  POST /api/tags/submit      - Submit tag data")
        print("  GET  /api/tags             - Get all tags")
        print("  GET  /api/tags/{tag_id}    - Get specific tag")
        print("  GET  /api/system/status    - System status")
        print("  GET  /health               - Health check")
        print("\nPress Ctrl+C to stop the system")
        print("="*60 + "\n")
    
    def stop(self):
        """Stop all components"""
        logger.info("Stopping Access Process Backend...")
        
        self.running = False
        
        if self.simulator:
            try:
                self.simulator.stop()
                logger.info("Simulator stopped")
            except Exception as e:
                logger.error(f"Error stopping simulator: {e}")
        
        if self.api_server:
            try:
                self.api_server.stop()
                logger.info("API server stopped")
            except Exception as e:
                logger.error(f"Error stopping API server: {e}")
        
        if self.db:
            try:
                self.db.close()
                logger.info("Database closed")
            except Exception as e:
                logger.error(f"Error closing database: {e}")
        
        uptime = datetime.now() - self.start_time
        logger.info(f"System stopped. Total uptime: {uptime}")
    
    def get_status(self) -> dict:
        """Get system status"""
        uptime = datetime.now() - self.start_time
        
        status = {
            "running": self.running,
            "start_time": self.start_time.isoformat(),
            "uptime": str(uptime),
            "components": {
                "database": self.db is not None,
                "parser": self.parser is not None,
                "simulator": self.simulator is not None and self.simulator.running if self.simulator else False,
                "api_server": self.api_server is not None
            }
        }
        
        if self.simulator:
            status["simulator_status"] = self.simulator.get_status()
        
        if self.parser:
            status["parser_stats"] = self.parser.get_stats()
        
        if self.db:
            status["database_stats"] = self.db.get_statistics()
        
        return status
    
    def run_monitoring_loop(self):
        """Run monitoring loop to track system health"""
        logger.info("Starting monitoring loop...")
        
        while self.running:
            try:
                # Log system status every 5 minutes
                if int(time.time()) % 300 == 0:
                    status = self.get_status()
                    logger.info(f"System health check - Uptime: {status['uptime']}")
                    
                    if self.db:
                        stats = self.db.get_statistics()
                        logger.info(f"Database stats - Tags: {stats.get('total_tags', 0)}, "
                                  f"Records: {stats.get('total_records', 0)}")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)


def create_config_from_args(args) -> dict:
    """Create configuration dictionary from command line arguments"""
    return {
        "api_host": args.api_host,
        "api_port": args.api_port,
        "simulator_host": args.simulator_host,
        "simulator_port": args.simulator_port,
        "simulator_output": args.simulator_output,
        "enable_simulator": args.enable_simulator,
        "tag_ids": args.tag_ids,
        "enable_monitoring": args.enable_monitoring
    }


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Access Process Backend for Edge Devices")
    
    # API server options
    parser.add_argument("--api-host", default="0.0.0.0", 
                       help="API server host (default: 0.0.0.0)")
    parser.add_argument("--api-port", type=int, default=8000,
                       help="API server port (default: 8000)")
    
    # Simulator options
    parser.add_argument("--enable-simulator", action="store_true", default=True,
                       help="Enable tag simulator (default: True)")
    parser.add_argument("--no-simulator", dest="enable_simulator", action="store_false",
                       help="Disable tag simulator")
    parser.add_argument("--simulator-host", default="localhost",
                       help="Simulator socket host (default: localhost)")
    parser.add_argument("--simulator-port", type=int, default=8888,
                       help="Simulator socket port (default: 8888)")
    parser.add_argument("--simulator-output", choices=["socket", "file", "stdout"],
                       default="socket", help="Simulator output method (default: socket)")
    parser.add_argument("--tag-ids", nargs="+", 
                       default=["fa451f0755d8", "ab123c4567ef", "cd789e0123fa"],
                       help="Tag IDs for simulation (minimum 3 required)")
    
    # System options
    parser.add_argument("--enable-monitoring", action="store_true", default=True,
                       help="Enable system monitoring loop (default: True)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default="INFO", help="Logging level (default: INFO)")
    
    args = parser.parse_args()
    
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    if len(args.tag_ids) < 3:
        logger.error("Minimum 3 tag IDs required for simulation")
        sys.exit(1)
    
    config = create_config_from_args(args)
    
    app = AccessProcessBackend()
    
    try:
        app.start_full_system(config)
        
        if config.get("enable_monitoring", True):
            app.run_monitoring_loop()
        else:
            while app.running:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        app.stop()


if __name__ == "__main__":
    main()
