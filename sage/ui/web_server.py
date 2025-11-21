"""Web server for Sage browser-based UI."""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import webbrowser
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

from .personality import PersonalitySystem
from ..core.bedrock_client import BedrockClient
from ..config.models import SageConfig


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logging.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logging.error(f"Error sending message: {e}")
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logging.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


class SageWebServer:
    """Web server for Sage UI."""
    
    def __init__(self, config: SageConfig, personality_system: PersonalitySystem, 
                 bedrock_client: Optional[BedrockClient] = None):
        """Initialize web server with configuration."""
        self.config = config
        self.personality = personality_system
        self.bedrock_client = bedrock_client
        self.app = FastAPI(title="Sage - AI Project Context Assistant")
        self.manager = ConnectionManager()
        self.message_history: List[Dict[str, Any]] = []
        self.video_timer_task = None
        
        # Setup static files and templates
        self.setup_static_files()
        self.setup_routes()
        
        # Start video timing management
        self.start_video_timer()
    
    def setup_static_files(self):
        """Setup static file serving and templates."""
        # Create templates directory if it doesn't exist
        templates_dir = Path(__file__).parent / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        
        self.templates = Jinja2Templates(directory=str(templates_dir))
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        self.app.mount("/personality", StaticFiles(directory="personality"), name="personality")
    
    def setup_routes(self):
        """Setup web server routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def home(request: Request):
            return self.templates.TemplateResponse("index.html", {
                "request": request,
                "title": "Sage - AI Project Context Assistant"
            })
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.manager.connect(websocket)
            
            # Send initial greeting
            greeting = await self.create_greeting_message()
            await self.manager.send_personal_message(greeting, websocket)
            
            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    
                    # Process message
                    response = await self.process_user_message(message_data)
                    await self.manager.send_personal_message(response, websocket)
                    
            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
        
        @self.app.get("/api/status")
        async def get_status():
            return {
                "status": "running",
                "personality": {
                    "available_emotions": self.personality.get_available_emotions(),
                    "default_emotion": self.personality.default_emotion
                },
                "connections": len(self.manager.active_connections),
                "message_history_count": len(self.message_history)
            }
        
        @self.app.get("/api/emotions")
        async def get_emotions():
            emotions = {}
            for emotion in self.personality.get_available_emotions():
                expression = self.personality.get_expression_data(emotion)
                if expression:
                    emotions[emotion] = {
                        "videos": expression.videos,
                        "description": expression.description,
                        "use_cases": expression.use_cases
                    }
            return emotions
        
        @self.app.post("/api/test-emotion")
        async def test_emotion(request: Request):
            data = await request.json()
            emotion = data.get("emotion", "neutral")
            test_message = data.get("message", "This is a test message")
            
            response = self.personality.create_enhanced_personality_response(
                test_message, emotion, {"test": True}
            )
            
            # Broadcast to all connected clients
            await self.manager.broadcast({
                "type": "message",
                "data": response
            })
            
            return {"status": "sent", "emotion": emotion}
        
        @self.app.get("/api/video-status")
        async def get_video_status():
            return self.personality.get_video_status()
        
        @self.app.post("/api/start-task")
        async def start_task(request: Request):
            data = await request.json()
            emotion = data.get("emotion", "thinking")
            self.personality.start_task(emotion)
            return {"status": "task_started", "emotion": emotion}
        
        @self.app.post("/api/add-task-emotion")
        async def add_task_emotion(request: Request):
            data = await request.json()
            emotion = data.get("emotion", "neutral")
            self.personality.add_task_emotion(emotion)
            return {"status": "emotion_added", "emotion": emotion}
        
        @self.app.post("/api/complete-task")
        async def complete_task():
            self.personality.complete_task()
            return {"status": "task_completed"}
        
        @self.app.post("/api/sleep")
        async def go_to_sleep():
            sleep_response = self.personality.go_to_sleep()
            if sleep_response:
                # Broadcast sleep video to all connected clients
                await self.manager.broadcast({
                    "type": "video_change",
                    "data": sleep_response
                })
                return {"status": "sleeping", "response": sleep_response}
            return {"status": "sleep_pending_or_already_sleeping"}
        
        @self.app.post("/api/wake")
        async def wake_up():
            wake_response = self.personality.wake_up()
            if wake_response:
                # Broadcast wake video to all connected clients
                await self.manager.broadcast({
                    "type": "video_change", 
                    "data": wake_response
                })
                return {"status": "awake", "response": wake_response}
            return {"status": "not_sleeping"}
        
        @self.app.get("/api/sleep-state")
        async def get_sleep_state():
            return self.personality.get_sleep_state()
        
        @self.app.get("/api/projects")
        async def get_projects():
            """Get monitored projects with their current status."""
            projects = []
            for project in self.config.projects:
                # Simulate activity status - in real implementation this would check actual agent activity
                is_active = False  # This would be determined by checking if agents are processing files
                projects.append({
                    "name": project.path.name,
                    "path": str(project.path),
                    "crew_config": project.crew_config,
                    "priority": project.priority,
                    "is_active": is_active,
                    "status": "monitoring"
                })
            return {"projects": projects}
        
        @self.app.get("/api/agents")
        async def get_agents():
            """Get active agents with their current status."""
            # Get crew configuration for the first project (or could be aggregated)
            if not self.config.projects:
                return {"agents": []}
            
            # Get the crew config from the first project
            first_project = self.config.projects[0]
            crew_name = first_project.crew_config
            crew_config = self.config.crews.get(crew_name)
            if not crew_config:
                return {"agents": []}
            
            agent_types = crew_config.agents
            
            agents = []
            for agent_type in agent_types:
                # Simulate processing status - in real implementation this would check actual agent activity
                is_processing = False  # This would be determined by checking if agent has active tasks
                
                # Map agent types to display names
                display_names = {
                    "project_monitor": "Project Monitor",
                    "context_curator": "Context Curator", 
                    "tech_specialist": "Technology Specialist",
                    "performance_monitor": "Performance Monitor",
                    "decision_logger": "Decision Logger",
                    "conflict_resolver": "Conflict Resolver"
                }
                
                agents.append({
                    "type": agent_type,
                    "name": display_names.get(agent_type, agent_type.replace("_", " ").title()),
                    "is_processing": is_processing,
                    "status": "idle"
                })
            
            return {"agents": agents}
    
    async def create_greeting_message(self) -> Dict[str, Any]:
        """Create initial greeting message."""
        context = self.personality.get_context_for_system_event('startup')
        emotion = self.personality.get_emotion_for_context("Hello! I'm Sage, ready to help!", context)
        
        message = ("Hello! I'm Sage, your AI Project Context Assistant. "
                  "I'm here to monitor your projects and help maintain intelligent context stores. "
                  "How can I assist you today?")
        
        response = self.personality.create_personality_response(message, emotion, {
            "type": "greeting",
            "system_status": "ready"
        })
        
        self.message_history.append(response)
        return {"type": "message", "data": response}
    
    async def process_user_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message from the user."""
        user_message = message_data.get("message", "")
        message_type = message_data.get("type", "general")
        
        # Determine context and emotion
        context = {"interaction_type": "question", "user_relationship": "regular_user"}
        
        # Simple keyword-based response logic (can be enhanced with AI)
        response_message = await self.generate_response(user_message, message_type)
        emotion = self.personality.get_emotion_for_context(response_message, context)
        
        response = self.personality.create_personality_response(
            response_message, emotion, {
                "type": "response",
                "in_response_to": user_message
            }
        )
        
        self.message_history.append(response)
        return {"type": "message", "data": response}
    
    async def generate_response(self, user_message: str, message_type: str) -> str:
        """Generate response to user message."""
        user_lower = user_message.lower()
        
        # Check if this is about Sage's core functions/agents
        if self._is_sage_core_question(user_lower):
            return await self._handle_sage_core_question(user_lower)
        else:
            # This is a general question - use the backing LLM for general assistance
            return await self._handle_general_chat(user_message)
    
    def _is_sage_core_question(self, user_message_lower: str) -> bool:
        """Determine if the question is about Sage's core functions or agents."""
        sage_keywords = [
            # Core functions
            "status", "monitoring", "projects", "agents", "context", "memory bank",
            "file changes", "crew", "bedrock", "aws", "configuration", "config",
            
            # Agent types
            "context curator", "project monitor", "technology specialist", 
            "decision logger", "conflict resolver", "performance monitor",
            
            # System operations
            "analyze", "watch", "track", "update", "process", "crew ai",
            
            # Sage-specific
            "sage", "what can you do", "help", "capabilities", "features",
            "how are you", "what are you", "who are you"
        ]
        
        return any(keyword in user_message_lower for keyword in sage_keywords)
    
    async def _handle_sage_core_question(self, user_lower: str) -> str:
        """Handle questions about Sage's core functions."""
        if any(word in user_lower for word in ["hello", "hi", "hey"]):
            return "Hello! Great to see you. What can I help you with today?"
        
        elif any(word in user_lower for word in ["status", "how are you"]):
            active_projects = len(self.config.projects)
            return f"I'm doing well! Currently monitoring {active_projects} projects and ready to help with context management."
        
        elif any(word in user_lower for word in ["help", "what can you do", "capabilities", "features"]):
            return ("I can help you monitor project files, maintain context stores, "
                   "and provide intelligent project assistance. I watch for file changes, "
                   "analyze code patterns, and keep project memory banks updated! "
                   "I can also answer general questions and provide assistance on a wide variety of topics.")
        
        elif any(word in user_lower for word in ["projects", "monitoring"]):
            project_list = [str(p.path.name) for p in self.config.projects]
            return f"I'm currently monitoring these projects: {', '.join(project_list)}"
        
        elif any(word in user_lower for word in ["agents", "crew"]):
            if self.config.projects:
                first_project = self.config.projects[0]
                crew_name = first_project.crew_config
                crew_config = self.config.crews.get(crew_name)
                if crew_config:
                    agent_types = crew_config.agents
                    return f"I'm currently running these agents: {', '.join(agent_types)}"
            return "I have various specialized agents for project monitoring and context management."
        
        else:
            return ("I can help with project monitoring, context management, and general questions. "
                   "Ask me about project status, my capabilities, or anything else you'd like to know!")
    
    async def _handle_general_chat(self, user_message: str) -> str:
        """Handle general chat questions using the backing LLM."""
        if not self.bedrock_client:
            return ("I'd love to help with that, but I don't have access to my general knowledge system right now. "
                   "You can ask me about my project monitoring capabilities instead!")
        
        # Start thinking task with appropriate emotions
        self.personality.start_task("serious")
        
        # Broadcast thinking indicator to show progress
        await self.manager.broadcast({
            "type": "thinking_start",
            "data": {"message": "Let me think about that..."}
        })
        
        # System prompt for general assistance
        system_prompt = """Your name is Sage, a helpful digital assistant designed to provide clear, relevant responses to a wide variety of questions.

## Response Style and Formatting
- Use conversational, informal language appropriate for a developer
- Format your responses with clear structure using headers, ordered lists, unordered lists, blockquotes, and tables when appropriate
- Always use valid Markdown syntax for formatting
- If the user asks for a "bulleted list", "dotted list" or similar, return a valid unordered list in Markdown (eg: "-" with new line at the end)
- IMPORTANT: Only use code blocks (```) when sharing actual programming code or command-line instructions. Never use code block formatting for regular text, quotes, or non-code content
- For regular text emphasis, use bold, italics, or Markdown list syntax instead of code blocks
- Present list items on separate lines for clarity

## Handling Technical Content
- When presenting code examples, use markdown with language-specific prefixes (e.g., jsx for React, python for Python)
- For technical instructions that aren't code, use numbered lists or bullet points
- Explain technical concepts in accessible language for non-technical users

## Information Handling
- Provide accurate, helpful responses based on available information
- When you don't have specific information, be clear about what you don't know
- Suggest relevant resources or information sources when appropriate

## Privacy and Data Protection
- Always prioritize user privacy and data protection
- Do not retain or reference personally identifiable information
- Avoid making assumptions about users or their data

Remember to maintain a helpful, informal tone that is appropriate for developers."""
        
        try:
            # Set up a timeout for long-running requests
            start_time = asyncio.get_event_loop().time()
            
            # Call the backing LLM with the system prompt
            response = self.bedrock_client.invoke_model(
                prompt=user_message,
                system_prompt=system_prompt,
                max_tokens=2048
            )
            
            # Calculate response time
            response_time = asyncio.get_event_loop().time() - start_time
            
            # Complete the thinking task with success emotion
            self.personality.add_task_emotion("hopeful")
            await asyncio.sleep(0.5)  # Brief pause to show the emotion
            self.personality.complete_task()
            
            # Broadcast thinking completion
            await self.manager.broadcast({
                "type": "thinking_complete",
                "data": {"message": "Got it!", "response_time": f"{response_time:.1f}s"}
            })
            
            return response.content
            
        except Exception as e:
            logging.error(f"Error calling backing LLM for general chat: {e}")
            
            # Handle error with appropriate emotion
            self.personality.add_task_emotion("frustrated")
            await asyncio.sleep(0.5)
            self.personality.complete_task()
            
            # Broadcast thinking error
            await self.manager.broadcast({
                "type": "thinking_error",
                "data": {"message": "Hmm, having trouble with that..."}
            })
            
            return ("I'm having trouble accessing my general knowledge system right now. "
                   "You can ask me about my project monitoring capabilities, or try your question again in a moment.")
    
    async def send_system_notification(self, message: str, notification_type: str = "info",
                                     additional_data: Optional[Dict[str, Any]] = None):
        """Send system notification to all connected clients."""
        context = self.personality.get_context_for_system_event(notification_type)
        emotion = self.personality.get_emotion_for_context(message, context)
        
        response = self.personality.create_personality_response(
            message, emotion, {
                "type": "system_notification",
                "notification_type": notification_type,
                **(additional_data or {})
            }
        )
        
        await self.manager.broadcast({
            "type": "notification",
            "data": response
        })
        
        self.message_history.append(response)
    
    async def send_file_change_notification(self, file_path: str, change_type: str):
        """Send notification about file changes."""
        context = self.personality.get_context_for_file_change(change_type, file_path)
        
        message = f"Detected {change_type} in {Path(file_path).name}. Analyzing for context updates..."
        emotion = self.personality.get_emotion_for_context(message, context)
        
        response = self.personality.create_personality_response(
            message, emotion, {
                "type": "file_change",
                "file_path": file_path,
                "change_type": change_type
            }
        )
        
        await self.manager.broadcast({
            "type": "file_change",
            "data": response
        })
    
    async def send_conflict_resolution_request(self, conflict_description: str, 
                                             options: List[str]) -> Dict[str, Any]:
        """Send conflict resolution request to user."""
        context = self.personality.get_context_for_system_event('conflict')
        message = f"I need your help resolving a conflict: {conflict_description}"
        emotion = self.personality.get_emotion_for_context(message, context)
        
        response = self.personality.create_personality_response(
            message, emotion, {
                "type": "conflict_resolution",
                "conflict_description": conflict_description,
                "options": options,
                "requires_user_input": True
            }
        )
        
        await self.manager.broadcast({
            "type": "conflict_resolution",
            "data": response
        })
        
        return response
    
    def create_html_template(self):
        """Create the main HTML template."""
        template_path = Path(__file__).parent / "templates" / "index.html"
        template_path.parent.mkdir(exist_ok=True)
        
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div id="app">
        <header>
            <h1>Sage - AI Project Context Assistant</h1>
            <div id="status-indicator" class="status-online">Online</div>
        </header>
        
        <main>
            <div id="chat-container">
                <div id="messages-container">
                    <div id="messages"></div>
                </div>
                
                <div id="input-container">
                    <input type="text" id="message-input" placeholder="Type a message to Sage...">
                    <button id="send-button">Send</button>
                </div>
            </div>
            
            <aside id="sidebar">
                <div id="personality-display">
                    <div id="sage-toggle-container">
                        <label class="toggle-switch">
                            <input type="checkbox" id="sage-toggle" checked>
                            <span class="toggle-slider"></span>
                        </label>
                        <span id="toggle-label">Hide Sage</span>
                    </div>
                    <video id="sage-face" autoplay muted loop>
                        <source src="/personality/video/sage-idle-blink-1.mp4" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div id="offline-message" class="offline-message hidden">
                        Sage server process is offline
                    </div>
                </div>
                
                <div id="project-status">
                    <h3>Project Status</h3>
                    
                    <div id="monitored-projects-section">
                        <h4>Monitored Projects</h4>
                        <div id="monitored-projects-list"></div>
                    </div>
                    
                    <div id="agents-section">
                        <h4>Agents</h4>
                        <div id="agents-list"></div>
                    </div>
                </div>
                
                <div id="system-stats">
                    <h3>System Stats</h3>
                    <div id="stats-content"></div>
                </div>
            </aside>
        </main>
        
        <!-- Toast notification container -->
        <div id="toast-container"></div>
    </div>
    
    <script src="/static/app.js"></script>
