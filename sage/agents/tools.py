"""CrewAI tools for Sage agents."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..core.bedrock_client import BedrockClient
from ..context.store import ContextStore
from ..context.memory_bank import MemoryBankManager


class CodeAnalysisTool(BaseTool):
    """Tool for analyzing code files using Bedrock."""
    
    name: str = "code_analysis"
    description: str = "Analyze code files to extract technologies, patterns, and context"
    
    def __init__(self, bedrock_client: BedrockClient):
        super().__init__()
        self.bedrock_client = bedrock_client
    
    def _run(self, file_path: str, analysis_type: str = "general") -> str:
        """Run code analysis on a file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"File not found: {file_path}"
            
            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                return f"Cannot read file (binary or unsupported encoding): {file_path}"
            
            # Skip very large files
            if len(content) > 50000:
                content = content[:50000] + "\n... (truncated)"
            
            # Analyze with Bedrock
            response = self.bedrock_client.analyze_code(content, file_path, analysis_type)
            return response.content
            
        except Exception as e:
            logging.error(f"Error in code analysis tool: {e}")
            return f"Error analyzing file: {str(e)}"


class TechnologyDetectionTool(BaseTool):
    """Tool for detecting technologies in project files."""
    
    name: str = "technology_detection"
    description: str = "Detect technologies, frameworks, and tools used in a project"
    
    def __init__(self, bedrock_client: BedrockClient):
        super().__init__()
        self.bedrock_client = bedrock_client
    
    def _run(self, project_path: str, file_extensions: str = ".py,.js,.ts,.java,.go,.rs") -> str:
        """Detect technologies in a project."""
        try:
            project_dir = Path(project_path)
            if not project_dir.exists():
                return f"Project path not found: {project_path}"
            
            # Collect sample files
            extensions = [ext.strip() for ext in file_extensions.split(',')]
            sample_files = []
            
            for ext in extensions:
                files = list(project_dir.rglob(f"*{ext}"))[:5]  # Max 5 files per extension
                for file_path in files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()[:2000]  # First 2000 chars
                        try:
                            relative_path = str(file_path.relative_to(project_dir))
                        except ValueError:
                            # File is not within project directory, use absolute path
                            relative_path = str(file_path)
                        
                        sample_files.append({
                            'path': relative_path,
                            'content': content
                        })
                    except (UnicodeDecodeError, PermissionError):
                        continue
            
            if not sample_files:
                return "No readable source files found in project"
            
            # Analyze with Bedrock
            response = self.bedrock_client.extract_technologies(sample_files)
            return response.content
            
        except Exception as e:
            logging.error(f"Error in technology detection tool: {e}")
            return f"Error detecting technologies: {str(e)}"


class ContextSearchTool(BaseTool):
    """Tool for searching the global context store."""
    
    name: str = "context_search"
    description: str = "Search the global context store for relevant information"
    
    def __init__(self, context_store: ContextStore):
        super().__init__()
        self.context_store = context_store
    
    def _run(self, query: str, technologies: str = "", category: str = "", limit: str = "5") -> str:
        """Search for contexts."""
        try:
            tech_list = [t.strip() for t in technologies.split(',') if t.strip()] if technologies else None
            search_limit = int(limit) if limit.isdigit() else 5
            
            results = self.context_store.search_contexts(
                query=query,
                technologies=tech_list,
                category=category if category else None,
                limit=search_limit
            )
            
            if not results:
                return f"No contexts found for query: {query}"
            
            output = f"Found {len(results)} relevant contexts:\n\n"
            for i, context in enumerate(results, 1):
                output += f"{i}. **{context.title}** (Score: {context.relevance_score:.1f})\n"
                output += f"   Category: {context.category}/{context.subcategory}\n"
                output += f"   Technologies: {', '.join(context.technologies)}\n"
                output += f"   Content: {context.content[:200]}...\n\n"
            
            return output
            
        except Exception as e:
            logging.error(f"Error in context search tool: {e}")
            return f"Error searching contexts: {str(e)}"


class ContextAddTool(BaseTool):
    """Tool for adding new context to the global store."""
    
    name: str = "context_add"
    description: str = "Add new context information to the global store"
    
    def __init__(self, context_store: ContextStore):
        super().__init__()
        self.context_store = context_store
    
    def _run(self, title: str, content: str, category: str, subcategory: str, 
             source: str, technologies: str = "", tags: str = "") -> str:
        """Add context to the store."""
        try:
            tech_list = [t.strip() for t in technologies.split(',') if t.strip()] if technologies else []
            tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else []
            
            context_id = self.context_store.add_context(
                title=title,
                content=content,
                category=category,
                subcategory=subcategory,
                source=source,
                technologies=tech_list,
                tags=tag_list
            )
            
            return f"Successfully added context with ID: {context_id}"
            
        except Exception as e:
            logging.error(f"Error in context add tool: {e}")
            return f"Error adding context: {str(e)}"


