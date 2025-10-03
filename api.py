from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import asyncio
import socket
import threading
from datetime import datetime, timedelta

from db import get_database, TagDatabase
from paser import TagParser, TagData

logger = logging.getLogger(__name__)

# Pydantic models for API
class TagDataRequest(BaseModel):
    """Request model for tag data submission"""
    raw_data: str = Field(..., description="Raw TAG data string", example="TAG,fa451f0755d8,197,20251003140059.456")

class TagRegistrationRequest(BaseModel):
    """Request model for tag registration"""
    id: str = Field(..., description="Tag ID", example="fa451f0755d8")
    description: str = Field(..., description="Tag description", example="Helmet Tag for worker A")

class TagDataResponse(BaseModel):
    """Response model for tag data submission"""
    success: bool
    message: str
    tag_id: Optional[str] = None
    cnt: Optional[int] = None
    cnt_changed: Optional[bool] = None

class TagRegistrationResponse(BaseModel):
    """Response model for tag registration"""
    success: bool
    message: str
    tag_id: Optional[str] = None

class TagStatusResponse(BaseModel):
    """Response model for tag status"""
    id: str
    description: str
    last_cnt: Optional[int] = None
    last_seen: Optional[str] = None
    status: str  # "registered" or "active"

class RegisteredTagsResponse(BaseModel):
    """Response model for registered tags list"""
    tags: List[TagStatusResponse]
    total_count: int

class SystemStatusResponse(BaseModel):
    """Response model for system status"""
    status: str
    uptime: str
    total_tags: int
    total_records: int
    parser_stats: Dict[str, Any]
    server_info: Dict[str, Any]

class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: str
    uptime: str
    database_status: str
    api_status: str

app = FastAPI(
    title="Access Process Backend API",
    description="Backend system for Edge device tag processing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
parser = TagParser(strict_mode=True)
start_time = datetime.now()
socket_server = None
socket_thread = None

def get_db() -> TagDatabase:
    """Dependency to get database instance"""
    return get_database()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Access Process Backend API")
    
    # Start socket server for tag data reception
    start_socket_server()

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Access Process Backend API")
    
    # Stop socket server
    stop_socket_server()

@app.post("/tags", response_model=TagRegistrationResponse)
async def register_tag(
    request: TagRegistrationRequest,
    db: TagDatabase = Depends(get_db)
):
    """
    Register a new tag
    """
    try:
        success = db.register_tag(request.id, request.description)
        
        if success:
            return TagRegistrationResponse(
                success=True,
                message="Tag registered successfully",
                tag_id=request.id
            )
        else:
            raise HTTPException(
                status_code=409, 
                detail=f"Tag {request.id} is already registered"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tags", response_model=RegisteredTagsResponse)
async def get_registered_tags(db: TagDatabase = Depends(get_db)):
    """
    Get all registered tags and their status
    """
    try:
        registered_tags = db.get_registered_tags()
        
        tag_responses = [
            TagStatusResponse(
                id=tag["id"],
                description=tag["description"],
                last_cnt=tag["last_cnt"],
                last_seen=tag["last_seen"],
                status=tag["status"]
            )
            for tag in registered_tags
        ]
        
        return RegisteredTagsResponse(
            tags=tag_responses,
            total_count=len(tag_responses)
        )
        
    except Exception as e:
        logger.error(f"Error getting registered tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tag/{tag_id}", response_model=TagStatusResponse)
async def get_tag_status(tag_id: str, db: TagDatabase = Depends(get_db)):
    """
    Get status of a specific registered tag
    """
    try:
        tag_status = db.get_registered_tag_status(tag_id)
        
        if not tag_status:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found or not registered")
        
        return TagStatusResponse(
            id=tag_status["id"],
            description=tag_status["description"],
            last_cnt=tag_status["last_cnt"],
            last_seen=tag_status["last_seen"],
            status=tag_status["status"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tag status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", response_model=HealthResponse)
async def health_check(db: TagDatabase = Depends(get_db)):
    """
    Health check endpoint for system monitoring
    """
    try:
        uptime = datetime.now() - start_time
        
        try:
            db.get_statistics()
            db_status = "healthy"
        except:
            db_status = "unhealthy"
        
        return HealthResponse(
            status="healthy" if db_status == "healthy" else "degraded",
            timestamp=datetime.now().isoformat(),
            uptime=str(uptime),
            database_status=db_status,
            api_status="healthy"
        )
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            uptime=str(datetime.now() - start_time),
            database_status="unknown",
            api_status="error"
        )

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "Access Process Backend API",
        "version": "1.0.0",
        "status": "running"
    }


# Socket Server for TAG data reception
def handle_socket_client(client_socket, client_address, db: TagDatabase):
    """Handle individual socket client connection"""
    logger.info(f"Client connected from {client_address}")
    
    try:
        while True:
            data = client_socket.recv(1024).decode('utf-8').strip()
            if not data:
                break
            
            # Parse and process the tag data
            parsed_data = parser.parse_tag_data(data)
            if parsed_data:
                cnt_changed = db.store_tag_data(
                    parsed_data.tag_id,
                    parsed_data.cnt,
                    parsed_data.timestamp
                )
                
                if cnt_changed:
                    logger.info(f"Socket: CNT changed for tag {parsed_data.tag_id}: {parsed_data.cnt}")
                
                # Send acknowledgment
                client_socket.send(b"ACK\n")
            else:
                logger.warning(f"Socket: Invalid data from {client_address}: {data}")
                client_socket.send(b"NACK\n")
                
    except Exception as e:
        logger.error(f"Error handling socket client {client_address}: {e}")
    finally:
        client_socket.close()
        logger.info(f"Client {client_address} disconnected")

def socket_server_thread():
    """Socket server thread function"""
    global socket_server
    
    try:
        socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_server.bind(("localhost", 8888))
        socket_server.listen(5)
        
        logger.info("Socket server listening on localhost:8888")
        
        db = get_database()
        
        while True:
            try:
                client_socket, client_address = socket_server.accept()
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=handle_socket_client,
                    args=(client_socket, client_address, db)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if socket_server:  # Only log if server is supposed to be running
                    logger.error(f"Error accepting socket connection: {e}")
                break
                
    except Exception as e:
        logger.error(f"Socket server error: {e}")
    finally:
        if socket_server:
            socket_server.close()
            socket_server = None

def start_socket_server():
    """Start the socket server"""
    global socket_thread
    
    if socket_thread and socket_thread.is_alive():
        logger.warning("Socket server already running")
        return
    
    socket_thread = threading.Thread(target=socket_server_thread)
    socket_thread.daemon = True
    socket_thread.start()
    logger.info("Socket server thread started")

def stop_socket_server():
    """Stop the socket server"""
    global socket_server, socket_thread
    
    if socket_server:
        socket_server.close()
        socket_server = None
        logger.info("Socket server stopped")
    
    if socket_thread and socket_thread.is_alive():
        socket_thread.join(timeout=5)

if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the API server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
