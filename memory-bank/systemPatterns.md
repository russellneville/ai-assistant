# System Patterns: Sage Architecture

## Overall Architecture

### Multi-Layer Design
```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   CLI Interface │  │  Web UI Server  │  │ Personality │ │
│  │    (Typer)      │  │   (FastAPI)     │  │   System    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Application Orchestration                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              SageApplication (Main)                     │ │
│  │  - Async/await coordination                             │ │
│  │  - Component lifecycle management                       │ │
│  │  - Signal handling & graceful shutdown                  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestration                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Crew Manager   │  │  Agent Registry │  │ Task Engine │ │
│  │   (CrewAI)      │  │   (6 Types)     │  │  (Dynamic)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Core Services                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ File Monitor    │  │ Context Store   │  │ Bedrock     │ │
│  │  (Watchdog)     │  │ (Global/Local)  │  │  Client     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Patterns

### 1. Agent-Based Architecture (CrewAI)
**Pattern**: Specialized agents working in coordinated crews
**Implementation**:
- 6 core agent types with specific responsibilities
- Dynamic crew composition based on project needs
- Task-based execution with context sharing
- Registry pattern for agent discovery and instantiation

**Agent Types**:
- **Context Curator**: Maintains global context store
- **Project Monitor**: Watches file changes and triggers updates
- **Technology Specialist**: Matches technologies to project needs
- **Decision Logger**: Tracks all decisions with reasoning
- **Conflict Resolver**: Handles conflicts and escalates to users
- **Performance Monitor**: Ensures efficient resource usage

### 2. Event-Driven File Monitoring
**Pattern**: Observer pattern with async event processing
**Implementation**:
```python
FileMonitor -> FileChangeEvent -> AsyncEventHandler -> CrewExecution
```
- Watchdog library for cross-platform file monitoring
- Event filtering based on ignore patterns
- Async processing to prevent blocking
- Batch processing for performance optimization

### 3. Configuration-Driven System
**Pattern**: Dependency injection through configuration
**Implementation**:
- Pydantic models for type-safe configuration
- Hierarchical configuration (global -> project-specific)
- Validation at load time with clear error messages
- Hot-reload capability for development

### 4. Context Store Hierarchy
**Pattern**: Layered context management
**Structure**:
```
Global Context Store
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
├── domains/
└── solutions/

Project-Specific Memory Banks (Cline format)
├── projectbrief.md
├── productContext.md
├── activeContext.md
├── systemPatterns.md
├── techContext.md
└── progress.md
```

### 5. Personality System Pattern
**Pattern**: State machine with context-aware transitions
**Implementation**:
- JSON-driven emotion mapping
- Context analysis for appropriate emotion selection
- Image-based visual expressions
- Fallback mechanisms for unknown contexts

## Component Relationships

### Core Dependencies
```
SageApplication
├── ConfigLoader (Pydantic validation)
├── BedrockClient (AWS SDK)
├── CrewManager (CrewAI orchestration)
│   └── Agent Registry (6 specialized agents)
├── FileMonitor (Watchdog events)
├── ContextStore (Global knowledge)
├── MemoryBankManager (Project-specific context)
├── PersonalitySystem (Emotional expressions)
└── WebServer (FastAPI + WebSockets)
```

### Data Flow Patterns
1. **File Change Detection**:
   ```
   File System → Watchdog → FileMonitor → Event Queue → CrewManager → Agents
   ```

2. **Context Updates**:
   ```
   Agent Analysis → Context Store → Memory Bank → Persistence Layer
   ```

3. **User Interaction**:
   ```
   Web UI → WebSocket → PersonalitySystem → Response Generation → UI Update
   ```

## Critical Implementation Paths

### 1. Startup Sequence
1. Load and validate configuration
2. Initialize AWS Bedrock client
3. Create context store and memory bank manager
4. Initialize personality system
5. Start file monitoring
6. Perform initial project analysis
7. Start web server
8. Send startup notification

### 2. File Change Processing
1. Detect file change event
2. Filter based on ignore patterns
3. Identify relevant project configuration
4. Queue for async processing
5. Execute crew analysis
6. Update context stores
7. Update memory banks
8. Notify UI with personality-appropriate response

### 3. Conflict Resolution
1. Agent detects conflicting information
2. Escalate to ConflictResolver agent
3. Generate conflict description and options
4. Present to user through personality UI
5. Capture user decision
6. Log decision with reasoning
7. Update context with resolution

## Error Handling Patterns

### 1. Graceful Degradation
- System continues operating with reduced functionality if components fail
- Clear logging of component failures
- User notification of degraded capabilities

### 2. Circuit Breaker Pattern
- Bedrock client has health checks and fallback behavior
- File monitoring can be throttled under high load
- Agent execution has timeout and retry mechanisms

### 3. Resource Management
- Thread pool executor with configurable limits
- Memory monitoring and cleanup
- File handle management for large projects

## Performance Patterns

### 1. Async/Await Throughout
- Non-blocking I/O operations
- Concurrent file processing
- Async web server and WebSocket handling

### 2. Batching and Throttling
- File change events batched for efficiency
- Configurable monitoring frequencies
- Resource usage monitoring and throttling

### 3. Caching Strategies
- Context store caching for frequently accessed data
- Agent result caching for repeated analyses
- Configuration caching with invalidation

## Security Patterns

### 1. Credential Management
- AWS credentials through standard AWS SDK patterns
- No hardcoded secrets in configuration
- Environment variable support for sensitive data

### 2. File System Access
- Configurable ignore patterns for sensitive files
- Path validation to prevent directory traversal
- User-controlled project boundaries

### 3. Web Interface Security
- CORS configuration for browser access
- WebSocket authentication (future enhancement)
- Input validation on all user inputs