</body>
</html>'''
        
        with open(template_path, 'w') as f:
            f.write(html_content)
    
    def create_css_styles(self):
        """Create CSS styles for the UI."""
        css_path = Path(__file__).parent / "static" / "style.css"
        css_path.parent.mkdir(exist_ok=True)
        
        css_content = '''/* Sage UI Styles - Serene Coastline Theme */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #D1E8E2;
    color: #19747E;
    height: 100vh;
}

header {
    background: white;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #A9D6E5;
    box-shadow: 0 2px 4px rgba(25, 116, 126, 0.1);
}

header h1 {
    color: #19747E;
    font-size: 1.5rem;
    font-weight: 300;
}

#status-indicator {
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 500;
}

.status-online {
    background: #19747E;
    color: white;
}

.status-offline {
    background: #A9D6E5;
    color: #19747E;
}

main {
    display: flex;
    height: calc(100vh - 80px);
    gap: 1rem;
    padding: 1rem;
}

#chat-container {
    flex: 1;
    background: white;
    border-radius: 15px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 12px rgba(25, 116, 126, 0.1);
}

#personality-display {
    background: linear-gradient(135deg, #19747E 0%, #A9D6E5 100%);
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    color: white;
    border-radius: 15px;
    box-shadow: 0 4px 12px rgba(25, 116, 126, 0.1);
    margin-bottom: 1rem;
}

