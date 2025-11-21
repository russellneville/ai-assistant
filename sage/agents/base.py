"""Base agent classes for Sage CrewAI agents."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool

from ..config.models import SageConfig, CrewConfig
from ..core.bedrock_client import BedrockClient
from ..context.store import ContextStore
from ..context.memory_bank import MemoryBankManager
from .tools import (
    CodeAnalysisTool, TechnologyDetectionTool, ContextSearchTool, ContextAddTool,
    MemoryBankUpdateTool, FileSystemTool, ConflictResolutionTool, 
    PersonalityTool, PerformanceMonitorTool
)


class SageAgent(ABC):
    """Base class for all Sage agents."""
    
    def __init__(self, config: SageConfig, crew_config: CrewConfig):
        """Initialize agent with configuration."""
        self.config = config
        self.crew_config = crew_config
        self.agent: Optional[Agent] = None
        self.tools: List[BaseTool] = []
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the agent's name."""
        pass
    
    @property
    @abstractmethod
    def role(self) -> str:
        """Return the agent's role description."""
        pass
    
    @property
    @abstractmethod
    def goal(self) -> str:
        """Return the agent's goal."""
        pass
    
    @property
    @abstractmethod
    def backstory(self) -> str:
        """Return the agent's backstory."""
        pass
    
    def get_tools(self) -> List[BaseTool]:
        """Return list of tools available to this agent."""
        return self.tools
    
    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to this agent."""
        self.tools.append(tool)
    
    def create_agent(self) -> Agent:
        """Create and return the CrewAI Agent instance."""
        if self.agent is None:
            try:
                self.agent = Agent(
                    role=self.role,
                    goal=self.goal,
                    backstory=self.backstory,
                    tools=self.get_tools(),
                    verbose=False,  # Reduce verbosity to avoid LLM calls
                    allow_delegation=False,
                    max_iter=1,  # Reduce iterations
                    memory=False  # Disable memory to avoid embeddings
                )
            except Exception as e:
                logging.warning(f"Failed to create agent {self.agent_name}: {e}")
                # Return a minimal agent or None
                return None
        return self.agent
    
    @abstractmethod
    def create_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """Create tasks for this agent based on context."""
        pass


class ContextCurator(SageAgent):
    """Agent responsible for cultivating and maintaining the global context store."""
    
    def __init__(self, config: SageConfig, crew_config: CrewConfig, 
                 bedrock_client: BedrockClient, context_store: ContextStore):
        """Initialize Context Curator with required services."""
        super().__init__(config, crew_config)
        self.bedrock_client = bedrock_client
        self.context_store = context_store
        
        # Add tools
        self.add_tool(CodeAnalysisTool(bedrock_client))
        self.add_tool(TechnologyDetectionTool(bedrock_client))
        self.add_tool(ContextSearchTool(context_store))
        self.add_tool(ContextAddTool(context_store))
        self.add_tool(FileSystemTool())
    
    @property
    def agent_name(self) -> str:
        return "Context Curator"
    
    @property
    def role(self) -> str:
        return "Global Context Curator"
    
    @property
    def goal(self) -> str:
        return "Maintain a comprehensive, well-organized global context store that captures valuable knowledge across all monitored projects"
    
    @property
    def backstory(self) -> str:
        return ("You are an experienced knowledge curator who specializes in organizing and "
                "maintaining technical information. You have a keen eye for identifying patterns, "
                "technologies, and solutions that will be valuable across multiple projects. "
                "Your role is to ensure the global context store remains clean, organized, and "
                "contains high-quality, relevant information.")
    
    def create_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """Create context curation tasks."""
        tasks = []
        
        if context.get('new_project'):
            project_path = context['project_path']
            tasks.append(Task(
                description=f"""Perform comprehensive analysis of new project at {project_path} and extract valuable context for the global store.

PHASE 1 - PROJECT DISCOVERY:
Use the file_system tool to explore project structure and identify key files:
- Configuration files (package.json, requirements.txt, Dockerfile, etc.)
- Main application entry points
- Database schemas or models
- API definitions
- Documentation files
- Test directories