class MemoryBankUpdateTool(BaseTool):
    """Tool for updating project memory banks."""
    
    name: str = "memory_bank_update"
    description: str = "Update project memory bank with new information"
    
    def __init__(self, memory_bank_manager: MemoryBankManager):
        super().__init__()
        self.memory_bank_manager = memory_bank_manager
    
    def _run(self, project_path: str, filename: str, section: str, content: str) -> str:
        """Update memory bank section."""
        try:
            project_dir = Path(project_path)
            memory_bank = self.memory_bank_manager.get_memory_bank(project_dir)
            memory_bank.update_memory_section(filename, section, content)
            
            return f"Successfully updated {section} in {filename}"
            
        except Exception as e:
            logging.error(f"Error in memory bank update tool: {e}")
            return f"Error updating memory bank: {str(e)}"


class FileSystemTool(BaseTool):
    """Tool for basic file system operations."""
    
    name: str = "file_system"
    description: str = "Read file contents and list directory contents"
    
    def _run(self, operation: str, path: str, pattern: str = "*") -> str:
        """Perform file system operations."""
        try:
            target_path = Path(path)
            
            if operation == "read":
                if not target_path.exists():
                    return f"File not found: {path}"
                
                try:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Truncate very large files
                    if len(content) > 10000:
                        content = content[:10000] + "\n... (truncated)"
                    
                    return content
                except UnicodeDecodeError:
                    return f"Cannot read file (binary or unsupported encoding): {path}"
            
            elif operation == "list":
                if not target_path.exists():
                    return f"Directory not found: {path}"
                
                if target_path.is_file():
                    return f"Path is a file, not a directory: {path}"
                
                items = []
                for item in target_path.glob(pattern):
                    item_type = "dir" if item.is_dir() else "file"
                    items.append(f"{item_type}: {item.name}")
                
                if not items:
                    return f"No items found matching pattern: {pattern}"
                
                return "\n".join(sorted(items))
            
            else:
                return f"Unknown operation: {operation}. Use 'read' or 'list'"
                
        except Exception as e:
            logging.error(f"Error in file system tool: {e}")
            return f"Error with file system operation: {str(e)}"


class ConflictResolutionTool(BaseTool):
    """Tool for analyzing and resolving conflicts."""
    
    name: str = "conflict_resolution"
    description: str = "Analyze conflicts and suggest resolutions"
    
    def __init__(self, bedrock_client: BedrockClient):
        super().__init__()
        self.bedrock_client = bedrock_client
    
    def _run(self, conflict_description: str, options: str) -> str:
        """Analyze conflict and suggest resolution."""
        try:
            option_list = [opt.strip() for opt in options.split('|') if opt.strip()]
            
            response = self.bedrock_client.resolve_conflict(conflict_description, option_list)
            return response.content
            
        except Exception as e:
            logging.error(f"Error in conflict resolution tool: {e}")
            return f"Error resolving conflict: {str(e)}"


class PersonalityTool(BaseTool):
    """Tool for determining appropriate personality expressions."""
    
    name: str = "personality_expression"
    description: str = "Determine appropriate emotional expression for Sage"
    
    def __init__(self, bedrock_client: BedrockClient):
        super().__init__()
        self.bedrock_client = bedrock_client
    
    def _run(self, message: str, context: str = "{}") -> str:
        """Determine appropriate emotion."""
        try:
            import json
            context_dict = json.loads(context) if context != "{}" else {}
            
            response = self.bedrock_client.determine_emotion(message, context_dict)
            return response.content
            
        except Exception as e:
            logging.error(f"Error in personality tool: {e}")
            return f"Error determining emotion: {str(e)}"


class PerformanceMonitorTool(BaseTool):
    """Tool for monitoring system performance."""
    
    name: str = "performance_monitor"
    description: str = "Monitor system resource usage and performance"
    
    def _run(self, metric: str = "all") -> str:
        """Monitor system performance."""
        try:
            import psutil
            import os
            
            if metric == "memory" or metric == "all":
                memory = psutil.virtual_memory()
                memory_info = f"Memory Usage: {memory.percent}% ({memory.used // (1024**2)} MB used of {memory.total // (1024**2)} MB)"
            
            if metric == "cpu" or metric == "all":
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_info = f"CPU Usage: {cpu_percent}%"
            
            if metric == "disk" or metric == "all":
                disk = psutil.disk_usage('/')
                disk_info = f"Disk Usage: {disk.percent}% ({disk.used // (1024**3)} GB used of {disk.total // (1024**3)} GB)"
            
            if metric == "process" or metric == "all":
                process = psutil.Process(os.getpid())
                process_memory = process.memory_info().rss // (1024**2)
                process_cpu = process.cpu_percent()
                process_info = f"Sage Process: {process_memory} MB memory, {process_cpu}% CPU"
            
            if metric == "all":
                return f"{memory_info}\n{cpu_info}\n{disk_info}\n{process_info}"
            elif metric == "memory":
                return memory_info
            elif metric == "cpu":
                return cpu_info
            elif metric == "disk":
                return disk_info
            elif metric == "process":
                return process_info
            else:
                return f"Unknown metric: {metric}. Use: memory, cpu, disk, process, or all"
                
        except ImportError:
            return "psutil not available for performance monitoring"
        except Exception as e:
            logging.error(f"Error in performance monitor tool: {e}")
            return f"Error monitoring performance: {str(e)}"
