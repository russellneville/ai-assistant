# Technical Context: Sage Technology Stack

## Core Technologies

### Python Ecosystem
- **Python Version**: 3.9+ (specified in pyproject.toml)
- **Package Management**: pip with setuptools build system
- **Development Tools**: black (formatting), flake8 (linting), mypy (type checking)
- **Testing**: pytest with async support (pytest-asyncio)

### AI/ML Framework Stack
- **CrewAI**: v0.28.0+ for multi-agent orchestration
  - Agent creation and management
  - Task-based execution
  - Crew coordination and communication
- **Amazon Bedrock**: Claude model integration
  - Default model: `us.anthropic.claude-sonnet-4-20250514-v1:0`
  - AWS SDK (boto3) for API access
  - Configurable model parameters and regions

### Web Framework
- **FastAPI**: v0.100.0+ for web server and API endpoints
- **Uvicorn**: v0.23.0+ ASGI server for production deployment
- **WebSockets**: v11.0.0+ for real-time UI communication
- **Jinja2**: v3.1.0+ for HTML template rendering
- **aiofiles**: v23.0.0+ for async file operations

### File System & Monitoring
- **Watchdog**: v3.0.0+ for cross-platform file monitoring
- **pathlib**: Built-in Python for path handling
- **asyncio**: Built-in async/await support throughout

### Configuration & Data
- **PyYAML**: v6.0+ for YAML configuration files
- **Pydantic**: v2.0.0+ for data validation and settings management
- **python-multipart**: v0.0.6+ for form data handling

### CLI & User Interface
- **Typer**: v0.9.0+ for command-line interface
- **Rich**: v13.0.0+ for enhanced terminal output and formatting
- **httpx**: v0.24.0+ for HTTP client operations

## Development Setup

### Project Structure
```
sage/
├── sage/                    # Main package
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # CLI entry point
│   ├── core/               # Core application logic
│   │   ├── sage_main.py    # Main application orchestrator
│   │   ├── bedrock_client.py # AWS Bedrock integration
│   │   └── file_monitor.py # File monitoring system
│   ├── agents/             # CrewAI agents
│   │   ├── base.py         # Agent base classes
│   │   └── crew_manager.py # Crew orchestration
│   ├── config/             # Configuration management
│   │   ├── loader.py       # Config loading and validation
│   │   └── models.py       # Pydantic configuration models
│   ├── context/            # Context and memory management
│   │   ├── memory_bank.py  # Memory bank management
│   │   └── store.py        # Context store operations
│   └── ui/                 # User interface components
│       ├── personality.py  # Personality system
│       ├── web_server.py   # FastAPI web server
│       ├── static/         # Static web assets
│       └── templates/      # HTML templates
├── personality/            # Personality configuration
│   ├── expressions.json   # Emotion mapping
│   └── images/            # Expression images (14 emotions)
├── context-store/         # Global context storage
├── features/              # Feature specifications
├── memory-bank/           # Cline memory bank (this directory)
└── pyproject.toml         # Project configuration
```

### Installation & Dependencies
```bash
# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e .[dev]

# Key dependencies automatically installed:
# - crewai>=0.28.0 (AI agent framework)
# - boto3>=1.34.0 (AWS SDK)
# - fastapi>=0.100.0 (web framework)
# - watchdog>=3.0.0 (file monitoring)
# - pydantic>=2.0.0 (data validation)
```

## Configuration System

### Main Configuration (config.yaml)
```yaml
# Project monitoring configuration
projects:
  - path: "/path/to/project"
    crew_config: "web_development"
    priority: "high"

# Agent crew definitions
crews:
  web_development:
    agents: ["context_curator", "project_monitor", "tech_specialist"]
    specializations: ["javascript", "react", "nodejs"]

# AWS Bedrock configuration
aws:
  region: "us-east-1"
  bedrock:
    model: "us.anthropic.claude-sonnet-4-20250514-v1:0"
    max_tokens: 4096

# Performance tuning
performance:
  file_monitor_frequency: 5      # seconds
  background_frequency: 30       # seconds
  batch_update_interval: 120     # seconds
  max_concurrent_ops: 10

# UI configuration
ui:
  personality:
    expressions_map: "./personality/expressions.json"
    default_emotion: "neutral"
  browser:
    port: 8080
    auto_open: true
```