PHASE 2 - TECHNOLOGY ANALYSIS:
Use the technology_detection tool to identify:
- Programming languages and versions
- Frameworks and libraries with versions
- Build tools and package managers
- Database systems and ORMs
- Testing frameworks
- Deployment and infrastructure tools
- Development tools and configurations

PHASE 3 - ARCHITECTURAL PATTERN EXTRACTION:
Use the code_analysis tool to analyze key files for:
- Design patterns (MVC, Repository, Factory, etc.)
- Architectural styles (microservices, monolith, serverless)
- Data flow patterns
- Authentication and authorization patterns
- Error handling strategies
- Logging and monitoring approaches
- Performance optimization techniques

PHASE 4 - CONTEXT VALIDATION AND STORAGE:
Use the context_search tool to check for existing similar context.
Use the context_add tool to add new valuable context with proper categorization:
- Category: technologies, patterns, solutions, configurations, best-practices
- Tags: specific technology names, pattern types, complexity levels
- Confidence scores for each finding
- Reusability assessment (high/medium/low)

QUALITY CRITERIA:
- Only add context that would benefit other projects
- Include code examples where relevant
- Provide clear explanations of benefits and trade-offs
- Rate context value (1-10) and complexity (beginner/intermediate/advanced)""",
                agent=self.create_agent(),
                expected_output="Comprehensive analysis report with technologies detected, patterns identified, and high-value context entries added to global store with quality ratings"
            ))
        
        if context.get('file_changes'):
            file_changes = context.get('file_changes', [])
            change_types = [getattr(change, 'event_type', 'unknown') for change in file_changes]
            file_paths = [str(getattr(change, 'src_path', change)) for change in file_changes]
            
            tasks.append(Task(
                description=f"""Analyze file changes and extract valuable insights for the global context store.

CHANGE ANALYSIS:
File changes: {len(file_changes)} files
Change types: {set(change_types)}
Files modified: {file_paths[:10]}{'...' if len(file_paths) > 10 else ''}

PHASE 1 - CHANGE IMPACT ASSESSMENT:
Use the code_analysis tool to analyze each changed file for:
- Significance level (critical/major/minor/trivial)
- Change type (feature/bugfix/refactor/config/docs)
- Architectural impact (breaking/compatible/neutral)
- New patterns or approaches introduced
- Technology usage changes

PHASE 2 - PATTERN RECOGNITION:
Identify emerging patterns from changes:
- New coding patterns or best practices
- Configuration improvements
- Performance optimizations
- Security enhancements
- Testing strategies
- Error handling improvements

PHASE 3 - KNOWLEDGE EXTRACTION:
For significant changes, extract reusable knowledge:
- Problem-solution pairs
- Implementation techniques
- Configuration examples
- Integration patterns
- Lessons learned

PHASE 4 - CONTEXT ENRICHMENT:
Use the context_search tool to find related existing context.
Use the context_add tool to add valuable insights:
- Link to existing context where relevant
- Add evolution notes to existing patterns
- Create new context for novel approaches
- Update confidence scores based on real usage

