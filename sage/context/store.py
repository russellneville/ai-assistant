"""Global context store management for Sage."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import hashlib
from pydantic import BaseModel


class ContextItem(BaseModel):
    """Represents a single context item in the global store."""
    id: str
    title: str
    content: str
    category: str
    subcategory: str
    tags: List[str] = []
    technologies: List[str] = []
    created_at: datetime
    updated_at: datetime
    source: str  # Project or source that contributed this context
    relevance_score: float = 0.0
    usage_count: int = 0


class ContextStore:
    """Manages the global context store for Sage."""
    
    def __init__(self, store_path: Path):
        """Initialize context store with storage path."""
        self.store_path = store_path
        self.contexts: Dict[str, ContextItem] = {}
        self.categories = {
            'technologies': ['frameworks', 'languages', 'databases', 'tools'],
            'patterns': ['architectural', 'design', 'deployment'],
            'environments': ['development', 'staging', 'production'],
            'domains': ['business-logic', 'integrations', 'security'],
            'solutions': ['common-issues', 'troubleshooting', 'best-practices']
        }
        self._ensure_directory_structure()
        self._load_contexts()
    
    def _ensure_directory_structure(self) -> None:
        """Ensure the context store directory structure exists."""
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        # Create category directories
        for category, subcategories in self.categories.items():
            category_path = self.store_path / category
            category_path.mkdir(exist_ok=True)
            
            for subcategory in subcategories:
                subcategory_path = category_path / subcategory
                subcategory_path.mkdir(exist_ok=True)
    
    def _generate_context_id(self, title: str, content: str) -> str:
        """Generate a unique ID for a context item."""
        content_hash = hashlib.md5(f"{title}:{content}".encode()).hexdigest()[:8]
        return f"ctx_{content_hash}"
    
    def _get_context_file_path(self, context_item: ContextItem) -> Path:
        """Get the file path for a context item."""
        return (self.store_path / context_item.category / 
                context_item.subcategory / f"{context_item.id}.md")
    
    def _load_contexts(self) -> None:
        """Load all contexts from the file system."""
        logging.info("Loading contexts from store...")
        
        context_count = 0
        for category_path in self.store_path.iterdir():
            if not category_path.is_dir():
                continue
            
            for subcategory_path in category_path.iterdir():
                if not subcategory_path.is_dir():
                    continue
                
                for context_file in subcategory_path.glob("*.md"):
                    try:
                        context_item = self._load_context_file(context_file)
                        if context_item:
                            self.contexts[context_item.id] = context_item
                            context_count += 1
                    except Exception as e:
                        logging.error(f"Error loading context file {context_file}: {e}")
        
        logging.info(f"Loaded {context_count} contexts from store")
    
    def _load_context_file(self, file_path: Path) -> Optional[ContextItem]:
        """Load a single context file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse metadata from frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    metadata_yaml = parts[1].strip()
                    content_body = parts[2].strip()
                    
                    # Simple YAML parsing for metadata
                    metadata = {}
                    for line in metadata_yaml.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Handle lists
                            if value.startswith('[') and value.endswith(']'):
                                value = [v.strip().strip('"\'') for v in value[1:-1].split(',') if v.strip()]
                            # Handle strings
                            elif value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            # Handle numbers
                            elif value.replace('.', '').isdigit():
                                value = float(value) if '.' in value else int(value)
                            
                            metadata[key] = value
                    
                    # Create context item
                    context_id = file_path.stem
                    return ContextItem(
                        id=context_id,
                        title=metadata.get('title', context_id),
                        content=content_body,
                        category=metadata.get('category', file_path.parent.parent.name),
                        subcategory=metadata.get('subcategory', file_path.parent.name),
                        tags=metadata.get('tags', []),
                        technologies=metadata.get('technologies', []),
                        created_at=datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat())),
                        updated_at=datetime.fromisoformat(metadata.get('updated_at', datetime.now().isoformat())),
                        source=metadata.get('source', 'unknown'),
                        relevance_score=metadata.get('relevance_score', 0.0),
                        usage_count=metadata.get('usage_count', 0)
                    )
        except Exception as e:
            logging.error(f"Error parsing context file {file_path}: {e}")
        
        return None
    
    def _save_context_file(self, context_item: ContextItem) -> None:
        """Save a context item to file."""
        file_path = self._get_context_file_path(context_item)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create frontmatter
        metadata = {
            'title': context_item.title,
            'category': context_item.category,
            'subcategory': context_item.subcategory,
            'tags': context_item.tags,
            'technologies': context_item.technologies,
            'created_at': context_item.created_at.isoformat(),
            'updated_at': context_item.updated_at.isoformat(),
            'source': context_item.source,
            'relevance_score': context_item.relevance_score,
            'usage_count': context_item.usage_count
        }
        
        frontmatter = "---\n"
        for key, value in metadata.items():
            if isinstance(value, list):
                frontmatter += f"{key}: {json.dumps(value)}\n"
            elif isinstance(value, str):
                frontmatter += f"{key}: \"{value}\"\n"
            else:
                frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter + context_item.content)
    
    def add_context(self, title: str, content: str, category: str, 
                   subcategory: str, source: str, 
                   tags: Optional[List[str]] = None,
                   technologies: Optional[List[str]] = None) -> str:
        """Add a new context item to the store."""
        context_id = self._generate_context_id(title, content)
        
        # Check if context already exists
        if context_id in self.contexts:
            logging.info(f"Context already exists: {context_id}")
            return context_id
        
        # Validate category and subcategory
        if category not in self.categories:
            raise ValueError(f"Invalid category: {category}")
        if subcategory not in self.categories[category]:
            raise ValueError(f"Invalid subcategory: {subcategory} for category: {category}")
        
        # Create context item
        context_item = ContextItem(
            id=context_id,
            title=title,
            content=content,
            category=category,
            subcategory=subcategory,
            tags=tags or [],
            technologies=technologies or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source=source
        )
        
        # Add to memory and save to file
        self.contexts[context_id] = context_item
        self._save_context_file(context_item)
        
        logging.info(f"Added context: {context_id} - {title}")
        return context_id
    
    def update_context(self, context_id: str, **updates) -> bool:
        """Update an existing context item."""
        if context_id not in self.contexts:
            return False
        
        context_item = self.contexts[context_id]
        
        # Update allowed fields
        allowed_updates = {'title', 'content', 'tags', 'technologies', 'relevance_score'}
        for key, value in updates.items():
            if key in allowed_updates:
                setattr(context_item, key, value)
        
        context_item.updated_at = datetime.now()
        
        # Save to file
        self._save_context_file(context_item)
        
        logging.info(f"Updated context: {context_id}")
        return True
    
    def get_context(self, context_id: str) -> Optional[ContextItem]:
        """Get a context item by ID."""
        return self.contexts.get(context_id)
    
    def search_contexts(self, query: str, technologies: Optional[List[str]] = None,
                       category: Optional[str] = None,
                       subcategory: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       limit: int = 10) -> List[ContextItem]:
        """Search for contexts matching criteria."""
        results = []
        query_lower = query.lower() if query else ""
        
        for context_item in self.contexts.values():
            score = 0.0
            
            # Text matching
            if query_lower:
                if query_lower in context_item.title.lower():
                    score += 3.0
                if query_lower in context_item.content.lower():
                    score += 1.0
                if any(query_lower in tag.lower() for tag in context_item.tags):
                    score += 2.0
            
            # Technology matching
            if technologies:
                tech_matches = len(set(technologies) & set(context_item.technologies))
                score += tech_matches * 2.0
            
            # Category filtering
            if category and context_item.category != category:
                continue
            if subcategory and context_item.subcategory != subcategory:
                continue
            
            # Tag matching
            if tags:
                tag_matches = len(set(tags) & set(context_item.tags))
                score += tag_matches * 1.5
            
            if score > 0:
                context_item.relevance_score = score
                results.append(context_item)
        
        # Sort by relevance score and usage count
        results.sort(key=lambda x: (x.relevance_score, x.usage_count), reverse=True)
        
        return results[:limit]
    
    def get_contexts_by_technology(self, technology: str, limit: int = 10) -> List[ContextItem]:
        """Get contexts related to a specific technology."""
        return self.search_contexts("", technologies=[technology], limit=limit)
    
    def get_contexts_by_category(self, category: str, 
                                subcategory: Optional[str] = None) -> List[ContextItem]:
        """Get all contexts in a category/subcategory."""
        results = []
        
        for context_item in self.contexts.values():
            if context_item.category == category:
                if subcategory is None or context_item.subcategory == subcategory:
                    results.append(context_item)
        
        return sorted(results, key=lambda x: x.updated_at, reverse=True)
    
    def increment_usage(self, context_id: str) -> None:
        """Increment usage count for a context item."""
        if context_id in self.contexts:
            self.contexts[context_id].usage_count += 1
            self._save_context_file(self.contexts[context_id])
    
    def get_popular_contexts(self, limit: int = 10) -> List[ContextItem]:
        """Get most frequently used contexts."""
        sorted_contexts = sorted(
            self.contexts.values(), 
            key=lambda x: x.usage_count, 
            reverse=True
        )
        return sorted_contexts[:limit]
    
    def get_recent_contexts(self, limit: int = 10) -> List[ContextItem]:
        """Get most recently updated contexts."""
        sorted_contexts = sorted(
            self.contexts.values(),
            key=lambda x: x.updated_at,
            reverse=True
        )
        return sorted_contexts[:limit]
    
    def remove_context(self, context_id: str) -> bool:
        """Remove a context item from the store."""
        if context_id not in self.contexts:
            return False
        
        context_item = self.contexts[context_id]
        file_path = self._get_context_file_path(context_item)
        
        # Remove file
        if file_path.exists():
            file_path.unlink()
        
        # Remove from memory
        del self.contexts[context_id]
        
        logging.info(f"Removed context: {context_id}")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the context store."""
        stats = {
            'total_contexts': len(self.contexts),
            'categories': {},
            'technologies': {},
            'recent_activity': len([c for c in self.contexts.values() 
                                  if (datetime.now() - c.updated_at).days < 7])
        }
        
        # Category statistics
        for context_item in self.contexts.values():
            category = context_item.category
            subcategory = context_item.subcategory
            
            if category not in stats['categories']:
                stats['categories'][category] = {}
            if subcategory not in stats['categories'][category]:
                stats['categories'][category][subcategory] = 0
            stats['categories'][category][subcategory] += 1
        
        # Technology statistics
        for context_item in self.contexts.values():
            for tech in context_item.technologies:
                stats['technologies'][tech] = stats['technologies'].get(tech, 0) + 1
        
        return stats