### Project-Specific Configuration
- **`.sageignore`**: File patterns to ignore during monitoring
- **`.alxyrules`**: Project-specific context importance rules

## AWS Integration

### Bedrock Setup
- **Authentication**: Standard AWS credential chain
  - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  - AWS credentials file (~/.aws/credentials)
  - IAM roles (for EC2/container deployment)
- **Permissions Required**:
  - `bedrock:InvokeModel` for Claude model access
  - `bedrock:GetFoundationModel` for model information
- **Regional Availability**: Bedrock available in specific AWS regions

### Model Configuration
- **Default Model**: Claude Sonnet 4 (2025-05-14 version)
- **Configurable Parameters**:
  - max_tokens: Response length limit
  - temperature: Response creativity (if supported)
  - region: AWS region for Bedrock access

## File Monitoring Technical Details

### Watchdog Integration
- **Event Types**: Created, Modified, Deleted, Moved
- **Recursive Monitoring**: Full directory tree scanning
- **Performance Optimization**:
  - Configurable polling intervals
  - Batch event processing
  - Ignore pattern filtering

### Supported File Types
- **Source Code**: All programming languages
- **Documentation**: .md, .txt, .rst files
- **Configuration**: .json, .yaml, .toml, .ini files
- **Dependencies**: package.json, requirements.txt, Cargo.toml, etc.
- **Build Files**: Makefile, Dockerfile, etc.

## Memory Bank Integration

### Cline Compatibility
- **Format**: Markdown files following Cline memory bank structure
- **Required Files**: projectbrief.md, productContext.md, activeContext.md, systemPatterns.md, techContext.md, progress.md
- **Update Triggers**: File changes, initial analysis, user requests
- **Storage Location**: Project-specific directories

### Context Store Structure
```
context-store/
├── technologies/           # Technology-specific knowledge
│   ├── frameworks/        # React, Django, etc.
│   ├── languages/         # Python, JavaScript, etc.
│   ├── databases/         # PostgreSQL, MongoDB, etc.
│   └── tools/             # Docker, Git, etc.
├── patterns/              # Architectural patterns
├── environments/          # Dev, staging, production
├── domains/               # Business logic areas
└── solutions/             # Common solutions and fixes
```

## Development Workflow

### Local Development
```bash
# Start Sage in development mode
sage run --debug

# Validate configuration
sage validate

# Check system status
sage status

# Initialize new configuration
sage init
```

### Code Quality Tools
```bash
# Format code
black sage/

# Type checking
mypy sage/

# Linting
flake8 sage/

# Run tests
pytest
```

## Performance Considerations

### Resource Management
- **Thread Pool**: Configurable max workers (default: 10)
- **Memory Usage**: Context caching with cleanup
- **File Handles**: Proper cleanup for large projects
- **CPU Usage**: Throttling under high load

### Scalability Factors
- **Project Count**: Tested with multiple simultaneous projects
- **File Count**: Efficient handling of large codebases
- **Update Frequency**: Configurable monitoring intervals
- **Concurrent Operations**: Async processing throughout

## Security Considerations

### Credential Security
- **No Hardcoded Secrets**: All credentials via environment or AWS credential chain
- **File Access**: User-controlled project boundaries
- **Network Security**: Local web server with configurable CORS

### Data Privacy
- **Local Processing**: All analysis done locally
- **AWS Communication**: Only model inference calls to Bedrock
- **File Filtering**: Configurable ignore patterns for sensitive files

## Future Technical Enhancements

### Planned Integrations
- **MCP Tools**: Model Context Protocol tool registry
- **Version Control**: Git integration for change tracking
- **IDE Plugins**: Direct integration with popular editors
- **Container Support**: Docker deployment options

### Performance Improvements
- **Caching Layer**: Redis/SQLite for context caching
- **Incremental Analysis**: Only analyze changed portions
- **Distributed Processing**: Multi-machine deployment support