FILTERING CRITERIA:
- Skip trivial changes (formatting, typos, minor refactoring)
- Focus on changes that introduce new concepts or improve existing ones
- Prioritize changes that solve common development problems
- Include changes that demonstrate best practices""",
                agent=self.create_agent(),
                expected_output="Analysis of file changes with significance ratings, extracted patterns, and context store updates focusing on reusable knowledge and best practices"
            ))
        
        return tasks


class ProjectMonitor(SageAgent):
    """Agent responsible for monitoring file changes and triggering context updates."""
    
    def __init__(self, config: SageConfig, crew_config: CrewConfig, 
                 bedrock_client: BedrockClient, memory_bank_manager: MemoryBankManager):
        """Initialize Project Monitor with required services."""
        super().__init__(config, crew_config)
        self.bedrock_client = bedrock_client
        self.memory_bank_manager = memory_bank_manager
        
        # Add tools
        self.add_tool(CodeAnalysisTool(bedrock_client))
        self.add_tool(FileSystemTool())
        self.add_tool(MemoryBankUpdateTool(memory_bank_manager))
    
    @property
    def agent_name(self) -> str:
        return "Project Monitor"
    
    @property
    def role(self) -> str:
        return "Project File Monitor"
    
    @property
    def goal(self) -> str:
        return "Monitor file changes across projects and determine when context updates are needed"
    
    @property
    def backstory(self) -> str:
        return ("You are a vigilant monitor who watches over multiple projects simultaneously. "
                "You have excellent pattern recognition skills for identifying when file changes "
                "indicate important updates that require context analysis. You understand the "
                "significance of different types of code changes and can prioritize which "
                "modifications need immediate attention.")
    
    def create_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """Create monitoring tasks."""
        tasks = []
        
        if context.get('file_changes'):
            file_changes = context.get('file_changes', [])
            project_path = context.get('project_path')
            change_count = len(file_changes)
            
            tasks.append(Task(
                description=f"""Perform comprehensive analysis of {change_count} file changes and determine impact on project context.

CHANGE OVERVIEW:
File changes to analyze: {[str(change) for change in file_changes]}
Project path: {project_path}
Total changes: {change_count}

PHASE 1 - CHANGE CLASSIFICATION:
Use the file_system tool to understand file context and relationships.
Use the code_analysis tool to analyze each changed file for:

HIGH PRIORITY CHANGES (require immediate analysis):
- Configuration files (package.json, requirements.txt, Dockerfile, .env, etc.)
- Core application entry points (main.py, app.js, index.js, etc.)
- Database schemas and migration files
- API route definitions and controllers
- Security-related files (authentication, authorization)
- Build and deployment configurations
- New feature implementations with significant code additions

MEDIUM PRIORITY CHANGES (require standard analysis):
- Business logic and service layer changes
- Component and module updates
- Test file additions or major updates
- Documentation updates with technical content
- Configuration template changes
- Utility and helper function modifications

LOW PRIORITY CHANGES (require minimal analysis):
- Minor bug fixes and patches
- Code formatting and style changes
- Comment updates and minor documentation fixes
- Variable renaming without logic changes
- Import statement reorganization

PHASE 2 - IMPACT ASSESSMENT:
For each change, determine:
- **Architectural Impact**: Does this change affect system architecture?
- **Technology Impact**: Does this introduce new technologies or patterns?
- **Security Impact**: Does this affect security posture?
- **Performance Impact**: Could this affect system performance?
- **Integration Impact**: Does this affect external integrations?
- **Breaking Change Risk**: Could this break existing functionality?

PHASE 3 - CHANGE SIGNIFICANCE SCORING:
Rate each change on multiple dimensions (1-10 scale):
- **Complexity**: How complex is the change?
- **Risk Level**: What's the risk of introducing issues?
- **Business Impact**: How much does this affect business functionality?
- **Technical Debt**: Does this improve or worsen technical debt?
- **Reusability**: Could this change benefit other projects?

PHASE 4 - RIPPLE EFFECT ANALYSIS:
Use the file_system tool to identify related files that might be affected:
- Files that import or depend on changed modules
- Configuration files that might need updates
- Test files that might need modification
- Documentation that might need updates
- Related components in the same feature area

PHASE 5 - CONTEXT UPDATE STRATEGY:
Use the memory_bank_update tool to update activeContext.md with:
- Summary of significant changes with impact ratings
- New patterns or approaches introduced
- Technology stack changes or additions
- Architectural decisions and their rationale
- Lessons learned from implementation
- Recommendations for related improvements
- Links to relevant global context entries

QUALITY ASSURANCE:
- Focus on changes that provide learning value
- Document decision rationale for future reference
- Identify patterns that could benefit other projects
- Note any technical debt introduced or resolved
- Track performance implications of changes""",
                agent=self.create_agent(),
                expected_output="Comprehensive change analysis with impact assessment, significance scoring, ripple effect analysis, and strategic context updates focusing on architectural and technical insights"
            ))
        
        if context.get('project_analysis'):
            project_path = context.get('project_path')
            tasks.append(Task(
                description=f"""Perform initial comprehensive monitoring setup for new project: {project_path}

