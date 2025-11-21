# Sage - AI Project Context Assistant

## Overview
Sage is an agentic assistant that monitors project folders and maintains intelligent context stores for AI code assistants. It uses CrewAI to orchestrate multiple specialized agents that work together to cultivate, update, and distribute relevant project context across multiple active projects.

## Core Architecture

### Multi-Project Support
- **Multiple Agent Crews**: Each project or project group has its own dedicated CrewAI crew
- **Concurrent Monitoring**: Sage handles multiple projects simultaneously with efficient resource allocation
- **Cross-Project Learning**: Context learned from one project can benefit others through the global context store

### Technology Stack
- **Framework**: [CrewAI](https://github.com/crewAIInc/crewAI) for agent orchestration
- **LLM Provider**: Amazon Bedrock
- **Default Model**: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- **Memory Format**: Cline memory bank format for project-specific context
- **MCP Integration**: Configurable MCP tool registry for external data retrieval

## Agent Roles & Responsibilities

### Core Agent Crews
1. **Context Curator**: Cultivates and maintains the global context store
2. **Project Monitor**: Watches file changes and triggers context updates
3. **Technology Specialist**: Matches technologies/frameworks to project needs
4. **Decision Logger**: Tracks all decisions made by Sage with timestamps and reasoning
5. **Conflict Resolver**: Handles cases where multiple contexts or rules conflict
6. **Performance Monitor**: Ensures efficient resource usage

## Context Management System

### Global Context Store Structure
```
context-store/
├── technologies/
│   ├── frameworks/
│   ├── languages/
│   ├── databases/
│   └── tools/
├── patterns/
│   ├── architectural/
│   ├── design/
│   └── deployment/
├── environments/
│   ├── development/
│   ├── staging/
│   └── production/
├── domains/
│   ├── business-logic/
│   ├── integrations/
│   └── security/
└── solutions/
    ├── common-issues/
    ├── troubleshooting/
    └── best-practices/
```

### Context Granularity
- **Concept-Level Analysis**: Focus on understanding and matching concepts rather than file-specific details
- **Semantic Relationships**: Track relationships between technologies, patterns, and solutions
- **Contextual Relevance**: Match context based on keywords, file patterns, and dependency analysis

### Memory Banks
- **Format**: Cline memory bank structure with markdown files
- **Project-Specific**: Each monitored project gets its own memory bank
- **Automatic Updates**: Memory banks updated on startup and file changes
- **Separation**: Maintained separately from CLAUDE.md files

## File Monitoring & Processing

### Monitored File Types
- Source code files (all languages)
- Documentation files (.md, .txt, .rst)
- Configuration files (.json, .yaml, .toml, .ini)
- Dependencies (package.json, requirements.txt, Cargo.toml, etc.)
- Build files (Makefile, Dockerfile, etc.)

### Monitoring Behavior
- **Startup**: Immediate analysis of all configured projects
- **File Changes**: Real-time response to file modifications
- **Nested Hierarchies**: Full support for complex folder structures
- **Ignore Patterns**: Configurable via `.sageignore` files

### Performance Optimization
- **File Monitoring**: Every 5 seconds for active projects, 30 seconds for background
- **Context Processing**: Batch updates every 2 minutes
- **Concurrent Operations**: Maximum 10 simultaneous file operations
- **Resource Monitoring**: Automatic throttling to prevent system overload

## Decision Logic & Learning

### Sage Rules System
- **`.alxyrules` Files**: User-defined rules for context importance
- **Rule Hierarchy**: Project-specific rules override global rules
- **Learning Integration**: Rules work alongside machine learning from existing projects
- **Conflict Resolution**: Escalation to user when rules conflict

### Context Matching Strategies
1. **Keyword Analysis**: Match technologies and concepts by name
2. **File Pattern Recognition**: Identify project types by file structure
3. **Dependency Analysis**: Understand requirements from package files

## User Interface & Interaction

### Browser-Based Personality Interface
- **Communication Method**: HTML/CSS interface in browser window
- **Personality System**: Sage has distinct personality with emotional expressions
- **Expression Mapping**: JSON configuration file maps emotions to image files
- **Dynamic Emotions**: Sage determines appropriate emotion based on message context
- **Interactive Decisions**: User can resolve conflicts and provide guidance through UI

### Notification & Alerts
- **Conflict Resolution**: Browser popup when Sage needs user decision
- **Progress Updates**: Visual feedback on processing status
- **Decision History**: Accessible log of all decisions and reasoning

## Configuration System

### Main Configuration File
```yaml
# Projects to monitor
projects:
  - path: "/path/to/project1"
    crew_config: "web_development"
    priority: "high"
  - path: "/path/to/project2" 
    crew_config: "data_science"
    priority: "medium"

# Crew configurations
crews:
  web_development:
    agents: ["context_curator", "project_monitor", "tech_specialist"]
    specializations: ["javascript", "react", "nodejs"]
  data_science:
    agents: ["context_curator", "project_monitor", "tech_specialist", "data_specialist"]
    specializations: ["python", "pandas", "jupyter"]

# AWS/Bedrock settings
aws:
  region: "us-east-1"
  bedrock:
    model: "us.anthropic.claude-sonnet-4-20250514-v1:0"
    max_tokens: 4096

# MCP Integration
mcp:
  registry_path: "/path/to/mcp-tools"
  enabled_tools: ["web_search", "documentation", "code_analysis"]

# Performance settings
performance:
  file_monitor_frequency: 5  # seconds for active projects
  background_frequency: 30   # seconds for background projects
  batch_update_interval: 120 # seconds
  max_concurrent_ops: 10

# UI settings
ui:
  personality:
    expressions_map: "./personality/expressions.json"
    default_emotion: "neutral"
  browser:
    port: 8080
    auto_open: true
```

### Ignore Patterns (`.sageignore`)
```
# Version control
.git/
.svn/
.hg/

# Dependencies
node_modules/
vendor/
.venv/
venv/
__pycache__/

# Build outputs
dist/
build/
target/
*.o
*.exe

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
logs/

# User-defined patterns
# Add custom ignore patterns below
```

## Startup & Operational Flow

### Initialization Process
1. Load configuration and validate settings
2. Initialize browser UI and personality system
3. Scan all configured project directories
4. Create/update memory banks for each project
5. Start file monitoring on all projects
6. Initialize CrewAI agents for each project crew

### Operational Cycle
1. **File Change Detection**: Monitor configured directories
2. **Context Analysis**: Determine if changes require context updates
3. **Global Context Query**: Check if relevant context exists in global store
4. **Memory Bank Update**: Update project-specific memory banks as needed
5. **Conflict Resolution**: Escalate to user when conflicts arise
6. **Decision Logging**: Record all decisions and actions taken

## Integration Points

### MCP Tools
- **Registry Configuration**: Configurable path to MCP tool registry
- **Dynamic Loading**: Load tools based on project requirements
- **Context Enrichment**: Use MCP tools to gather additional context when needed

### External Systems
- **Version Control**: Git integration for tracking project changes
- **CI/CD**: Potential integration with build systems
- **Documentation**: Automatic updates to project documentation

## Success Metrics

### Efficiency Metrics
- Context update frequency and accuracy
- System resource utilization
- Response time to file changes

### Quality Metrics  
- Relevance of context suggestions
- Reduction in manual context setup
- User satisfaction with personality interface

### Learning Metrics
- Growth of global context store
- Improvement in context matching over time
- Reduction in user intervention requirements