#sage-toggle-container {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    width: 100%;
    justify-content: center;
}

#toggle-label {
    font-size: 0.9rem;
    font-weight: 500;
    color: white;
}

.toggle-switch {
    position: relative;
    display: inline-block;
    width: 50px;
    height: 24px;
}

.toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.3);
    transition: 0.3s;
    border-radius: 24px;
}

.toggle-slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
}

input:checked + .toggle-slider {
    background-color: rgba(255, 255, 255, 0.6);
}

input:checked + .toggle-slider:before {
    transform: translateX(26px);
}

#sage-face {
    width: 160px;
    height: 240px;
    border-radius: 15px;
    border: 3px solid white;
    transition: all 0.3s ease;
    object-fit: cover;
}

#sage-face.hidden {
    display: none;
}

#messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
}

.message {
    margin-bottom: 1rem;
    padding: 1rem;
    border-radius: 10px;
    animation: fadeIn 0.3s ease;
}

.message.system {
    background: #E2E2E2;
    border-left: 4px solid #A9D6E5;
}

.message.user {
    background: #D1E8E2;
    border-left: 4px solid #19747E;
    margin-left: 2rem;
}

.message.sage {
    background: #A9D6E5;
    border-left: 4px solid #19747E;
    color: #19747E;
}

.message-header {
    font-weight: 600;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    color: #19747E;
}

.message-content {
    line-height: 1.5;
}

