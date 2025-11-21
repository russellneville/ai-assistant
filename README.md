# Sage - AI Project Context Assistant

An intelligent agentic assistant that monitors project folders and maintains context stores for AI code assistants using CrewAI and Amazon Bedrock.

## Features

- **Multi-Project Monitoring**: Simultaneously monitor multiple projects with dedicated agent crews
- **Intelligent Context Management**: Maintains a global context store with project-specific memory banks
- **Real-time File Monitoring**: Responds to file changes and updates context automatically
- **CrewAI Agent Orchestration**: Specialized agents for different aspects of context management
- **AWS Bedrock Integration**: Powered by Claude for intelligent analysis and decision-making
- **Browser-based UI**: Interactive personality-driven interface with emotional expressions
- **Cline Memory Bank Format**: Compatible with existing AI assistant workflows

## Architecture

### Core Components

- **Context Curator**: Maintains the global context store
- **Project Monitor**: Watches file changes and triggers updates
- **Technology Specialist**: Identifies and matches technologies with relevant context
- **Decision Logger**: Tracks all system decisions with full transparency
- **Conflict Resolver**: Handles conflicts and escalates to users when needed
- **Performance Monitor**: Ensures efficient resource usage

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

## Installation

### Requirements
- Python 3.8+
- AWS CLI configured with Bedrock access
- Valid AWS credentials with appropriate permissions

### Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd sage
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Configure AWS credentials** for Bedrock access:
   ```bash
   aws configure
   ```

4. **Initialize configuration**:
   ```bash
   sage init
   ```

5. **Edit configuration** to add your projects:
   ```bash
   nano config.yaml
   ```

   **Important**: Ensure the AWS region in your config.yaml matches your AWS CLI configuration to avoid connection issues.

## Configuration

### Main Configuration (`config.yaml`)

```yaml
projects:
  - path: "/path/to/your/project"
    crew_config: "web_development"
    priority: "high"

crews:
  web_development:
    agents: ["context_curator", "project_monitor", "tech_specialist"]
    specializations: ["javascript", "react", "nodejs"]

aws:
  region: "us-east-1"
  bedrock:
    model: "us.anthropic.claude-sonnet-4-20250514-v1:0"
    max_tokens: 4096

ui:
  personality:
    expressions_map: "./personality/expressions.json"
    default_emotion: "neutral"
  browser:
    port: 8080
    auto_open: true
```

### Ignore Patterns (`.sageignore`)

Create `.sageignore` files in your project directories to exclude files:

```
node_modules/
.git/
*.log
dist/
build/
```

### Sage Rules (`.alxyrules`)

Define project-specific rules for context importance:

```yaml
# High priority patterns
high_priority:
  - "*.config.js"
  - "package.json"
  - "README.md"

# Technologies to always include
always_include_tech:
  - "react"
  - "typescript"
  - "nodejs"

# Custom context rules
context_rules:
  - pattern: "src/components/*.tsx"
    importance: "high"
    reason: "Core UI components"
```

## Usage

### Starting Sage

```bash
# Start with default configuration
sage run

# Start with custom configuration
sage run --config /path/to/config.yaml

# Start with debug logging
sage run --debug
```

### CLI Commands

```bash
# Show status and configuration
sage status

# Validate configuration
sage validate

# Show version
sage version

# Get help
sage --help
```

### Web Interface

Once running, Sage provides a browser-based interface at `http://localhost:8080` featuring:

- **Personality System**: Sage communicates with emotional expressions
- **Real-time Updates**: Live notifications of file changes and analysis
- **Interactive Decisions**: Resolve conflicts through the UI
- **Project Status**: View monitoring status and statistics

## Personality System

Sage has a personality system with various emotional expressions:

- **neutral**: Default calm expression
- **joyful**: Happy and enthusiastic
- **serious**: Focused and professional
- **hopeful**: Optimistic and encouraging
- **skeptical**: Questioning and analytical
- **frustrated**: Exasperated with repeated issues
- **laughing**: Amused by entertaining code
- **tired**: Weary from intensive processing

## Memory Bank Format

Sage uses the Cline memory bank format for project-specific context:

```
memory-bank/
├── projectbrief.md      # Project foundation and goals
├── productContext.md    # Why the project exists
├── activeContext.md     # Current work focus
├── systemPatterns.md    # Architecture and patterns
├── techContext.md       # Technology stack and setup
└── progress.md          # Status and known issues
```

## Development

### Project Structure

```
sage/
├── sage/
│   ├── core/           # Core functionality
│   ├── agents/         # CrewAI agents
│   ├── config/         # Configuration management
│   ├── context/        # Context and memory management
│   └── ui/             # User interface components
├── personality/        # Personality expressions
├── features/           # Feature specifications
└── tests/              # Test suite
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black sage/

# Type checking
mypy sage/

# Linting
flake8 sage/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Troubleshooting

### Common Issues

**Error: "asyncio.run() cannot be called from a running event loop"**
- This has been resolved in recent versions. Ensure you're using the latest code.

**AWS Connection Issues**
- Verify your AWS region in `config.yaml` matches your AWS CLI configuration
- Check that your AWS credentials have Bedrock access permissions
- Confirm the specified Bedrock model is available in your region

**File Monitoring Not Working**
- Check that project paths in `config.yaml` are absolute and valid
- Ensure you have read permissions for the monitored directories
- Verify `.sageignore` patterns aren't excluding important files

**Web Interface Not Loading**
- Default port is 8080 - check if it's already in use
- Try specifying a different port in the configuration
- Check browser console for JavaScript errors

## Support

- **Issues**: Report bugs and request features on GitHub
- **Documentation**: Additional docs in the `docs/` directory
- **Community**: Join discussions in GitHub Discussions

---

*Sage - Making AI project assistance more intelligent, one context at a time.* 🤖✨