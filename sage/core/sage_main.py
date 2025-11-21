"""Main Sage application orchestrator."""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from ..config.loader import ConfigLoader
from ..config.models import SageConfig
from ..core.file_monitor import FileMonitor, FileChangeEvent
from ..core.bedrock_client import BedrockClient
from ..agents.crew_manager import CrewManager
from ..context.store import ContextStore
from ..context.memory_bank import MemoryBankManager
from ..ui.personality import PersonalitySystem
from ..ui.web_server import SageWebServer


class SageApplication:
    """Main Sage application class."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Sage application."""
        self.config_path = config_path
        self.config: Optional[SageConfig] = None
        self.config_loader: Optional[ConfigLoader] = None
        
        # Core components
        self.bedrock_client: Optional[BedrockClient] = None
        self.context_store: Optional[ContextStore] = None
        self.memory_bank_manager: Optional[MemoryBankManager] = None
        self.crew_manager: Optional[CrewManager] = None
        self.file_monitor: Optional[FileMonitor] = None
        self.personality_system: Optional[PersonalitySystem] = None
        self.web_server: Optional[SageWebServer] = None
        
        # Runtime state
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Setup logging
        self._setup_logging()
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('sage.log')
            ]
        )
        
        # Reduce verbosity of some libraries
        logging.getLogger('watchdog').setLevel(logging.WARNING)
        logging.getLogger('uvicorn').setLevel(logging.WARNING)
        logging.getLogger('fastapi').setLevel(logging.WARNING)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logging.info(f"Received signal {signum}, shutting down gracefully...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize(self) -> bool:
        """Initialize all Sage components."""
        try:
            logging.info("🚀 Initializing Sage - AI Project Context Assistant")
            
            # Load configuration
            if not await self._load_configuration():
                return False
            
            # Initialize core components
            if not await self._initialize_core_components():
                return False
            
            # Initialize agents and crews
            if not await self._initialize_agents():
                return False
            
            # Initialize UI components
            if not await self._initialize_ui():
                return False
            
            # Setup file monitoring
            if not await self._setup_file_monitoring():
                return False
            
            logging.info("✅ Sage initialization complete")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize Sage: {e}")
            return False
    
    async def _load_configuration(self) -> bool:
        """Load and validate configuration."""
        try:
            self.config_loader = ConfigLoader(self.config_path)
            self.config = self.config_loader.load_config()
            
            logging.info(f"📋 Configuration loaded from {self.config_loader.config_path}")
            logging.info(f"🎯 Monitoring {len(self.config.projects)} projects")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Configuration loading failed: {e}")
            return False
    
    async def _initialize_core_components(self) -> bool:
        """Initialize core Sage components."""
        try:
            # Initialize Bedrock client
            self.bedrock_client = BedrockClient(self.config.aws)
            
            # Test Bedrock connection
            if not self.bedrock_client.health_check():
                logging.warning("⚠️  Bedrock health check failed, continuing with limited functionality")
            else:
                logging.info("🤖 Bedrock client initialized successfully")
            
            # Initialize context store
            context_store_path = Path("context-store")
            self.context_store = ContextStore(context_store_path)
            logging.info(f"📚 Context store initialized at {context_store_path}")
            
            # Initialize memory bank manager
            self.memory_bank_manager = MemoryBankManager(self.context_store)
            logging.info("🧠 Memory bank manager initialized")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Core components initialization failed: {e}")
            return False
    
    async def _initialize_agents(self) -> bool:
        """Initialize CrewAI agents and crews."""
        try:
            self.crew_manager = CrewManager(self.config)
            logging.info(f"👥 Crew manager initialized with {len(self.config.crews)} crews")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Agent initialization failed: {e}")
            return False
    
    async def _initialize_ui(self) -> bool:
        """Initialize UI components."""
        try:
            # Initialize personality system
            self.personality_system = PersonalitySystem(
                self.config.ui.personality.expressions_map,
                self.bedrock_client
            )
            
            # Validate personality configuration
            validation = self.personality_system.validate_expressions_config()
            if not validation['valid']:
                logging.warning(f"⚠️  Personality configuration issues: {validation['errors']}")
            
            logging.info(f"😊 Personality system initialized with {len(self.personality_system.expressions)} expressions")
            
            # Initialize web server
            self.web_server = SageWebServer(
                self.config,
                self.personality_system,
                self.bedrock_client
            )
            
            logging.info("🌐 Web server initialized")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ UI initialization failed: {e}")
            return False
    
    async def _setup_file_monitoring(self) -> bool:
        """Setup file monitoring system."""
        try:
            self.file_monitor = FileMonitor(self.config)
            
            # Add event callback
            self.file_monitor.add_event_callback(self._handle_file_change)
            
            logging.info("👁️  File monitoring system configured")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ File monitoring setup failed: {e}")
            return False
    
    async def _handle_file_change(self, event: FileChangeEvent):
        """Handle file change events."""
        try:
            logging.info(f"📝 File {event.event_type}: {event.src_path}")
            
            # Notify web UI
            if self.web_server:
                await self.web_server.send_file_change_notification(
                    str(event.src_path), 
                    event.event_type
                )
            
            # Find the project configuration for this file
            project_config = None
            for project in self.config.projects:
                if str(event.src_path).startswith(str(project.path)):
                    project_config = project
                    break
            
            if not project_config:
                logging.warning(f"No project configuration found for {event.src_path}")
                return
            
            # Process file change asynchronously
            await self._process_file_change_async(event, project_config)
            
        except Exception as e:
            logging.error(f"Error handling file change: {e}")
    
    async def _process_file_change_async(self, event: FileChangeEvent, project_config):
        """Process file change asynchronously."""
        try:
            # Run crew analysis for the file change
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.crew_manager.execute_file_change_analysis,
                project_config,
                [event],
                {"file_change_event": event}
            )
            
            if result['status'] == 'success':
                logging.info(f"✅ File change analysis completed for {project_config.path}")
                
                # Update memory bank if needed
                if self.memory_bank_manager:
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        self.memory_bank_manager.update_project_context,
                        project_config.path,
                        [],  # Technologies - could be extracted from analysis
                        [f"{event.event_type}: {event.src_path}"]
                    )
            
        except Exception as e:
            logging.error(f"Error processing file change: {e}")
    
    async def run(self):
        """Run the main Sage application."""
        if not await self.initialize():
            logging.error("❌ Failed to initialize Sage")
            return
        
        try:
            self.is_running = True
            
            # Start file monitoring
            self.file_monitor.start_monitoring()
            
            # Perform initial project analysis
            await self._perform_initial_analysis()
            
            # Send startup notification
            if self.web_server:
                await self.web_server.send_system_notification(
                    "Sage is now online and monitoring your projects! 🚀",
                    "startup"
                )
            
            # Start web server (this will block)
            await self.web_server.start_server()
            
        except Exception as e:
            logging.error(f"❌ Error running Sage: {e}")
        finally:
            await self.shutdown()
    
    async def _perform_initial_analysis(self):
        """Perform initial analysis of all configured projects."""
        logging.info("🔍 Performing initial project analysis...")
        
        for project in self.config.projects:
            try:
                # Run project analysis
                result = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.crew_manager.execute_project_analysis,
                    project,
                    {"new_project": True}
                )
                
                if result['status'] == 'success':
                    logging.info(f"✅ Initial analysis completed for {project.path}")
                else:
                    logging.warning(f"⚠️  Initial analysis had issues for {project.path}: {result}")
                
            except Exception as e:
                logging.error(f"❌ Error analyzing project {project.path}: {e}")
        
        logging.info("🎯 Initial project analysis complete")
    
    async def shutdown(self):
        """Shutdown Sage gracefully."""
        if not self.is_running:
            return
        
        logging.info("🛑 Shutting down Sage...")
        
        self.is_running = False
        
        try:
            # Stop file monitoring
            if self.file_monitor:
                self.file_monitor.stop_monitoring()
                logging.info("👁️  File monitoring stopped")
            
            # Shutdown crews
            if self.crew_manager:
                self.crew_manager.shutdown_all_crews()
                logging.info("👥 All crews shutdown")
            
            # Shutdown executor
            self.executor.shutdown(wait=True)
            logging.info("⚙️  Executor shutdown")
            
            # Send shutdown notification
            if self.web_server:
                await self.web_server.send_system_notification(
                    "Sage is shutting down. Goodbye! 👋",
                    "shutdown"
                )
            
            logging.info("✅ Sage shutdown complete")
            
        except Exception as e:
            logging.error(f"❌ Error during shutdown: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of Sage."""
        return {
            "is_running": self.is_running,
            "config_loaded": self.config is not None,
            "components": {
                "bedrock_client": self.bedrock_client is not None,
                "context_store": self.context_store is not None,
                "memory_bank_manager": self.memory_bank_manager is not None,
                "crew_manager": self.crew_manager is not None,
                "file_monitor": self.file_monitor is not None and self.file_monitor.is_running,
                "personality_system": self.personality_system is not None,
                "web_server": self.web_server is not None
            },
            "projects_monitored": len(self.config.projects) if self.config else 0,
            "crews_configured": len(self.config.crews) if self.config else 0
        }


async def main():
    """Main entry point for Sage."""
    sage = SageApplication()
    await sage.run()


if __name__ == "__main__":
    asyncio.run(main())