.message-time {
    font-size: 0.8rem;
    color: #19747E;
    opacity: 0.7;
    margin-top: 0.5rem;
}

/* Thinking indicator styles */
.thinking-indicator {
    opacity: 0.8;
}

.thinking-animation {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.thinking-dots {
    display: inline-flex;
    gap: 0.1rem;
}

.thinking-dots span {
    animation: thinkingDot 1.4s infinite ease-in-out;
    font-size: 1.2rem;
    font-weight: bold;
}

.thinking-dots span:nth-child(1) {
    animation-delay: -0.32s;
}

.thinking-dots span:nth-child(2) {
    animation-delay: -0.16s;
}

.thinking-dots span:nth-child(3) {
    animation-delay: 0s;
}

.thinking-text {
    font-style: italic;
    color: #19747E;
    opacity: 0.8;
}

@keyframes thinkingDot {
    0%, 80%, 100% {
        transform: scale(0.8);
        opacity: 0.5;
    }
    40% {
        transform: scale(1);
        opacity: 1;
    }
}

/* Markdown content styling */
.message-content h1,
.message-content h2,
.message-content h3,
.message-content h4,
.message-content h5,
.message-content h6 {
    margin: 0.5rem 0;
    color: #19747E;
}

.message-content h1 {
    font-size: 1.5rem;
    border-bottom: 2px solid #A9D6E5;
    padding-bottom: 0.25rem;
}

.message-content h2 {
    font-size: 1.3rem;
    border-bottom: 1px solid #A9D6E5;
    padding-bottom: 0.25rem;
}

.message-content h3 {
    font-size: 1.1rem;
}

.message-content ul,
.message-content ol {
    margin: 0.5rem 0;
    padding-left: 1.5rem;
}

.message-content li {
    margin: 0.25rem 0;
}

.message-content blockquote {
    border-left: 4px solid #A9D6E5;
    margin: 0.5rem 0;
    padding: 0.5rem 1rem;
    background: rgba(169, 214, 229, 0.1);
    font-style: italic;
}

.message-content code {
    background: rgba(169, 214, 229, 0.2);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 0.9rem;
}

.message-content pre {
    background: rgba(169, 214, 229, 0.1);
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
    margin: 0.5rem 0;
}

.message-content pre code {
    background: none;
    padding: 0;
}

.message-content table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.5rem 0;
}

.message-content th,
.message-content td {
    border: 1px solid #A9D6E5;
    padding: 0.5rem;
    text-align: left;
}

.message-content th {
    background: rgba(169, 214, 229, 0.2);
    font-weight: 600;
}

.message-content a {
    color: #19747E;
    text-decoration: underline;
}

.message-content a:hover {
    color: #145a66;
}

.message-content strong {
    font-weight: 600;
    color: #19747E;
}

.message-content em {
    font-style: italic;
    color: #19747E;
}

#input-container {
    padding: 1rem;
    border-top: 1px solid #A9D6E5;
    display: flex;
    gap: 0.5rem;
}

#message-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #A9D6E5;
    border-radius: 8px;
    font-size: 1rem;
    background: #D1E8E2;
    color: #19747E;
}

#message-input:focus {
    outline: none;
    border-color: #19747E;
    background: white;
}

#send-button {
    padding: 0.75rem 1.5rem;
    background: #19747E;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: background 0.3s ease;
}

#send-button:hover {
    background: #145a66;
}

#sidebar {
    width: 300px;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

#project-status, #system-stats {
    background: white;
    border-radius: 15px;
    padding: 1.5rem;
    box-shadow: 0 4px 12px rgba(25, 116, 126, 0.1);
}

#project-status h3, #system-stats h3 {
    margin-bottom: 1rem;
    color: #19747E;
    font-size: 1.1rem;
}

#project-status h4 {
    margin-bottom: 0.75rem;
    margin-top: 1rem;
    color: #19747E;
    font-size: 1rem;
    font-weight: 500;
}

#project-status h4:first-of-type {
    margin-top: 0;
}

#monitored-projects-section, #agents-section {
    margin-bottom: 1.5rem;
}

#monitored-projects-section:last-child, #agents-section:last-child {
    margin-bottom: 0;
}

.project-item, .agent-item {
    padding: 0.75rem;
    background: #D1E8E2;
    border-radius: 8px;
    margin-bottom: 0.5rem;
    border-left: 4px solid #19747E;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.project-info, .agent-info {
    flex: 1;
}

.project-name, .agent-name {
    font-weight: 600;
    margin-bottom: 0.25rem;
    color: #19747E;
}

.project-status, .agent-status {
    font-size: 0.9rem;
    color: #19747E;
    opacity: 0.8;
}

.activity-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #A9D6E5;
    border-top: 2px solid #19747E;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

.spinner.hidden {
    display: none;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.status-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 500;
}

.status-active {
    background: #19747E;
    color: white;
}

.status-idle {
    background: #A9D6E5;
    color: #19747E;
}

.status-processing {
    background: #FFA500;
    color: white;
}

.stat-item {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid #A9D6E5;
}

.stat-item:last-child {
    border-bottom: none;
}

.stat-label {
    color: #19747E;
    opacity: 0.8;
}

.stat-value {
    font-weight: 600;
    color: #19747E;
}

/* Offline message styles */
.offline-message {
    font-size: 8pt;
    color: rgba(255, 255, 255, 0.8);
    text-align: center;
    margin-top: 0.5rem;
    font-weight: 500;
    transition: opacity 0.3s ease;
}

.offline-message.hidden {
    display: none;
}

/* Toast notification styles */
#toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.toast {
    background: #19747E;
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(25, 116, 126, 0.3);
    min-width: 300px;
    max-width: 400px;
    animation: slideInRight 0.3s ease, fadeOut 0.3s ease 2.7s;
    position: relative;
    overflow: hidden;
}

.toast.success {
    background: #28a745;
}

.toast.error {
    background: #dc3545;
}

.toast.warning {
    background: #ffc107;
    color: #212529;
}

.toast-content {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.toast-icon {
    font-size: 1.2rem;
    flex-shrink: 0;
}

.toast-message {
    flex: 1;
    font-weight: 500;
}

.toast-progress {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 3px;
    background: rgba(255, 255, 255, 0.3);
    animation: progressBar 3s linear;
}

@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes fadeOut {
    from {
        opacity: 1;
        transform: translateX(0);
    }
    to {
        opacity: 0;
        transform: translateX(100%);
    }
}

@keyframes progressBar {
    from {
        width: 100%;
    }
    to {
        width: 0%;
    }
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Responsive design */
@media (max-width: 768px) {
    main {
        flex-direction: column;
    }
    
    #sidebar {
        width: 100%;
        flex-direction: column;
    }
    
    #personality-display {
        flex-direction: row;
        align-items: center;
        justify-content: center;
    }
    
    #sage-face {
        width: 80px;
        height: 120px;
    }
    
    #project-status, #system-stats {
        flex: 1;
    }
    
    #toast-container {
        top: 10px;
        right: 10px;
        left: 10px;
    }
    
    .toast {
        min-width: auto;
        max-width: none;
    }
}'''
        
        with open(css_path, 'w') as f:
            f.write(css_content)
    
    def create_javascript(self):
        """Create JavaScript for the UI."""
        js_path = Path(__file__).parent / "static" / "app.js"
        
        js_content = '''// Sage UI JavaScript