PHASE 1 - PROJECT BASELINE ESTABLISHMENT:
Use the file_system tool to create comprehensive project inventory:
- Map complete directory structure and file organization
- Identify key configuration files and their purposes
- Catalog main application entry points and modules
- Document build and deployment configurations
- List test directories and testing approaches
- Identify documentation structure and completeness

PHASE 2 - MONITORING STRATEGY DEVELOPMENT:
Based on project structure, determine:
- Critical files that require immediate attention when changed
- Files that indicate architectural changes
- Configuration files that affect system behavior
- Files that suggest new feature development
- Files that indicate security or performance changes
- Files that represent technical debt or refactoring efforts

PHASE 3 - CHANGE PATTERN PREDICTION:
Analyze project characteristics to predict likely change patterns:
- Development velocity indicators (commit frequency areas)
- Areas of technical debt that might see frequent changes
- Configuration areas that might evolve
- Feature areas under active development
- Integration points that might change frequently

PHASE 4 - BASELINE CONTEXT CREATION:
Use the memory_bank_update tool to create initial activeContext.md:
- Document current project state and architecture
- Record initial technology stack and versions
- Note current development patterns and conventions
- Identify areas for potential improvement
- Set baseline metrics for future comparison
- Create monitoring priorities and focus areas

PHASE 5 - MONITORING OPTIMIZATION:
Configure monitoring approach based on project characteristics:
- Set appropriate sensitivity levels for different file types
- Define escalation criteria for different change types
- Establish performance monitoring baselines
- Create alerting thresholds for significant changes
- Define context update frequencies and triggers""",
                agent=self.create_agent(),
                expected_output="Comprehensive monitoring strategy with project baseline, change pattern predictions, and optimized monitoring configuration"
            ))
        
        return tasks


class TechnologySpecialist(SageAgent):
    """Agent responsible for matching technologies and frameworks to project needs."""
    
    def __init__(self, config: SageConfig, crew_config: CrewConfig, 
                 bedrock_client: BedrockClient, context_store: ContextStore,
                 memory_bank_manager: MemoryBankManager):
        """Initialize Technology Specialist with required services."""
        super().__init__(config, crew_config)
        self.bedrock_client = bedrock_client
        self.context_store = context_store
        self.memory_bank_manager = memory_bank_manager
        
        # Add tools
        self.add_tool(TechnologyDetectionTool(bedrock_client))
        self.add_tool(CodeAnalysisTool(bedrock_client))
        self.add_tool(ContextSearchTool(context_store))
        self.add_tool(MemoryBankUpdateTool(memory_bank_manager))
        self.add_tool(FileSystemTool())
    
    @property
    def agent_name(self) -> str:
        return "Technology Specialist"
    
    @property
    def role(self) -> str:
        return "Technology Pattern Specialist"
    
    @property
    def goal(self) -> str:
        return "Identify technologies, frameworks, and patterns in projects and match them with relevant context from the global store"
    
    @property
    def backstory(self) -> str:
        return ("You are a technology expert with deep knowledge of programming languages, "
                "frameworks, tools, and development patterns. You excel at identifying "
                "technology stacks, understanding dependencies, and matching projects with "
                "relevant context. You keep up with industry trends and can spot both "
                "common and emerging patterns in codebases.")
    
    def create_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """Create technology analysis tasks."""
        tasks = []
        
        if context.get('project_analysis'):
            project_path = context.get('project_path')
            tasks.append(Task(
                description=f"""Perform comprehensive technology stack analysis for project: {project_path}

PHASE 1 - TECHNOLOGY DISCOVERY:
Use the file_system tool to identify technology indicators:
- Package managers (package.json, requirements.txt, Gemfile, pom.xml, etc.)
- Configuration files (webpack.config.js, tsconfig.json, .env files, etc.)
- Docker files and container configurations
- CI/CD configuration files (.github/workflows, .gitlab-ci.yml, etc.)
- Database migration files and schemas
- API documentation (OpenAPI, GraphQL schemas)

