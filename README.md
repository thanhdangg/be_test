# Access Process Backend

Backend system for Edge device tag processing with simulation capabilities. This system processes TAG data in a specific format and provides API endpoints for data submission and monitoring.

## 📋 Overview

This backend system is designed for Access Process operations on Edge devices with the following key features:

- **Tag Simulation**: Generates TAG data in the format `TAG,<tag_id>,<cnt>,<timestamp>`
- **Data Processing**: Parses and validates incoming TAG data
- **State Management**: Tracks last CNT value and timestamp for each tag
- **Logging**: Outputs logs when CNT values change
- **API Endpoints**: RESTful API for data submission and status monitoring
- **Multiple Input Methods**: Supports socket, file output, and standard output

## 📁 Project Structure

```
Backend_Test/
├── main.py              # Main application entry point
├── api.py               # FastAPI web server and endpoints
├── tag_simulator.py     # Tag data simulator
├── paser.py            # TAG data parser
├── db.py               # Database operations
├── requirements.txt     # Python dependencies
├── README.md           # This documentation
└── tags.db             # SQLite database (created at runtime)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Installation

1. **Clone or download the project**
   ```powershell
   cd d:\Backend_Test
   ```

2. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run the complete system**
   ```powershell
   python main.py
   ```

The system will start with:
- API server on `http://localhost:8000`
- Socket server on `localhost:8888`
- Tag simulator generating data every 1-5 seconds

### Basic Usage

**Access the API documentation:**
- Open `http://localhost:8000/docs` for interactive API documentation

**Submit tag data manually:**
```powershell
curl -X POST "http://localhost:8000/api/tags/submit" -H "Content-Type: application/json" -d '{\"raw_data\": \"TAG,fa451f0755d8,197,20251003140059.456\"}'
```

**Get all tags:**
```powershell
curl "http://localhost:8000/api/tags"
```

## 🔧 Configuration Options

### Command Line Arguments

```powershell
python main.py --help
```

**Key options:**
- `--api-host`: API server host (default: 0.0.0.0)
- `--api-port`: API server port (default: 8000)
- `--no-simulator`: Disable tag simulator
- `--simulator-output`: Output method (socket/file/stdout)
- `--tag-ids`: Custom tag IDs for simulation
- `--log-level`: Logging level (DEBUG/INFO/WARNING/ERROR)

### Examples

**Run with custom configuration:**
```powershell
python main.py --api-port 9000 --simulator-output stdout --tag-ids tag001 tag002 tag003
```

**Run API only (no simulator):**
```powershell
python main.py --no-simulator
```

**Run with debug logging:**
```powershell
python main.py --log-level DEBUG
```

## 📊 TAG Data Format

The system processes TAG data in the following format:

```
TAG,<tag_id>,<cnt>,<timestamp>
```

**Example:**
```
TAG,fa451f0755d8,197,20251003140059.456
```

**Format specifications:**
- `TAG`: Fixed prefix
- `tag_id`: Hexadecimal identifier (8-16 characters)
- `cnt`: Counter value (non-negative integer)
- `timestamp`: Format `YYYYMMDDHHMMSS.mmm`

## 🔌 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint with system info |
| GET | `/api/tags` | Get all tag statuses |
| GET | `/api/tags/{tag_id}` | Get specific tag status |
| GET | `/api/tags/{tag_id}/history` | Get tag history |
| GET | `/api/system/status` | System status and statistics |
| GET | `/health` | Health check endpoint |

### Example API Calls

**Get tag status:**
```http
GET /api/tags/fa451f0755d8
```

**Response:**
```json
{
  "tag_id": "fa451f0755d8",
  "last_cnt": 197,
  "last_timestamp": "20251003140059.456",
  "total_updates": 1,
  "first_seen": "20251003140059.456"
}
```

## 🎯 Individual Module Usage

### Tag Simulator

Run the simulator standalone:

```powershell
# Socket output to localhost:8888
python tag_simulator.py --output socket

# File output
python tag_simulator.py --output file

# Standard output
python tag_simulator.py --output stdout

# Custom tags
python tag_simulator.py --tags tag001 tag002 tag003 tag004
```

### API Server Only

```powershell
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Database Testing

```powershell
python db.py
```

### Parser Testing

```powershell
python paser.py
```

## 📈 Monitoring and Logging

### Log Files
- Console output: Real-time system logs
- File output: `access_process.log`

### Key Log Events
- TAG data reception and processing
- CNT value changes
- Database operations
- System status updates
- Error conditions


## 🔧 Development

### Testing

Run individual module tests:
```powershell
# Test database
python db.py

# Test parser
python paser.py

# Test simulator
python tag_simulator.py --output stdout
```

## 🛠️ Troubleshooting

### Common Issues

**Port already in use:**
```
Error: [Errno 98] Address already in use
```
Solution: Change ports using `--api-port` or `--simulator-port`

**Permission denied:**
```
Error: [Errno 13] Permission denied
```
Solution: Run with administrator privileges or use ports > 1024

**Module import errors:**
```
ModuleNotFoundError: No module named 'fastapi'
```
Solution: Install requirements: `pip install -r requirements.txt`

### Debug Mode

Enable debug logging for detailed information:
```powershell
python main.py --log-level DEBUG
```

### Database Issues

If database corruption occurs:
1. Stop the system
2. Delete `tags.db`
3. Restart the system (database will be recreated)

**System Status Dashboard:** `http://localhost:8000/docs`  
**Health Check:** `http://localhost:8000/health`  
**API Documentation:** `http://localhost:8000/docs`