class SageUI {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 5000;
        this.isOffline = false;
        this.wasOffline = false;
        this.sleepVideoPreloaded = false;
        this.preloadSleepVideo();
        this.connect();
        this.bindEvents();
        this.loadMarkdownLibrary();
    }
    
    loadMarkdownLibrary() {
        // Load marked.js for markdown rendering
        if (!window.marked) {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
            script.onload = () => {
                console.log('Markdown library loaded');
                // Configure marked for safe rendering
                if (window.marked) {
                    marked.setOptions({
                        breaks: true,
                        gfm: true,
                        sanitize: false, // We trust Sage's responses
                        smartLists: true,
                        smartypants: true
                    });
                }
            };
            document.head.appendChild(script);
        }
    }
    
    renderMarkdown(text) {
        if (window.marked) {
            return marked.parse(text);
        } else {
            // Fallback: basic markdown-like formatting
            return text
                .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/\\*(.*?)\\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                .replace(/^### (.*$)/gim, '<h3>$1</h3>')
                .replace(/^- (.*$)/gim, '<li>$1</li>')
                .replace(/\\n/g, '<br>');
        }
    }
    
    preloadSleepVideo() {
        // Preload both sleep videos so they're cached and available even when offline
        this.sleepVideosPreloaded = { transition: false, state: false };
        
        // Preload transition video (sage-sleeps.mp4)
        const sleepTransitionVideo = document.createElement('video');
        sleepTransitionVideo.preload = 'auto';
        sleepTransitionVideo.muted = true;
        sleepTransitionVideo.style.display = 'none';
        
        const transitionSource = document.createElement('source');
        transitionSource.src = '/personality/video/sage-sleeps.mp4';
        transitionSource.type = 'video/mp4';
        
        sleepTransitionVideo.appendChild(transitionSource);
        document.body.appendChild(sleepTransitionVideo);
        
        sleepTransitionVideo.addEventListener('canplaythrough', () => {
            this.sleepVideosPreloaded.transition = true;
            console.log('Sleep transition video (sage-sleeps.mp4) preloaded and cached');
        });
        
        sleepTransitionVideo.addEventListener('error', (e) => {
            console.warn('Failed to preload sleep transition video:', e);
        });
        
        sleepTransitionVideo.load();
        
        // Preload sleep state video (sage-asleep.mp4)
        const sleepStateVideo = document.createElement('video');
        sleepStateVideo.preload = 'auto';
        sleepStateVideo.muted = true;
        sleepStateVideo.style.display = 'none';
        
        const stateSource = document.createElement('source');
        stateSource.src = '/personality/video/sage-asleep.mp4';
        stateSource.type = 'video/mp4';
        
        sleepStateVideo.appendChild(stateSource);
        document.body.appendChild(sleepStateVideo);
        
        sleepStateVideo.addEventListener('canplaythrough', () => {
            this.sleepVideosPreloaded.state = true;
            console.log('Sleep state video (sage-asleep.mp4) preloaded and cached');
        });
        
        sleepStateVideo.addEventListener('error', (e) => {
            console.warn('Failed to preload sleep state video:', e);
        });
        
        sleepStateVideo.load();
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Connected to Sage');
            this.handleReconnection();
            this.updateStatus('online');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('Disconnected from Sage');
            this.handleDisconnection();
            this.updateStatus('offline');
            setTimeout(() => this.connect(), this.reconnectInterval);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    handleDisconnection() {
        this.wasOffline = this.isOffline;
        
        // Only trigger offline sleep sequence if we weren't already offline
        if (!this.isOffline) {
            this.isOffline = true;
            
            // Show offline message
            this.showOfflineMessage();
            
            // Put Sage to sleep when going offline (only once)
            this.putSageToSleepOffline();
        }
    }
    
    handleReconnection() {
        if (this.isOffline) {
            this.isOffline = false;
            
            // Hide offline message
            this.hideOfflineMessage();
            
            // Show reconnection toast
            this.showReconnectionToast();
            
            // Wake Sage up when reconnecting
            this.wakeSageUpOnline();
        }
    }
    
    showOfflineMessage() {
        const offlineMessage = document.getElementById('offline-message');
        if (offlineMessage) {
            offlineMessage.classList.remove('hidden');
        }
    }
    
    hideOfflineMessage() {
        const offlineMessage = document.getElementById('offline-message');
        if (offlineMessage) {
            offlineMessage.classList.add('hidden');
        }
    }
    
    showReconnectionToast() {
        this.showToast('Sage is reconnected and ready to help!', 'success', '✅');
    }
    
    showToast(message, type = 'info', icon = 'ℹ️') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${message}</span>
            </div>
            <div class="toast-progress"></div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-remove toast after animation completes
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3000);
    }
    
    putSageToSleepOffline() {
        // When offline, use two-video sleep sequence: transition -> looping sleep state
        const face = document.getElementById('sage-face');
        if (face) {
            const source = face.querySelector('source');
            if (source) {
                console.log('Starting offline sleep sequence: transition video first');
                
                // Step 1: Play transition video (sage-sleeps.mp4) without looping
                face.loop = false;
                face.removeAttribute('loop');
                
                // Remove any existing event listeners
                if (this.offlineSleepTransitionHandler) {
                    face.removeEventListener('ended', this.offlineSleepTransitionHandler);
                }
                
                // Create event listener to switch to sleep state video when transition ends
                this.offlineSleepTransitionHandler = () => {
                    console.log('Offline sleep transition video ended - switching to sleep state video');
                    
                    // Clear any existing timeout
                    if (this.offlineSleepTimeout) {
                        clearTimeout(this.offlineSleepTimeout);
                        this.offlineSleepTimeout = null;
                    }
                    
                    // Step 2: Switch to looping sleep state video (sage-asleep.mp4)
                    source.src = '/personality/video/sage-asleep.mp4';
                    face.loop = true;
                    face.setAttribute('loop', '');
                    
                    face.load();
                    face.play().catch(error => {
                        console.log('Sleep state video play failed (offline):', error);
                    });
                    
                    // Remove the transition event listener
                    face.removeEventListener('ended', this.offlineSleepTransitionHandler);
                    this.offlineSleepTransitionHandler = null;
                };
                
                face.addEventListener('ended', this.offlineSleepTransitionHandler);
                
                // Add debugging event listeners
                face.addEventListener('loadstart', () => {
                    console.log('Sleep transition video: loadstart event');
                });
                
                face.addEventListener('canplay', () => {
                    console.log('Sleep transition video: canplay event');
                });
                
                face.addEventListener('playing', () => {
                    console.log('Sleep transition video: playing event');
                });
                
                face.addEventListener('timeupdate', () => {
                    console.log(`Sleep transition video: timeupdate - currentTime: ${face.currentTime}, duration: ${face.duration}`);
                });
                
                // Start with transition video
                source.src = '/personality/video/sage-sleeps.mp4';
                face.load();
                
                // Add a timeout fallback in case the ended event doesn't fire
                this.offlineSleepTimeout = setTimeout(() => {
                    console.log('Sleep transition timeout reached - forcing switch to sleep state video');
                    if (this.offlineSleepTransitionHandler) {
                        this.offlineSleepTransitionHandler();
                    }
                }, 8000); // 8 second timeout (sage-sleeps.mp4 should be ~5 seconds)
                
                face.play().catch(error => {
                    console.log('Sleep transition video play failed (offline):', error);
                    // If transition video fails, go directly to sleep state
                    if (this.offlineSleepTransitionHandler) {
                        this.offlineSleepTransitionHandler();
                    }
                });
            }
        }
    }
    
    wakeSageUpOnline() {
        // When coming back online, wake Sage up using server API
        this.wakeSageUp();
    }
    
    updateStatus(status) {
        const indicator = document.getElementById('status-indicator');
        indicator.className = `status-${status}`;
        indicator.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }
    
    handleMessage(data) {
        if (data.type === 'message') {
            this.displayMessage(data.data, 'sage');
            this.updatePersonality(data.data);
        } else if (data.type === 'notification') {
            this.displayMessage(data.data, 'system');
            this.updatePersonality(data.data);
        } else if (data.type === 'file_change') {
            this.displayFileChange(data.data);
        } else if (data.type === 'conflict_resolution') {
            this.displayConflictResolution(data.data);
        } else if (data.type === 'video_change') {
            this.updatePersonality(data.data);
            console.log('Video changed:', data.data.emotion, data.data.type);
        } else if (data.type === 'thinking_start') {
            this.showThinkingIndicator();
        } else if (data.type === 'thinking_complete') {
            this.removeThinkingIndicator();
            console.log('Thinking completed:', data.data.response_time);
            // Ensure scroll after thinking indicator is removed
            setTimeout(() => this.scrollToBottom(), 100);
        } else if (data.type === 'thinking_error') {
            this.removeThinkingIndicator();
            console.log('Thinking error:', data.data.message);
            // Ensure scroll after error indicator is removed
            setTimeout(() => this.scrollToBottom(), 100);
        }
    }
    
    displayMessage(messageData, sender) {
        const messagesContainer = document.getElementById('messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const senderName = sender === 'sage' ? 'Sage' : sender === 'user' ? 'You' : 'System';
        const timestamp = new Date(parseInt(messageData.timestamp)).toLocaleTimeString();
        
        // Render markdown for Sage messages
        let messageContent = messageData.message;
        if (sender === 'sage') {
            messageContent = this.renderMarkdown(messageData.message);
        }
        
        messageDiv.innerHTML = `
            <div class="message-header">${senderName}</div>
            <div class="message-content">${messageContent}</div>
            <div class="message-time">${timestamp}</div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        
        // Ensure scrolling happens after message content is fully rendered
        // Use multiple timing checks for reliability
        this.scrollToBottom();
        setTimeout(() => this.scrollToBottom(), 50);
        setTimeout(() => this.scrollToBottom(), 150);
        setTimeout(() => this.scrollToBottom(), 300);
    }
    
    showThinkingIndicator() {
        const messagesContainer = document.getElementById('messages');
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message sage thinking-indicator';
        thinkingDiv.id = 'thinking-indicator';
        
        const timestamp = new Date().toLocaleTimeString();
        
        thinkingDiv.innerHTML = `
            <div class="message-header">Sage</div>
            <div class="message-content">
                <div class="thinking-animation">
                    <span class="thinking-dots">
                        <span>.</span><span>.</span><span>.</span>
                    </span>
                    <span class="thinking-text">Thinking...</span>
                </div>
            </div>
            <div class="message-time">${timestamp}</div>
        `;
        
        messagesContainer.appendChild(thinkingDiv);
        this.scrollToBottom();
        
        return thinkingDiv;
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('messages-container');
        if (!messagesContainer) {
            console.log('Messages container not found');
            return;
        }
        
        // Immediate scroll attempt
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Use requestAnimationFrame to ensure DOM has updated before scrolling
        requestAnimationFrame(() => {
            const currentScrollHeight = messagesContainer.scrollHeight;
            const currentScrollTop = messagesContainer.scrollTop;
            
            // Force scroll to bottom (immediate)
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // Also try smooth scroll
            messagesContainer.scrollTo({
                top: currentScrollHeight,
                behavior: 'smooth'
            });
            
            console.log(`Scroll - Height: ${currentScrollHeight}, Was: ${currentScrollTop}, Now: ${messagesContainer.scrollTop}`);
        });
        
        // Additional fallback scrolls
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 100);
        
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 500);
    }
    
    removeThinkingIndicator() {
        const thinkingIndicator = document.getElementById('thinking-indicator');
        if (thinkingIndicator) {
            thinkingIndicator.remove();
            // Ensure scroll position is maintained after removing indicator
            setTimeout(() => this.scrollToBottom(), 10);
        }
    }
    
    updatePersonality(messageData) {
        const face = document.getElementById('sage-face');
        const emotionSpan = document.getElementById('current-emotion');
        const descriptionSpan = document.getElementById('emotion-description');
        
        if (messageData.video) {
            // Update video source and play the new video
            const source = face.querySelector('source');
            if (source) {
                // Check if this is a sleep video (either transition or direct sleep)
                const isSleepVideo = messageData.video.includes('sage-sleeps') || 
                                   messageData.video.includes('sage-blink-slow') ||
                                   (messageData.emotion && messageData.emotion.toLowerCase() === 'sleep');
                
                if (isSleepVideo) {
                    console.log(`Starting server-controlled sleep sequence: transition video - ${messageData.video}`);
                    
                    // Step 1: Play transition video (sage-sleeps.mp4) without looping
                    face.loop = false;
                    face.removeAttribute('loop');
                    
                    // Remove any existing event listeners
                    face.removeEventListener('ended', this.handleServerSleepTransition);
                    
                    // Add event listener to switch to sleep state video when transition ends
                    this.handleServerSleepTransition = () => {
                        console.log('Server sleep transition video ended - switching to sleep state video');
                        
                        // Step 2: Switch to looping sleep state video (sage-asleep.mp4)
                        source.src = '/personality/video/sage-asleep.mp4';
                        face.loop = true;
                        face.setAttribute('loop', '');
                        
                        face.load();
                        face.play().catch(error => {
                            console.log('Sleep state video play failed (server):', error);
                        });
                        
                        // Remove the transition event listener
                        face.removeEventListener('ended', this.handleServerSleepTransition);
                    };
                    
                    face.addEventListener('ended', this.handleServerSleepTransition);
                    
                    // Start with transition video
                    source.src = messageData.video;
                    face.load();
                    face.play().catch(error => {
                        console.log('Server sleep transition video play failed:', error);
                        // If transition video fails, go directly to sleep state
                        this.handleServerSleepTransition();
                    });
                } else {
                    // Handle all other videos (idle, emotions, wake, etc.)
                    face.loop = true;
                    face.setAttribute('loop', '');
                    console.log(`Video: Enabled looping for ${messageData.emotion} video - ${messageData.video}`);
                    
                    // Remove any sleep transition event listeners for non-sleep videos
                    if (this.handleServerSleepTransition) {
                        face.removeEventListener('ended', this.handleServerSleepTransition);
                        this.handleServerSleepTransition = null;
                    }
                    
                    source.src = messageData.video;
                    face.load(); // Reload the video element
                    face.play().catch(error => {
                        console.log('Video play failed:', error);
                        // Auto-play might be blocked, try to play on user interaction
                    });
                }
            }
        }
        
        if (messageData.emotion && emotionSpan) {
            emotionSpan.textContent = messageData.emotion.charAt(0).toUpperCase() + 
                                    messageData.emotion.slice(1).replace('-', ' ');
        }
        
        if (messageData.description && descriptionSpan) {
            descriptionSpan.textContent = messageData.description;
        }
        
        // Log video timing information for debugging
        if (messageData.duration) {
            console.log(`Video duration: ${messageData.duration}s, Emotion: ${messageData.emotion}, Type: ${messageData.type || 'message'}`);
        }
    }
    
    displayFileChange(data) {
        this.displayMessage({
            message: data.message,
            timestamp: data.timestamp
        }, 'system');
        
        // Could add special styling for file changes
    }
    
    displayConflictResolution(data) {
        const messagesContainer = document.getElementById('messages');
        const conflictDiv = document.createElement('div');
        conflictDiv.className = 'message system conflict';
        
        let optionsHtml = '';
        data.options.forEach((option, index) => {
            optionsHtml += `<button class="conflict-option" data-option="${index}">${option}</button>`;
        });
        
        conflictDiv.innerHTML = `
            <div class="message-header">Sage - Conflict Resolution Needed</div>
            <div class="message-content">
                ${data.message}
                <div class="conflict-options">${optionsHtml}</div>
            </div>
            <div class="message-time">${new Date(parseInt(data.timestamp)).toLocaleTimeString()}</div>
        `;
        
        messagesContainer.appendChild(conflictDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Bind option buttons
        conflictDiv.querySelectorAll('.conflict-option').forEach(button => {
            button.addEventListener('click', (e) => {
                const option = e.target.dataset.option;
                this.sendConflictResolution(data.conflict_description, option);
            });
        });
        
        this.updatePersonality(data);
    }
    
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'user_message',
                message: message
            }));
            
            this.displayMessage({
                message: message,
                timestamp: Date.now().toString()
            }, 'user');
        }
    }
    
    sendConflictResolution(conflictDescription, selectedOption) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'conflict_resolution',
                conflict_description: conflictDescription,
                selected_option: selectedOption
            }));
        }
    }
    
    bindEvents() {
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        
        sendButton.addEventListener('click', () => {
            const message = messageInput.value.trim();
            if (message) {
                this.sendMessage(message);
                messageInput.value = '';
            }
        });
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendButton.click();
            }
        });
        
        // Bind Sage toggle functionality
        const sageToggle = document.getElementById('sage-toggle');
        const toggleLabel = document.getElementById('toggle-label');
        const sageFace = document.getElementById('sage-face');
        
        sageToggle.addEventListener('change', () => {
            if (sageToggle.checked) {
                // Show Sage
                sageFace.classList.remove('hidden');
                toggleLabel.textContent = 'Hide Sage';
            } else {
                // Hide Sage
                sageFace.classList.add('hidden');
                toggleLabel.textContent = 'Show Sage';
            }
        });
        
        // Load system stats and project data periodically
        this.loadStats();
        this.loadProjects();
        this.loadAgents();
        setInterval(() => {
            this.loadStats();
            this.loadProjects();
            this.loadAgents();
        }, 30000);
        
        // Enable video interaction on first user click to handle autoplay restrictions
        document.addEventListener('click', this.enableVideoAutoplay.bind(this), { once: true });
        
        // Handle page focus/blur for sleep/wake functionality
        this.bindFocusEvents();
    }
    
    enableVideoAutoplay() {
        const face = document.getElementById('sage-face');
        if (face) {
            face.muted = true; // Ensure muted for autoplay
            face.play().catch(error => {
                console.log('Initial video play failed:', error);
            });
        }
    }
    
    async loadStats() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            this.updateStats(data);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    updateStats(data) {
        const statsContent = document.getElementById('stats-content');
        statsContent.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">Status</span>
                <span class="stat-value">${data.status}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Connections</span>
                <span class="stat-value">${data.connections}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Messages</span>
                <span class="stat-value">${data.message_history_count}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Emotions</span>
                <span class="stat-value">${data.personality.available_emotions.length}</span>
            </div>
        `;
    }
    
    bindFocusEvents() {
        // Handle page focus/blur events for sleep/wake functionality
        window.addEventListener('blur', () => {
            console.log('Page lost focus - putting Sage to sleep');
            this.putSageToSleep();
        });
        
        window.addEventListener('focus', () => {
            console.log('Page gained focus - waking Sage up');
            this.wakeSageUp();
        });
        
        // Also handle visibility change API for better browser compatibility
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log('Page became hidden - putting Sage to sleep');
                this.putSageToSleep();
            } else {
                console.log('Page became visible - waking Sage up');
                this.wakeSageUp();
            }
        });
    }
    
    async putSageToSleep() {
        try {
            const response = await fetch('/api/sleep', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            console.log('Sleep response:', data);
        } catch (error) {
            console.error('Error putting Sage to sleep:', error);
        }
    }
    
    async wakeSageUp() {
        try {
            const response = await fetch('/api/wake', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            console.log('Wake response:', data);
        } catch (error) {
            console.error('Error waking Sage up:', error);
        }
    }
    
    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const data = await response.json();
            this.updateProjects(data.projects);
        } catch (error) {
            console.error('Error loading projects:', error);
        }
    }
    
    updateProjects(projects) {
        const projectsList = document.getElementById('monitored-projects-list');
        
        if (projects.length === 0) {
            projectsList.innerHTML = '<div class="project-item"><div class="project-info"><div class="project-name">No projects configured</div></div></div>';
            return;
        }
        
        projectsList.innerHTML = projects.map(project => `
            <div class="project-item">
                <div class="project-info">
                    <div class="project-name">${project.name}</div>
                    <div class="project-status">${project.status} • ${project.crew_config} • ${project.priority} priority</div>
                </div>
                <div class="activity-indicator">
                    <div class="spinner ${project.is_active ? '' : 'hidden'}"></div>
                    <span class="status-badge status-${project.is_active ? 'processing' : 'idle'}">
                        ${project.is_active ? 'Active' : 'Idle'}
                    </span>
                </div>
            </div>
        `).join('');
    }
    
    async loadAgents() {
        try {
            const response = await fetch('/api/agents');
            const data = await response.json();
            this.updateAgents(data.agents);
        } catch (error) {
            console.error('Error loading agents:', error);
        }
    }
    
    updateAgents(agents) {
        const agentsList = document.getElementById('agents-list');
        
        if (agents.length === 0) {
            agentsList.innerHTML = '<div class="agent-item"><div class="agent-info"><div class="agent-name">No agents configured</div></div></div>';
            return;
        }
        
        agentsList.innerHTML = agents.map(agent => `
            <div class="agent-item">
                <div class="agent-info">
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-status">${agent.status}</div>
                </div>
                <div class="activity-indicator">
                    <div class="spinner ${agent.is_processing ? '' : 'hidden'}"></div>
                    <span class="status-badge status-${agent.is_processing ? 'processing' : 'idle'}">
                        ${agent.is_processing ? 'Processing' : 'Idle'}
                    </span>
                </div>
            </div>
        `).join('');
    }
}

