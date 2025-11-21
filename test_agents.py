#!/usr/bin/env python3
"""
Simple test script to verify Sage agent implementations work correctly.
This is a basic integration test to ensure the agents can be created and execute tasks.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sage.config.models import SageConfig, CrewConfig, ProjectConfig, AWSConfig, UIConfig
from sage.agents.crew_manager import CrewManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_config():
    """Create a test configuration for Sage."""
    
    # Create test project config
    test_project = ProjectConfig(
        path=Path("."),  # Use current directory as test project
        crew_config="test_crew",
        priority="high"
    )
    
    # Create test crew config
    test_crew = CrewConfig(
        agents=["context_curator", "tech_specialist", "project_monitor"],
        specializations=["python", "ai", "testing"]
    )
    
    # Create AWS config (will use default values)
    aws_config = AWSConfig()
    
    # Create UI config
    ui_config = UIConfig()
    
    # Create main config
    config = SageConfig(
        projects=[test_project],
        crews={"test_crew": test_crew},
        aws=aws_config,
        ui=ui_config
    )
    
    return config


async def test_crew_creation():
    """Test that crews can be created successfully."""
    logger.info("Testing crew creation...")
    
    try:
        config = create_test_config()
        crew_manager = CrewManager(config)
        
        # Check if crews were created
        if "test_crew" in crew_manager.crews:
            logger.info("✅ Test crew created successfully")
            
            # Check agents in the crew
            if "test_crew" in crew_manager.agents:
                agents = crew_manager.agents["test_crew"]
                logger.info(f"✅ Created {len(agents)} agents: {list(agents.keys())}")
                
                # Test each agent
                for agent_name, agent in agents.items():
                    if agent:
                        logger.info(f"✅ Agent {agent_name} created successfully")
                        logger.info(f"   - Role: {agent.role}")
                        logger.info(f"   - Tools: {len(agent.get_tools())} tools available")
                    else:
                        logger.error(f"❌ Agent {agent_name} failed to create")
            else:
                logger.error("❌ No agents found in test crew")
        else:
            logger.error("❌ Test crew not created")
            
    except Exception as e:
        logger.error(f"❌ Error during crew creation test: {e}")
        import traceback
        traceback.print_exc()


async def test_task_creation():
    """Test that agents can create tasks."""
    logger.info("Testing task creation...")
    
    try:
        config = create_test_config()
        crew_manager = CrewManager(config)
        
        # Test context for task creation
        test_context = {
            "project_path": Path("."),
            "new_project": True,
            "project_analysis": True
        }
        
        # Get test crew agents
        if "test_crew" in crew_manager.agents:
            agents = crew_manager.agents["test_crew"]
            
            for agent_name, agent in agents.items():
                try:
                    tasks = agent.create_tasks(test_context)
                    logger.info(f"✅ Agent {agent_name} created {len(tasks)} tasks")
                    
                    for i, task in enumerate(tasks):
                        logger.info(f"   Task {i+1}: {task.description[:100]}...")
                        
                except Exception as e:
                    logger.error(f"❌ Agent {agent_name} failed to create tasks: {e}")
        else:
            logger.error("❌ No test crew found for task creation test")
            
    except Exception as e:
        logger.error(f"❌ Error during task creation test: {e}")
        import traceback
        traceback.print_exc()


async def test_tools():
    """Test that agent tools work correctly."""
    logger.info("Testing agent tools...")
    
    try:
        config = create_test_config()
        crew_manager = CrewManager(config)
        
        # Get test crew agents
        if "test_crew" in crew_manager.agents:
            agents = crew_manager.agents["test_crew"]
            
            for agent_name, agent in agents.items():
                tools = agent.get_tools()
                logger.info(f"✅ Agent {agent_name} has {len(tools)} tools:")
                
                for tool in tools:
                    logger.info(f"   - {tool.name}: {tool.description}")
                    
                    # Test a simple tool operation (file_system tool if available)
                    if tool.name == "file_system":
                        try:
                            result = tool._run("list", ".", "*.py")
                            logger.info(f"   ✅ Tool {tool.name} executed successfully")
                            logger.info(f"      Result preview: {result[:100]}...")
                        except Exception as e:
                            logger.error(f"   ❌ Tool {tool.name} failed: {e}")
        else:
            logger.error("❌ No test crew found for tools test")
            
    except Exception as e:
        logger.error(f"❌ Error during tools test: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Sage Agent Tests")
    logger.info("=" * 50)
    
    await test_crew_creation()
    logger.info("-" * 30)
    
    await test_task_creation()
    logger.info("-" * 30)
    
    await test_tools()
    logger.info("-" * 30)
    
    logger.info("🎯 Sage Agent Tests Complete")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
