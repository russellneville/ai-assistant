"""Crew management system for Sage agents."""

import logging
from typing import Dict, List, Type, Any, Optional
from crewai import Crew, Task
from pathlib import Path

from .base import (
    SageAgent, ContextCurator, ProjectMonitor, TechnologySpecialist,
    DecisionLogger, ConflictResolver, PerformanceMonitor
)
from ..config.models import SageConfig, CrewConfig, ProjectConfig


class CrewManager:
    """Manages CrewAI crews for different projects and contexts."""
    
    # Registry of available agent types
    AGENT_REGISTRY: Dict[str, Type[SageAgent]] = {
        'context_curator': ContextCurator,
        'project_monitor': ProjectMonitor,
        'tech_specialist': TechnologySpecialist,
        'technology_specialist': TechnologySpecialist,  # Alias
        'decision_logger': DecisionLogger,
        'conflict_resolver': ConflictResolver,
        'performance_monitor': PerformanceMonitor,
    }
    
    def __init__(self, config: SageConfig):
        """Initialize crew manager with configuration."""
        self.config = config
        self.crews: Dict[str, Crew] = {}
        self.agents: Dict[str, Dict[str, SageAgent]] = {}
        self._initialize_crews()
    
    def _initialize_crews(self) -> None:
        """Initialize all crews based on configuration."""
        for crew_name, crew_config in self.config.crews.items():
            try:
                self._create_crew(crew_name, crew_config)
                logging.info(f"Initialized crew: {crew_name}")
            except Exception as e:
                logging.error(f"Failed to initialize crew {crew_name}: {e}")
    
    def _create_crew(self, crew_name: str, crew_config: CrewConfig) -> None:
        """Create a crew with specified agents."""
        # Create agents for this crew
        crew_agents = {}
        agents_list = []
        
        for agent_name in crew_config.agents:
            if agent_name not in self.AGENT_REGISTRY:
                logging.warning(f"Unknown agent type: {agent_name}")
                continue
            
            agent_class = self.AGENT_REGISTRY[agent_name]
            
            # Create agent with appropriate dependencies
            try:
                agent = self._create_agent_with_dependencies(agent_class, crew_config)
                if agent:
                    crew_agents[agent_name] = agent
                    created_agent = agent.create_agent()
                    if created_agent:
                        agents_list.append(created_agent)
            except Exception as e:
                logging.error(f"Failed to create agent {agent_name}: {e}")
                continue
        
        if not agents_list:
            logging.error(f"No agents created for crew {crew_name}")
            return
        
        # Store agents for this crew
        self.agents[crew_name] = crew_agents
        
        # Create the crew
        try:
            crew = Crew(
                agents=agents_list,
                tasks=[],  # Tasks will be added dynamically
                verbose=False,
                memory=False
            )
        except Exception as e:
            logging.error(f"Failed to create crew {crew_name}: {e}")
            return
        
        self.crews[crew_name] = crew
    
    def _create_agent_with_dependencies(self, agent_class, crew_config: CrewConfig):
        """Create an agent with its required dependencies."""
        # Import here to avoid circular imports
        from ..core.bedrock_client import BedrockClient
        from ..context.store import ContextStore
        from ..context.memory_bank import MemoryBankManager
        from pathlib import Path
        
        # Initialize services if not already done
        if not hasattr(self, '_bedrock_client'):
            self._bedrock_client = BedrockClient(self.config.aws)
        
        if not hasattr(self, '_context_store'):
            context_store_path = Path("context-store")
            self._context_store = ContextStore(context_store_path)
        
        if not hasattr(self, '_memory_bank_manager'):
            self._memory_bank_manager = MemoryBankManager(self._context_store)
        
        # Create agent based on type with required dependencies
        if agent_class.__name__ == 'ContextCurator':
            return agent_class(self.config, crew_config, self._bedrock_client, self._context_store)
        elif agent_class.__name__ == 'ProjectMonitor':
            return agent_class(self.config, crew_config, self._bedrock_client, self._memory_bank_manager)
        elif agent_class.__name__ == 'TechnologySpecialist':
            return agent_class(self.config, crew_config, self._bedrock_client, self._context_store, self._memory_bank_manager)
        elif agent_class.__name__ == 'ConflictResolver':
            return agent_class(self.config, crew_config, self._bedrock_client, self._memory_bank_manager)
        elif agent_class.__name__ == 'PerformanceMonitor':
            return agent_class(self.config, crew_config, self._memory_bank_manager)
        elif agent_class.__name__ == 'DecisionLogger':
            # DecisionLogger doesn't need special dependencies yet
            return agent_class(self.config, crew_config)
        else:
            # Fallback for agents that don't need special dependencies
            return agent_class(self.config, crew_config)
    
    def get_crew(self, crew_name: str) -> Optional[Crew]:
        """Get a crew by name."""
        return self.crews.get(crew_name)
    
    def get_agent(self, crew_name: str, agent_name: str) -> Optional[SageAgent]:
        """Get a specific agent from a crew."""
        if crew_name in self.agents:
            return self.agents[crew_name].get(agent_name)
        return None
    
    def execute_crew_tasks(self, crew_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks for a specific crew with given context."""
        if crew_name not in self.crews:
            raise ValueError(f"Crew not found: {crew_name}")
        
        crew = self.crews[crew_name]
        crew_agents = self.agents[crew_name]
        
        # Collect tasks from all agents in the crew
        all_tasks = []
        for agent_name, agent in crew_agents.items():
            try:
                tasks = agent.create_tasks(context)
                all_tasks.extend(tasks)
            except Exception as e:
                logging.error(f"Error creating tasks for agent {agent_name}: {e}")
        
        if not all_tasks:
            logging.info(f"No tasks to execute for crew: {crew_name}")
            return {"status": "no_tasks", "crew": crew_name}
        
        # Update crew with new tasks
        crew.tasks = all_tasks
        
        try:
            # Execute the crew
            result = crew.kickoff()
            logging.info(f"Crew {crew_name} execution completed")
            return {
                "status": "success",
                "crew": crew_name,
                "result": result,
                "tasks_executed": len(all_tasks)
            }
        except Exception as e:
            logging.error(f"Error executing crew {crew_name}: {e}")
            return {
                "status": "error",
                "crew": crew_name,
                "error": str(e),
                "tasks_attempted": len(all_tasks)
            }
    
    def execute_project_analysis(self, project: ProjectConfig, 
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute analysis for a specific project."""
        if context is None:
            context = {}
        
        # Add project-specific context
        context.update({
            "project_path": project.path,
            "project_priority": project.priority,
            "new_project": context.get("new_project", False),
            "project_analysis": True
        })
        
        return self.execute_crew_tasks(project.crew_config, context)
    
    def execute_file_change_analysis(self, project: ProjectConfig, 
                                   file_changes: List[Any],
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute analysis for file changes in a project."""
        if context is None:
            context = {}
        
        # Add file change context
        context.update({
            "project_path": project.path,
            "file_changes": file_changes,
            "change_count": len(file_changes)
        })
        
        return self.execute_crew_tasks(project.crew_config, context)
    
    def execute_context_matching(self, project: ProjectConfig,
                               technologies: List[str],
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute context matching for a project."""
        if context is None:
            context = {}
        
        # Add context matching information
        context.update({
            "project_path": project.path,
            "technologies": technologies,
            "context_matching": True
        })
        
        return self.execute_crew_tasks(project.crew_config, context)
    
    def log_decision(self, decision: str, reasoning: str, 
                    context: Optional[Dict[str, Any]] = None) -> None:
        """Log a decision across all crews with decision loggers."""
        if context is None:
            context = {}
        
        context.update({
            "decision_made": True,
            "decision": decision,
            "reasoning": reasoning
        })
        
        # Execute decision logging for all crews that have decision loggers
        for crew_name, crew_agents in self.agents.items():
            if "decision_logger" in crew_agents:
                try:
                    self.execute_crew_tasks(crew_name, context)
                except Exception as e:
                    logging.error(f"Error logging decision with crew {crew_name}: {e}")
    
    def handle_conflict(self, conflict_description: str, 
                       options: List[str],
                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a conflict using conflict resolver agents."""
        if context is None:
            context = {}
        
        context.update({
            "conflict_detected": True,
            "conflict_description": conflict_description,
            "options": options
        })
        
        # Find crews with conflict resolvers
        results = []
        for crew_name, crew_agents in self.agents.items():
            if "conflict_resolver" in crew_agents:
                try:
                    result = self.execute_crew_tasks(crew_name, context)
                    results.append(result)
                except Exception as e:
                    logging.error(f"Error resolving conflict with crew {crew_name}: {e}")
        
        return {
            "conflict_resolution_results": results,
            "requires_user_input": any(r.get("requires_user_input", False) for r in results)
        }
    
    def check_performance(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Check system performance across all crews."""
        if context is None:
            context = {}
        
        context.update({
            "performance_check": True
        })
        
        results = []
        for crew_name, crew_agents in self.agents.items():
            if "performance_monitor" in crew_agents:
                try:
                    result = self.execute_crew_tasks(crew_name, context)
                    results.append(result)
                except Exception as e:
                    logging.error(f"Error checking performance with crew {crew_name}: {e}")
        
        return results
    
    def shutdown_all_crews(self) -> None:
        """Shutdown all crews and clean up resources."""
        logging.info("Shutting down all crews...")
        
        # Clear crews and agents
        self.crews.clear()
        self.agents.clear()
        
        logging.info("All crews shutdown complete")
