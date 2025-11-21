# Sage - AI Project Context Assistant

## Project Overview

Sage is an intelligent agentic assistant that monitors project folders and maintains context stores for AI code assistants. It uses CrewAI for multi-agent orchestration and Amazon Bedrock (Claude) for intelligent analysis. The system provides a personality-driven browser interface with emotional expressions and real-time monitoring capabilities.

**Current Status**: MVP-03 ACTIVE DEVELOPMENT - Core system operational with ongoing advanced feature development ✅

## Core Architecture

### Multi-Agent System (CrewAI)
- **6 Specialized Agent Types**: Context Curator, Project Monitor, Technology Specialist, Decision Logger, Conflict Resolver, Performance Monitor
- **Dynamic Crew Configuration**: 6 different crew templates for various project types (general_development, python_web_development, javascript_frontend, full_stack_development, data_science, devops_infrastructure)
- **Advanced Analysis**: Multi-phase analysis workflows with impact assessment, pattern recognition, and context quality scoring

### Technology Stack
- **Python 3.9+** with full async/await architecture
- **CrewAI v0.28.0+** for agent orchestration
- **AWS Bedrock** with Claude Sonnet 4 integration
- **FastAPI + WebSockets** for real-time web interface
- **Watchdog** for cross-platform file monitoring
- **Pydantic v2** for configuration validation

### Key Features
- **Multi-Project Monitoring**: Simultaneous monitoring of multiple software projects
- **Personality System**: 15 emotional expressions with intelligent context mapping and duration-based video timing
- **Real-time Analysis**: File changes trigger intelligent context analysis immediately
- **Memory Bank Integration**: Cline-compatible memory bank format
- **Web UI**: Complete browser interface with real-time updates and activity indicators

## Current Implementation Status

### ✅ COMPLETED COMPONENTS (100% Functional)
- **CLI Interface**: All 6 commands (run, init, status, validate, version, test)
- **Configuration System**: Pydantic validation with hierarchical structure
- **Agent Framework**: All 6 agents with 9 specialized tools
- **File Monitoring**: Real-time monitoring with ignore patterns
- **Context Management**: Global context store and memory bank system
- **AWS Integration**: Complete Bedrock client with health checks
- **Web Server & UI**: FastAPI server with WebSocket support
- **Personality System**: 15 emotional expressions with video timing

### Recent Enhancements (MVP-03)
- **Two-Video Sleep Sequence System**: Robust state management with sleep/wake transitions
- **Enhanced Video State Management**: Improved reliability and user experience
- **Performance Optimization**: Context caching and efficient resource management
- **UI/UX Improvements**: Better visual feedback and responsive design
- **Advanced Monitoring**: Cross-project context sharing and intelligent analysis
- **State Persistence**: Reliable video state tracking across page interactions

## Configuration & Setup

### Installation
```bash
pip install -e .
sage init                    # Create initial configuration
sage validate               # Check configuration and dependencies
sage run                    # Start monitoring projects
```

### Configuration Structure (config.yaml)
```yaml
projects:
  - path: "/path/to/project"
    crew_config: "web_development"
    priority: "high"

crews:
  web_development:
    agents: ["context_curator", "project_monitor", "tech_specialist"]

aws:
  region: "us-east-1"
  bedrock:
    model: "us.anthropic.claude-sonnet-4-20250514-v1:0"
```

## Development Patterns

### Code Quality Standards
- **Type Hints**: Full mypy compliance required
- **Async/Await**: Consistent async patterns throughout codebase
- **Error Handling**: Comprehensive exception handling with logging
- **Configuration Validation**: Pydantic models with clear error messages

### Architecture Patterns
- **Event-Driven**: File monitoring triggers agent analysis
- **Registry Pattern**: Agent types registered for dynamic instantiation
- **Configuration-Driven**: Behavior controlled through YAML configuration
- **Dependency Injection**: Configuration-driven component initialization

### UI Modification Process
**CRITICAL**: The web server dynamically generates UI files on startup. To make persistent changes:
1. Edit methods in `sage/ui/web_server.py` (not the generated files)
2. `create_html_template()` for HTML changes
3. `create_css_styles()` for CSS changes  
4. `create_javascript()` for JavaScript changes
5. Restart server to regenerate files