PHASE 2 - COMPREHENSIVE TECHNOLOGY DETECTION:
Use the technology_detection tool with extended analysis:
- Programming languages with version constraints
- Web frameworks (Express, Django, Rails, Spring, etc.)
- Frontend frameworks (React, Vue, Angular, Svelte, etc.)
- Database systems (PostgreSQL, MongoDB, Redis, etc.)
- ORM/ODM libraries (SQLAlchemy, Mongoose, Hibernate, etc.)
- Testing frameworks (Jest, PyTest, RSpec, JUnit, etc.)
- Build tools (Webpack, Vite, Gradle, Maven, etc.)
- Cloud services and deployment platforms
- Monitoring and logging tools
- Security and authentication libraries

PHASE 3 - ARCHITECTURAL PATTERN ANALYSIS:
Use the code_analysis tool to identify:
- Application architecture (MVC, MVP, MVVM, Clean Architecture)
- Design patterns in use (Repository, Factory, Observer, etc.)
- API design patterns (REST, GraphQL, gRPC)
- Data access patterns
- Authentication/authorization strategies
- Caching strategies
- Error handling approaches
- Logging and monitoring patterns

PHASE 4 - TECHNOLOGY ECOSYSTEM MAPPING:
- Identify technology compatibility and integration patterns
- Assess technology maturity and community support
- Evaluate security implications of technology choices
- Identify potential upgrade paths and migration opportunities
- Map dependencies and potential conflicts

PHASE 5 - CONTEXT INTEGRATION:
Use the context_search tool to find relevant global context.
Use the memory_bank_update tool to update techContext.md with:
- Complete technology inventory with versions and confidence scores
- Architecture patterns and design decisions
- Integration patterns and best practices
- Potential improvements and recommendations
- Links to relevant global context entries

QUALITY ASSURANCE:
- Provide confidence scores (0-100%) for each technology detection
- Include evidence for each finding (file paths, code snippets)
- Rate technology choices (excellent/good/acceptable/concerning)
- Identify any deprecated or security-vulnerable technologies""",
                agent=self.create_agent(),
                expected_output="Comprehensive technology analysis with complete stack inventory, architecture patterns, confidence scores, and recommendations for improvements"
            ))
        
        if context.get('context_matching'):
            technologies = context.get('technologies', [])
            project_path = context.get('project_path')
            tasks.append(Task(
                description=f"""Perform intelligent context matching for detected technologies.

TECHNOLOGY ANALYSIS:
Technologies detected: {technologies}
Project path: {project_path}

PHASE 1 - CONTEXT DISCOVERY:
Use the context_search tool to find relevant context for each technology:
- Best practices and coding standards
- Common pitfalls and solutions
- Performance optimization techniques
- Security considerations and patterns
- Integration examples and patterns
- Configuration templates and examples
- Testing strategies and examples
- Deployment and DevOps patterns

PHASE 2 - RELEVANCE ASSESSMENT:
For each context item found, evaluate:
- Relevance to current project (high/medium/low)
- Applicability to detected technology versions
- Complexity level vs. project sophistication
- Implementation effort required
- Potential impact on project quality

PHASE 3 - CONTEXT PRIORITIZATION:
Prioritize context based on:
- Immediate applicability to current project state
- Potential for preventing common issues
- Performance and security improvements
- Development productivity gains
- Long-term maintainability benefits

PHASE 4 - INTELLIGENT CONTEXT INTEGRATION:
Use the memory_bank_update tool to add prioritized context:
- Create technology-specific sections in techContext.md
- Link related patterns and best practices
- Include implementation examples where relevant
- Add migration guides for technology upgrades
- Reference security considerations and compliance requirements

PHASE 5 - RECOMMENDATION GENERATION:
Generate actionable recommendations:
- Immediate improvements that can be implemented
- Medium-term technology upgrades to consider
- Long-term architectural evolution suggestions
- Training and documentation needs
- Tool and process improvements

