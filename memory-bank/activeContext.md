# Active Context: Sage System State

## Current Status
Sage is initialized and ready for project monitoring. The system has no projects configured. Ready to begin monitoring user-specified projects.

## System Components Status
- ✅ Core system operational and ready
- ✅ Configuration system initialized
- ✅ Web server and UI ready
- ✅ AWS Bedrock integration active
- ⏸️ Project monitoring paused (no projects configured)

## Ready to Configure
When projects are added to the configuration, the system will:
- Monitor files for changes in real-time
- Analyze changes with AI-powered agents
- Build contextual understanding of projects
- Provide intelligent assistance through the web interface

## System Architecture

### Core Components
- **CLI Interface**: Complete with all 6 commands (run, init, status, validate, version, test)
- **Configuration System**: Full Pydantic validation with comprehensive error handling
- **Agent System**: 6 specialized agent types with CrewAI orchestration
- **File Monitor**: Real-time monitoring with ignore patterns
- **AWS Bedrock Client**: LLM integration with Claude models
- **Context Store**: Hierarchical context management with search
- **Memory Bank Manager**: Cline-compatible memory bank system
- **Web Server**: FastAPI server with WebSocket support
- **Web UI**: HTML/CSS/JavaScript interface with personality integration

## Configuration Guide

### Adding Projects
Edit `config.yaml` to add projects:
```yaml
projects:
  - path: "/path/to/project"
    crew_config: "general_development"
    priority: "high"
```

### Crew Configuration Options
- `general_development`: Multi-agent monitoring for general projects
- `python_web_development`: Python/Django/Flask specialized crew
- `javascript_frontend`: React/Vue/Angular specialized crew
- `full_stack_development`: Complete web application monitoring
- `data_science`: ML/AI project specialized monitoring
- `devops_infrastructure`: Infrastructure and deployment focused crew

## Getting Started
1. Edit `config.yaml` to add projects
2. Run `sage validate` to confirm setup
3. Run `sage run` to start monitoring
4. Access web UI at `http://localhost:8080`

## System Capabilities
- Multi-project monitoring with real-time file change detection
- AI-powered code analysis using Claude via AWS Bedrock
- Intelligent context store management with automatic categorization
- Cline-compatible memory bank creation and maintenance
- Personality-driven browser interface with emotional expressions
- Conflict resolution with AI assistance
- Performance monitoring and resource management
- Technology detection and project analysis
