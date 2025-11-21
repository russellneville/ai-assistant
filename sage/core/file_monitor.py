"""File monitoring system for Sage using watchdog."""

import asyncio
import logging
from pathlib import Path
from typing import Set, Callable, Optional, Dict, List
from fnmatch import fnmatch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from pydantic import BaseModel

from ..config.models import SageConfig, ProjectConfig


class IgnorePatterns:
    """Manages ignore patterns for file monitoring."""
    
    def __init__(self, ignore_file: Optional[Path] = None):
        """Initialize with optional ignore file path."""
        self.patterns: Set[str] = set()
        self.ignore_file = ignore_file or Path(".sageignore")
        self.load_patterns()
    
    def load_patterns(self) -> None:
        """Load ignore patterns from file."""
        if not self.ignore_file.exists():
            return
        
        try:
            with open(self.ignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.patterns.add(line)
        except Exception as e:
            logging.warning(f"Failed to load ignore patterns: {e}")
    
    def should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        path_str = str(path)
        
        # Safely get relative path
        try:
            relative_path = str(path.relative_to(Path.cwd())) if path.is_absolute() else path_str
        except ValueError:
            # Path is not within current working directory, use absolute path
            relative_path = path_str
        
        for pattern in self.patterns:
            if fnmatch(path_str, pattern) or fnmatch(relative_path, pattern):
                return True
            # Check if any parent directory matches
            for parent in path.parents:
                if fnmatch(str(parent), pattern):
                    return True
        
        return False


class FileChangeEvent(BaseModel):
    """Represents a file change event."""
    event_type: str
    src_path: Path
    dest_path: Optional[Path] = None
    is_directory: bool
    project_path: Path


class SageFileHandler(FileSystemEventHandler):
    """Custom file system event handler for Sage."""
    
    def __init__(self, project_path: Path, ignore_patterns: IgnorePatterns, 
                 callback: Callable[[FileChangeEvent], None]):
        """Initialize handler with project path, ignore patterns, and callback."""
        super().__init__()
        self.project_path = project_path
        self.ignore_patterns = ignore_patterns
        self.callback = callback
        self.monitored_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
            '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.clj', '.hs',
            '.md', '.txt', '.rst', '.adoc',
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            '.xml', '.html', '.css', '.scss', '.sass', '.less',
            '.sql', '.sh', '.bash', '.zsh', '.ps1', '.bat',
            'Makefile', 'Dockerfile', 'CMakeLists.txt', 'BUILD', 'WORKSPACE'
        }
    
    def should_process_file(self, path: Path) -> bool:
        """Check if a file should be processed."""
        if self.ignore_patterns.should_ignore(path):
            return False
        
        # Check if it's a monitored file type
        if path.suffix.lower() in self.monitored_extensions:
            return True
        
        # Check for files without extensions that we care about
        if path.suffix == '' and path.name in ['Makefile', 'Dockerfile', 'BUILD', 'WORKSPACE']:
            return True
        
        return False
    
    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event."""
        try:
            src_path = Path(event.src_path)
            
            # Skip if we shouldn't process this file
            if not event.is_directory and not self.should_process_file(src_path):
                return
            
            # Create event object
            change_event = FileChangeEvent(
                event_type=event.event_type,
                src_path=src_path,
                dest_path=Path(event.dest_path) if hasattr(event, 'dest_path') else None,
                is_directory=event.is_directory,
                project_path=self.project_path
            )
            
            # Call callback
            self.callback(change_event)
            
        except Exception as e:
            logging.error(f"Error processing file event: {e}")


class FileMonitor:
    """Main file monitoring system for Sage."""
    
    def __init__(self, config: SageConfig):
        """Initialize file monitor with configuration."""
        self.config = config
        self.observers: Dict[str, Observer] = {}
        self.ignore_patterns: Dict[str, IgnorePatterns] = {}
        self.event_callbacks: List[Callable[[FileChangeEvent], None]] = []
        self.is_running = False
    
    def add_event_callback(self, callback: Callable[[FileChangeEvent], None]) -> None:
        """Add a callback for file events."""
        self.event_callbacks.append(callback)
    
    def _handle_file_event(self, event: FileChangeEvent) -> None:
        """Handle a file change event by calling all registered callbacks."""
        logging.info(f"File {event.event_type}: {event.src_path}")
        
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logging.error(f"Error in file event callback: {e}")
    
    def start_monitoring(self) -> None:
        """Start monitoring all configured projects."""
        if self.is_running:
            logging.warning("File monitoring is already running")
            return
        
        logging.info("Starting file monitoring...")
        
        for project in self.config.projects:
            self._start_project_monitoring(project)
        
        self.is_running = True
        logging.info(f"Monitoring {len(self.config.projects)} projects")
    
    def _start_project_monitoring(self, project: ProjectConfig) -> None:
        """Start monitoring a specific project."""
        project_key = str(project.path)
        
        if project_key in self.observers:
            logging.warning(f"Already monitoring project: {project.path}")
            return
        
        # Load ignore patterns for this project
        ignore_file = project.path / ".sageignore"
        self.ignore_patterns[project_key] = IgnorePatterns(ignore_file)
        
        # Create handler and observer
        handler = SageFileHandler(
            project.path,
            self.ignore_patterns[project_key],
            self._handle_file_event
        )
        
        observer = Observer()
        observer.schedule(handler, str(project.path), recursive=True)
        observer.start()
        
        self.observers[project_key] = observer
        logging.info(f"Started monitoring: {project.path}")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring all projects."""
        if not self.is_running:
            return
        
        logging.info("Stopping file monitoring...")
        
        for project_key, observer in self.observers.items():
            observer.stop()
            observer.join()
        
        self.observers.clear()
        self.ignore_patterns.clear()
        self.is_running = False
        logging.info("File monitoring stopped")
    
    def reload_ignore_patterns(self) -> None:
        """Reload ignore patterns for all projects."""
        for project_key, ignore_patterns in self.ignore_patterns.items():
            ignore_patterns.load_patterns()
        
        logging.info("Reloaded ignore patterns for all projects")
    
    def is_monitoring_project(self, project_path: Path) -> bool:
        """Check if a project is currently being monitored."""
        return str(project_path) in self.observers
