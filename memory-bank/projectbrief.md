# Project Brief: Sage - AI Project Context Assistant

## Core Mission
Sage is an intelligent agentic assistant that monitors project folders and maintains context stores for AI code assistants using CrewAI and Amazon Bedrock. The goal is to create a system that can simultaneously monitor multiple projects, understand their context, and provide intelligent assistance through a personality-driven interface.

## Primary Objectives

### 1. Multi-Project Context Management
- Monitor multiple software projects simultaneously
- Maintain intelligent context stores with project-specific memory banks
- Provide real-time file change monitoring and analysis
- Create a global context store that benefits all monitored projects

### 2. Intelligent Agent Orchestration
- Use CrewAI to orchestrate specialized agents for different aspects of context management
- Implement 6 core agent types: Context Curator, Project Monitor, Technology Specialist, Decision Logger, Conflict Resolver, Performance Monitor
- Enable dynamic crew configuration based on project needs

### 3. Personality-Driven Interface
- Provide a browser-based UI with emotional expressions
- Implement 14 different personality states based on context and interaction type
- Create engaging, human-like interactions while maintaining professional functionality

### 4. AWS Bedrock Integration
- Leverage Claude models through Amazon Bedrock for intelligent analysis
- Provide configurable model selection and parameters
- Ensure robust error handling and fallback mechanisms

## Success Criteria

### Technical Requirements
- Successfully monitor and analyze multiple projects concurrently
- Maintain accurate context stores that improve AI assistant effectiveness
- Provide real-time responsiveness to file changes
- Ensure system stability and resource efficiency

### User Experience Requirements
- Intuitive configuration and setup process
- Clear, personality-driven communication
- Effective conflict resolution when issues arise
- Seamless integration with existing development workflows

### Integration Requirements
- Compatible with Cline memory bank format
- Support for MCP tool integration
- Configurable ignore patterns and project-specific rules
- AWS credentials and Bedrock model configuration

## Project Scope

### In Scope
- Multi-project file monitoring and analysis
- CrewAI agent orchestration system
- Browser-based personality interface
- Context store management and memory bank creation
- AWS Bedrock integration for LLM capabilities
- CLI interface for configuration and management

### Out of Scope (Initially)
- Direct IDE integration beyond file monitoring
- Real-time collaboration features
- Version control system integration beyond file watching
- Advanced machine learning model training
- Enterprise authentication systems

## Key Constraints
- Python 3.9+ requirement
- AWS Bedrock availability and costs
- CrewAI framework limitations
- File system monitoring performance considerations
- Browser compatibility for UI components

## Target Users
- Software developers working on multiple projects
- Development teams needing better context management
- AI assistant users seeking more intelligent project understanding
- DevOps engineers managing complex project portfolios