## Project Structure
```
sage/
├── sage/                    # Main package
│   ├── cli.py              # CLI entry point
│   ├── core/               # Core application logic
│   ├── agents/             # CrewAI agents and tools
│   ├── config/             # Configuration management
│   ├── context/            # Context and memory management
│   └── ui/                 # User interface components
├── personality/            # Personality configuration & videos
├── context-store/         # Global context storage
├── memory-bank/           # Cline memory bank
└── pyproject.toml         # Project configuration
```

## Context Management

### Memory Bank Structure (Cline Compatible)
- `activeContext.md`: Current development state and recent enhancements
- `productContext.md`: User experience goals and target personas
- `progress.md`: Implementation status and milestones
- `projectbrief.md`: Core mission and success criteria
- `systemPatterns.md`: Architecture patterns and component relationships
- `techContext.md`: Technology stack and development setup

### Global Context Store Hierarchy
```
context-store/
├── technologies/           # Frameworks, languages, databases, tools
├── patterns/              # Architectural and design patterns
├── environments/          # Dev, staging, production
├── domains/               # Business logic areas
└── solutions/             # Common solutions and fixes
```

## Key Development Insights

### Technical Success Factors
1. **Agent Intelligence**: Multi-phase analysis provides comprehensive project understanding
2. **Performance**: Async architecture handles multiple large projects efficiently
3. **Reliability**: Comprehensive error handling with graceful degradation
4. **User Experience**: Personality system creates engaging interactions
5. **Video System**: Duration-based timing provides smooth real-time experience

### Architecture Decisions (Confirmed Good)
- **CrewAI Framework**: Excellent structure for multi-agent coordination
- **Pydantic Configuration**: Type safety and validation working excellently
- **FastAPI + WebSockets**: Good foundation for real-time web interface
- **Personality System**: Unique differentiator with well-designed emotion mapping

### Performance Optimizations
- **Async/Await Throughout**: Non-blocking operations for scalability
- **Batching and Throttling**: File events batched with configurable frequencies
- **Resource Management**: Thread pool limits, memory cleanup, file handle management
- **Caching Strategies**: Context store and agent result caching

## Usage Workflows

### Daily Development
1. Developer works normally on projects
2. Sage detects file changes in real-time
3. Agents analyze changes for context relevance
4. Memory banks updated with new insights
5. Personality system provides feedback through web UI

### Integration with AI Assistants
1. Memory bank format compatible with Cline
2. Rich project context available for AI assistant access
3. Cross-project learning through global context store
4. Reduced need to re-explain project details

### Validation & Status
```bash
sage validate               # Comprehensive system validation
sage status                 # Current monitoring status
sage run --debug           # Debug mode with detailed logging
```

## AWS Bedrock Integration

### Authentication
- Standard AWS credential chain (environment variables, credentials file, IAM roles)
- Required permissions: `bedrock:InvokeModel`, `bedrock:GetFoundationModel`
- Regional availability considerations

### Model Configuration
- **Default**: Claude Sonnet 4 (`us.anthropic.claude-sonnet-4-20250514-v1:0`)
- **Configurable**: max_tokens, temperature, region
- **Health Checks**: Connection monitoring and fallback mechanisms

## Current Development Focus (MVP-03)

### Active Development Areas
- **Performance Optimization**: Context caching and memory management improvements
- **Enhanced UI Components**: Better visual indicators and user feedback
- **State Management**: Robust handling of video states and transitions  
- **Cross-Project Intelligence**: Advanced context sharing between monitored projects

### Future Enhancement Areas
- MCP tool integration for additional data sources
- IDE plugins for direct integration  
- Container deployment options
- Advanced analytics and reporting

### Architecture Extensions
- Redis/SQLite caching layer for performance
- Distributed processing support
- Enterprise authentication systems
- Community plugin system

## System Requirements

### Environment
- Python 3.9+ 
- AWS account with Bedrock access
- Sufficient memory for large project monitoring
- Network access for AWS API calls

### Dependencies
- All core dependencies managed through pyproject.toml
- Development tools: black, flake8, mypy, pytest
- Runtime dependencies automatically installed

## Security Considerations

### Best Practices
- No hardcoded secrets in configuration
- User-controlled project boundaries
- Configurable ignore patterns for sensitive files
- Local processing with minimal cloud communication
- Standard AWS security practices

---

**Status**: Production ready system with comprehensive capabilities for intelligent project context management and AI assistant integration.