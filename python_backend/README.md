# CodeScan Python Backend

A source code security audit platform rewritten in Python using FastAPI.

## Features

- **Project Upload**: Upload ZIP files containing source code for analysis
- **Route Analysis**: Automatic API route inventory generation
- **Multi-stage Security Audits**: 
  - RCE (Remote Code Execution)
  - Injection (SQL/NoSQL)
  - Authentication & Session
  - Access Control
  - XSS (Cross-Site Scripting)
  - Configuration & Components
  - File Operations
  - Business Logic
- **Gap Check**: Find missed vulnerabilities
- **Revalidation**: Verify findings
- **HTML Reports**: Export professional security reports

## Requirements

- Python 3.9+
- MySQL 5.7+ or MariaDB 10.3+
- pip

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the system:
```bash
python -m cmd.init
```

This will:
- Create necessary directories (`data/`, `projects/`)
- Generate a configuration file with auth key
- Initialize the MySQL database

3. Start the server:
```bash
python main.py --host 0.0.0.0 --port 8089
```

## Configuration

Configuration is stored in `data/config.json`. You can also use environment variables:

| Environment Variable | Description |
|---------------------|-------------|
| `CODESCAN_AUTH_KEY` | Authentication key for API access |
| `CODESCAN_DB_HOST` | MySQL host (default: 127.0.0.1) |
| `CODESCAN_DB_PORT` | MySQL port (default: 3306) |
| `CODESCAN_DB_USER` | MySQL username (default: root) |
| `CODESCAN_DB_PASSWORD` | MySQL password |
| `CODESCAN_DB_NAME` | Database name (default: codescan) |
| `CODESCAN_AI_API_KEY` | AI/LLM API key |
| `CODESCAN_AI_BASE_URL` | AI/LLM API base URL |
| `CODESCAN_AI_MODEL` | AI model name (default: gemini-3-pro-high) |

## API Endpoints

All endpoints except `/api/login` require authentication via `Authorization: Bearer <auth_key>` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/login` | Authenticate and get token |
| GET | `/api/stats` | Get dashboard statistics |
| GET | `/api/tasks` | List all tasks |
| GET | `/api/tasks/{id}` | Get task details |
| POST | `/api/tasks` | Upload new project |
| DELETE | `/api/tasks/{id}` | Delete a task |
| POST | `/api/tasks/{id}/pause` | Pause running task |
| POST | `/api/tasks/{id}/resume` | Resume paused task |
| POST | `/api/tasks/{id}/stage/{stage}` | Run specific audit stage |
| POST | `/api/tasks/{id}/stage/{stage}/gap-check` | Run gap check |
| POST | `/api/tasks/{id}/stage/{stage}/revalidate` | Revalidate findings |
| POST | `/api/tasks/{id}/repair` | Repair malformed JSON output |
| GET | `/api/tasks/{id}/report` | Export HTML report |

## Project Structure

```
python_backend/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connection & migrations
│   ├── models.py          # SQLAlchemy ORM models
│   ├── api/
│   │   ├── routes.py      # Route registration
│   │   └── handlers/
│   │       ├── auth.py    # Authentication handler
│   │       ├── task.py    # Task handlers
│   │       ├── stats.py   # Statistics handler
│   │       └── report.py  # Report handler
│   ├── services/
│   │   ├── scanner.py     # AI scanning engine
│   │   ├── summary.py     # Statistics aggregation
│   │   └── report.py      # HTML report generation
│   └── utils/
│       └── zip_utils.py   # ZIP file handling
└── cmd/
    └── init.py            # Initialization script
```

## License

MIT License
