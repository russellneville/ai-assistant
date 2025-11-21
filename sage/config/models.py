"""Configuration models for Sage using Pydantic."""

from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator


class ProjectConfig(BaseModel):
    """Configuration for a single project to monitor."""
    path: Path
    crew_config: str
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    
    @validator('path')
    def validate_path(cls, v):
        """Ensure path exists and is a directory."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Project path does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Project path is not a directory: {path}")
        return path


class CrewConfig(BaseModel):
    """Configuration for a CrewAI crew."""
    agents: List[str]
    specializations: List[str]


class AWSConfig(BaseModel):
    """AWS and Bedrock configuration."""
    region: str = "us-east-1"
    profile: Optional[str] = "poc"  # Default to poc profile for Bedrock access
    bedrock: Dict[str, Any] = Field(default_factory=lambda: {
        "model": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "max_tokens": 4096
    })


class MCPConfig(BaseModel):
    """MCP tools configuration."""
    registry_path: Optional[Path] = None
    enabled_tools: List[str] = Field(default_factory=list)


class PerformanceConfig(BaseModel):
    """Performance and resource management configuration."""
    file_monitor_frequency: int = Field(default=5, ge=1, le=60)
    background_frequency: int = Field(default=30, ge=5, le=300)
    batch_update_interval: int = Field(default=120, ge=30, le=600)
    max_concurrent_ops: int = Field(default=10, ge=1, le=50)


class PersonalityConfig(BaseModel):
    """Personality system configuration."""
    expressions_map: Path = Field(default=Path("./personality/expressions-video.json"))
    default_emotion: str = "neutral"
    
    @validator('expressions_map')
    def validate_expressions_map(cls, v):
        """Ensure expressions map file exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Expressions map file does not exist: {path}")
        return path


class UIConfig(BaseModel):
    """User interface configuration."""
    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)
    browser: Dict[str, Any] = Field(default_factory=lambda: {
        "port": 8080,
        "auto_open": True
    })


class SageConfig(BaseModel):
    """Main Sage configuration."""
    projects: List[ProjectConfig] = Field(default_factory=list)
    crews: Dict[str, CrewConfig] = Field(default_factory=dict)
    aws: AWSConfig = Field(default_factory=AWSConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    
    @validator('projects')
    def validate_projects_not_empty(cls, v):
        """Ensure at least one project is configured."""
        if not v:
            raise ValueError("At least one project must be configured")
        return v
    
    @validator('crews')
    def validate_crew_configs(cls, v, values):
        """Ensure all referenced crew configs exist."""
        if 'projects' in values:
            referenced_crews = {p.crew_config for p in values['projects']}
            missing_crews = referenced_crews - set(v.keys())
            if missing_crews:
                raise ValueError(f"Missing crew configurations: {missing_crews}")
        return v