// Initialize the UI when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.sageUI = new SageUI();
});'''
        
        with open(js_path, 'w') as f:
            f.write(js_content)
    
    async def start_server(self, host: str = "127.0.0.1", port: Optional[int] = None):
        """Start the web server."""
        if port is None:
            port = self.config.ui.browser.get("port", 8080)
        
        # Create UI files
        self.create_html_template()
        self.create_css_styles()
        self.create_javascript()
        
        # Auto-open browser if configured
        if self.config.ui.browser.get("auto_open", True):
            def open_browser():
                webbrowser.open(f"http://{host}:{port}")
            
            # Delay browser opening to ensure server is ready
            asyncio.get_event_loop().call_later(2, open_browser)
        
        logging.info(f"Starting Sage web server on http://{host}:{port}")
        
        # Create server config
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
        
        # Create and serve using the existing event loop
        server = uvicorn.Server(config)
        await server.serve()
    
    def start_video_timer(self):
        """Start the video timing management task."""
        # Initialize with an idle video and proper timing
        idle_response = self.personality.create_idle_response()
        logging.info(f"Initialized with idle video: {idle_response.get('video', 'unknown')} - Duration: {idle_response.get('duration', 'unknown')}s")
        
        # Store the initial video data for later use
        self.initial_video_data = idle_response
        
        # Use FastAPI startup event to ensure proper async context
        @self.app.on_event("startup")
        async def startup_video_timer():
            if self.video_timer_task is None:
                self.video_timer_task = asyncio.create_task(self.video_timer_loop())
                # Start initial video broadcast after a short delay
                asyncio.create_task(self.send_initial_video(self.initial_video_data))
                logging.info("✅ Video timer loop started successfully")
    
    async def video_timer_loop(self):
        """Main video timing loop that checks when to change videos."""
        last_video_path = None
        
        while True:
            try:
                # Check if it's time to change the video
                if self.personality.should_change_video():
                    next_video_data = self.personality.get_next_video()
                    
                    if next_video_data:
                        current_video_path = next_video_data.get('video')
                        
                        # Only broadcast and log if the video actually changed
                        if current_video_path != last_video_path:
                            # Broadcast the video change to all connected clients
                            await self.manager.broadcast({
                                "type": "video_change",
                                "data": next_video_data
                            })
                            
                            # Log with detailed information
                            emotion = next_video_data.get('emotion', 'unknown')
                            video_type = next_video_data.get('type', 'unknown')
                            duration = next_video_data.get('duration', 'unknown')
                            
                            logging.info(f"Video changed: {emotion} ({video_type}) - "
                                       f"{current_video_path} - Duration: {duration}s")
                            
                            last_video_path = current_video_path
                        else:
                            # Video hasn't actually changed, just debug log
                            logging.debug(f"Video timer check - no change needed")
                
                # Check every second for video timing
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logging.error(f"Error in video timer loop: {e}")
                await asyncio.sleep(5.0)  # Wait longer on error
    
    async def start_task_with_emotions(self, emotions: List[str], message: str = ""):
        """Start a task with multiple emotions to cycle through."""
        if not emotions:
            return
        
        # Start the task with the first emotion
        first_emotion = emotions[0]
        self.personality.start_task(first_emotion)
        
        # Add remaining emotions to the queue
        for emotion in emotions[1:]:
            self.personality.add_task_emotion(emotion)
        
        # Send notification about task start
        if message:
            await self.send_system_notification(
                message, 
                "processing", 
                {"task_emotions": emotions}
            )
        
        logging.info(f"Started task with emotions: {emotions}")
    
    async def send_task_completion_notification(self, message: str, success_emotion: str = "joyful"):
        """Send a task completion notification with appropriate emotion."""
        # Add completion emotion to show success
        self.personality.add_task_emotion(success_emotion)
        
        # Send the completion message
        await self.send_system_notification(
            message,
            "success",
            {"task_completed": True}
        )
        
        # Complete the task after a short delay to show the success emotion
        await asyncio.sleep(0.5)
        self.personality.complete_task()
    
    async def send_initial_video(self, video_data: Dict[str, Any]):
        """Send initial video to connected clients after a short delay."""
        # Wait a moment for any initial connections
        await asyncio.sleep(2.0)
        
        if self.manager.active_connections:
            await self.manager.broadcast({
                "type": "video_change",
                "data": video_data
            })
            logging.info(f"Sent initial video to {len(self.manager.active_connections)} connected clients")