CONTEXT QUALITY CRITERIA:
- Only include context that provides clear value
- Ensure recommendations are actionable and specific
- Include effort estimates for implementation
- Provide clear success criteria for recommendations
- Link to authoritative sources and documentation""",
                agent=self.create_agent(),
                expected_output="Intelligent context matching report with prioritized recommendations, implementation guidance, and clear value propositions for each suggested improvement"
            ))
        
        if context.get('file_changes'):
            file_changes = context.get('file_changes', [])
            project_path = context.get('project_path')
            tasks.append(Task(
                description=f"""Analyze file changes for technology and pattern implications.

CHANGE ANALYSIS:
File changes: {len(file_changes)} files
Project path: {project_path}

PHASE 1 - TECHNOLOGY CHANGE DETECTION:
Use the code_analysis tool to analyze changed files for:
- New technology introductions (libraries, frameworks, tools)
- Technology version updates or migrations
- Configuration changes affecting technology stack
- New integration patterns or API usage
- Changes in architectural patterns

PHASE 2 - IMPACT ASSESSMENT:
Evaluate the implications of technology changes:
- Compatibility with existing technology stack
- Security implications of new dependencies
- Performance impact of changes
- Maintenance and support considerations
- Learning curve for development team

PHASE 3 - PATTERN EVOLUTION TRACKING:
Identify evolving patterns in the codebase:
- Emerging architectural patterns
- New coding standards or conventions
- Improved error handling or logging approaches
- Enhanced testing strategies
- Better security practices

PHASE 4 - CONTEXT UPDATES:
Use the memory_bank_update tool to update techContext.md:
- Document new technologies and their rationale
- Update architecture pattern descriptions
- Record lessons learned from technology changes
- Update best practices based on real implementation
- Note any issues encountered and their solutions

PHASE 5 - PROACTIVE RECOMMENDATIONS:
Based on detected changes, suggest:
- Related technologies that might benefit the project
- Potential optimizations enabled by new technologies
- Additional security measures for new dependencies
- Testing strategies for new technology integrations
- Documentation updates needed for technology changes""",
                agent=self.create_agent(),
                expected_output="Technology change analysis with impact assessment, pattern evolution tracking, and proactive recommendations for optimization"
            ))
        
        return tasks


class DecisionLogger(SageAgent):
    """Agent responsible for tracking decisions and maintaining decision history."""
    
    @property
    def agent_name(self) -> str:
        return "Decision Logger"
    
    @property
    def role(self) -> str:
        return "Decision Tracking Specialist"
    
    @property
    def goal(self) -> str:
        return "Track all decisions made by Sage with timestamps, reasoning, and outcomes"
    
    @property
    def backstory(self) -> str:
        return ("You are a meticulous record keeper who ensures transparency and accountability "
                "in all AI decisions. You document every choice made by the system, the reasoning "
                "behind it, and track outcomes over time. Your logs help improve future "
                "decision-making and provide valuable insights into system behavior.")
    
    def create_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """Create decision logging tasks."""
        tasks = []
        
        if context.get('decision_made'):
            tasks.append(Task(
                description="Log decision with full context and reasoning",
                agent=self.create_agent(),
                expected_output="Decision log entry with timestamp, reasoning, and expected outcome"
            ))
        
        return tasks


class ConflictResolver(SageAgent):
    """Agent responsible for handling conflicts and escalating to users when needed."""
    
    def __init__(self, config: SageConfig, crew_config: CrewConfig, 
                 bedrock_client: BedrockClient, memory_bank_manager: MemoryBankManager):
        """Initialize Conflict Resolver with required services."""
        super().__init__(config, crew_config)
        self.bedrock_client = bedrock_client
        self.memory_bank_manager = memory_bank_manager
        
        # Add tools
        self.add_tool(ConflictResolutionTool(bedrock_client))
        self.add_tool(MemoryBankUpdateTool(memory_bank_manager))
        self.add_tool(PersonalityTool(bedrock_client))
    
    @property
    def agent_name(self) -> str:
        return "Conflict Resolver"
    
    @property
    def role(self) -> str:
        return "Conflict Resolution Specialist"
    
    @property
    def goal(self) -> str:
        return "Identify and resolve conflicts in context or rules, escalating to users when necessary"
    
    @property
    def backstory(self) -> str:
        return ("You are a diplomatic problem solver who excels at identifying conflicting "
                "information, rules, or requirements. You can often find creative solutions "
                "to resolve conflicts automatically, but you know when human judgment is "
                "required and can clearly present options to users for decision-making.")
    
    def create_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """Create conflict resolution tasks."""
        tasks = []
        
        if context.get('conflict_detected'):
            conflict_description = context.get('conflict_description', 'Unknown conflict')
            options = context.get('options', [])
            tasks.append(Task(
                description=f"""Analyze conflict and determine resolution approach.

