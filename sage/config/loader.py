"""Configuration loading and management for Sage."""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import ValidationError

from .models import SageConfig


class ConfigLoader:
    """Handles loading and validation of Sage configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config loader with optional config path."""
        self.config_path = config_path or Path("config.yaml")
        self._config: Optional[SageConfig] = None
    
    def load_config(self) -> SageConfig:
        """Load and validate configuration from file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                config_data = {}
            
            self._config = SageConfig(**config_data)
            return self._config
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def get_config(self) -> SageConfig:
        """Get loaded configuration, loading it if necessary."""
        if self._config is None:
            self.load_config()
        return self._config
    
    def reload_config(self) -> SageConfig:
        """Force reload configuration from file."""
        self._config = None
        return self.load_config()
    
    @staticmethod
    def create_default_config(path: Path) -> None:
        """Create a default configuration file."""
        default_config = {
            "projects": [
                {
                    "path": "/path/to/your/project",
                    "crew_config": "general_development",
                    "priority": "high"
                }
            ],
            "crews": {
                "general_development": {
                    "agents": ["context_curator", "project_monitor", "tech_specialist"],
                    "specializations": ["python", "javascript", "general"]
                }
            },
            "aws": {
                "region": "us-east-1",
                "bedrock": {
                    "model": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                    "max_tokens": 4096
                }
            },
            "mcp": {
                "registry_path": None,
                "enabled_tools": []
            },
            "performance": {
                "file_monitor_frequency": 5,
                "background_frequency": 30,
                "batch_update_interval": 120,
                "max_concurrent_ops": 10
            },
            "ui": {
                "personality": {
                    "expressions_map": "./personality/expressions-video.json",
                    "default_emotion": "neutral"
                },
                "browser": {
                    "port": 8080,
                    "auto_open": True
                }
            }
        }
        
        with open(path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    @staticmethod
    def create_default_sageignore(path: Path) -> None:
        """Create a default .sageignore file."""
        ignore_patterns = [
            "# Version control",
            ".git/",
            ".svn/",
            ".hg/",
            "",
            "# Dependencies",
            "node_modules/",
            "vendor/",
            ".venv/",
            "venv/",
            "__pycache__/",
            "",
            "# Build outputs",
            "dist/",
            "build/",
            "target/",
            "*.o",
            "*.exe",
            "",
            "# IDE files",
            ".vscode/",
            ".idea/",
            "*.swp",
            "*.swo",
            "",
            "# Logs",
            "*.log",
            "logs/",
            "",
            "# Sage generated",
            "context-store/",
            "memory-banks/",
            ".sage/",
            "",
            "# User-defined patterns",
            "# Add custom ignore patterns below",
        ]
        
        with open(path, 'w') as f:
            f.write('\n'.join(ignore_patterns))