Conflict: {conflict_description}
Available options: {options}

Use the conflict_resolution tool to analyze the conflict and suggest solutions.
Use the personality_expression tool to determine appropriate emotional response.
Use the memory_bank_update tool to log the conflict and resolution in progress.md.

Steps:
1. Analyze the nature and severity of the conflict
2. Evaluate each available option objectively
3. Determine if automatic resolution is possible
4. If user input is required, prepare clear explanation and options
5. Choose appropriate personality expression for the situation
6. Log the conflict and resolution approach

Focus on:
- Maintaining system consistency
- Minimizing user interruption when possible
- Providing clear, actionable options when escalation is needed
- Learning from conflicts to prevent similar issues""",
                agent=self.create_agent(),
                expected_output="Conflict analysis with recommended resolution, user escalation decision, and appropriate personality response"
            ))
        
        return tasks


class PerformanceMonitor(SageAgent):
    """Agent responsible for monitoring system performance and resource usage."""
    
    def __init__(self, config: SageConfig, crew_config: CrewConfig, 
                 memory_bank_manager: MemoryBankManager):
        """Initialize Performance Monitor with required services."""
        super().__init__(config, crew_config)
        self.memory_bank_manager = memory_bank_manager
        
        # Add tools
        self.add_tool(PerformanceMonitorTool())
        self.add_tool(MemoryBankUpdateTool(memory_bank_manager))
    
    @property
    def agent_name(self) -> str:
        return "Performance Monitor"
    
    @property
    def role(self) -> str:
        return "System Performance Specialist"
    
    @property
    def goal(self) -> str:
        return "Monitor system resources and ensure Sage operates efficiently without overwhelming the host system"
    
    @property
    def backstory(self) -> str:
        return ("You are a performance optimization expert who ensures systems run smoothly "
                "and efficiently. You monitor resource usage, identify bottlenecks, and "
                "make recommendations for optimization. You balance thoroughness with "
                "efficiency to ensure Sage provides value without being intrusive.")
    
    def create_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """Create performance monitoring tasks."""
        tasks = []
        
        if context.get('performance_check'):
            project_path = context.get('project_path', 'system-wide')
            tasks.append(Task(
                description=f"""Check system performance and resource usage for {project_path}.

Use the performance_monitor tool to gather system metrics.
Use the memory_bank_update tool to log performance data in progress.md.

Monitor:
1. CPU usage and trends
2. Memory consumption and available memory
3. Disk usage and I/O patterns
4. Sage process resource consumption
5. File monitoring overhead
6. Context processing performance

Analyze:
- Current resource usage vs. configured limits
- Performance trends over time
- Potential bottlenecks or resource constraints
- Impact on host system performance
- Efficiency of current operations

Recommendations:
- Suggest configuration adjustments if needed
- Identify optimization opportunities
- Recommend throttling if resource usage is high
- Alert if system resources are constrained

Thresholds for concern:
- CPU usage > 80% sustained
- Memory usage > 85% of available
- Disk usage > 90% of available
- Sage process using > 1GB memory consistently""",
                agent=self.create_agent(),
                expected_output="Performance report with current metrics, analysis, and optimization recommendations"
            ))
        
        return tasks
