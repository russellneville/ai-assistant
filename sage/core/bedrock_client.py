"""AWS Bedrock client for Sage LLM integration."""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel

from ..config.models import AWSConfig


class BedrockResponse(BaseModel):
    """Response from Bedrock API."""
    content: str
    usage: Dict[str, int]
    model: str
    stop_reason: Optional[str] = None


class BedrockClient:
    """Client for interacting with AWS Bedrock."""
    
    def __init__(self, aws_config: AWSConfig):
        """Initialize Bedrock client with AWS configuration."""
        self.config = aws_config
        self.client = None
        self.default_system_prompt = None
        self._load_system_prompt()
        self._initialize_client()
    
    def _load_system_prompt(self) -> None:
        """Load the system prompt from sage.prompt file."""
        try:
            # Try to find the sage.prompt file
            current_dir = Path(__file__).parent.parent  # Go up to the sage package directory
            prompt_file = current_dir / "sage.prompt"
            
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    self.default_system_prompt = f.read()
                logging.info(f"Loaded system prompt from {prompt_file}")
            else:
                logging.warning(f"sage.prompt file not found at {prompt_file}")
                # Fallback to a basic system prompt
                self.default_system_prompt = (
                    "You are Sage, an intelligent AI assistant helping with software development tasks. "
                    "You provide clear, accurate, and helpful responses."
                )
        except Exception as e:
            logging.error(f"Failed to load system prompt: {e}")
            self.default_system_prompt = (
                "You are Sage, an intelligent AI assistant helping with software development tasks. "
                "You provide clear, accurate, and helpful responses."
            )
    
    def _initialize_client(self) -> None:
        """Initialize the Bedrock runtime client using SSO credentials."""
        try:
            # Check if a specific profile is configured
            profile_name = getattr(self.config, 'profile', None) or 'poc'
            
            # Use the specified profile (defaults to poc for Bedrock access)
            session = boto3.Session(profile_name=profile_name)
            self.client = session.client(
                'bedrock-runtime',
                region_name=self.config.region
            )
            logging.info(f"Bedrock client initialized for region: {self.config.region} using profile: {profile_name}")
        except NoCredentialsError:
            logging.error(f"AWS credentials not found for profile '{profile_name}'. Please run 'aws sso login' to authenticate.")
            raise
        except Exception as e:
            logging.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    def _prepare_claude_request(self, prompt: str, 
                               system_prompt: Optional[str] = None,
                               max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Prepare request payload for Claude model."""
        messages = [{"role": "user", "content": prompt}]
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.config.bedrock.get("max_tokens", 4096),
            "messages": messages
        }
        
        if system_prompt:
            request_body["system"] = system_prompt
        
        return request_body
    
    def invoke_model(self, prompt: str, 
                    system_prompt: Optional[str] = None,
                    max_tokens: Optional[int] = None) -> BedrockResponse:
        """Invoke the configured model with a prompt."""
        if not self.client:
            raise RuntimeError("Bedrock client not initialized")
        
        model_id = self.config.bedrock.get("model", "us.anthropic.claude-sonnet-4-20250514-v1:0")
        
        # Use the default system prompt if none provided
        effective_system_prompt = system_prompt or self.default_system_prompt
        
        try:
            # Prepare request based on model type
            if "anthropic" in model_id.lower() or "claude" in model_id.lower():
                request_body = self._prepare_claude_request(prompt, effective_system_prompt, max_tokens)
            else:
                raise ValueError(f"Unsupported model: {model_id}")
            
            # Make the API call
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract content based on model type
            if "anthropic" in model_id.lower() or "claude" in model_id.lower():
                content = response_body['content'][0]['text']
                usage = response_body.get('usage', {})
                stop_reason = response_body.get('stop_reason')
            else:
                raise ValueError(f"Unsupported model response format: {model_id}")
            
            return BedrockResponse(
                content=content,
                usage=usage,
                model=model_id,
                stop_reason=stop_reason
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logging.error(f"Bedrock API error {error_code}: {error_message}")
            raise
        except Exception as e:
            logging.error(f"Error invoking Bedrock model: {e}")
            raise
    
    def analyze_code(self, code: str, file_path: str, 
                    analysis_type: str = "general") -> BedrockResponse:
        """Analyze code and extract relevant information."""
        # Combine Sage base prompt with specialized instruction
        system_prompt = self.default_system_prompt + "\n\n" + (
            "As an expert code analyst, analyze the provided code and extract "
            "relevant information for project documentation."
        )
        
        prompt = f"""Analyze the following code file and provide insights:

File: {file_path}
Analysis Type: {analysis_type}

Code:
```
{code}
```

Please provide:
1. Technologies and frameworks detected
2. Key patterns and architectural decisions
3. Dependencies and integrations
4. Notable features or complexity
5. Potential context that would be valuable for AI assistants working on this project

Format your response as structured information that can be easily processed."""
        
        return self.invoke_model(prompt, system_prompt)
    
    def extract_technologies(self, project_files: List[Dict[str, str]]) -> BedrockResponse:
        """Extract technologies from project files."""
        # Combine Sage base prompt with specialized instruction
        system_prompt = self.default_system_prompt + "\n\n" + (
            "As a technology identification expert, analyze project files "
            "and identify all technologies, frameworks, and tools being used."
        )
        
        files_info = []
        for file_info in project_files:
            files_info.append(f"File: {file_info['path']}\nContent: {file_info['content'][:1000]}...")
        
        prompt = f"""Analyze these project files and identify all technologies:

{chr(10).join(files_info)}

Please identify:
1. Programming languages
2. Frameworks and libraries
3. Databases and storage systems
4. Build tools and package managers
5. Development tools and configurations
6. Cloud services and platforms
7. Testing frameworks
8. Any other relevant technologies

Provide a structured list of technologies with confidence levels."""
        
        return self.invoke_model(prompt, system_prompt)
    
    def match_context(self, project_technologies: List[str], 
                     available_context: List[str]) -> BedrockResponse:
        """Match project technologies with available context."""
        # Combine Sage base prompt with specialized instruction
        system_prompt = self.default_system_prompt + "\n\n" + (
            "As a context matching specialist, given a project's technologies "
            "and available context items, determine which context would be most valuable."
        )
        
        prompt = f"""Match technologies with relevant context:

Project Technologies:
{chr(10).join(f'- {tech}' for tech in project_technologies)}

Available Context Items:
{chr(10).join(f'- {ctx}' for ctx in available_context)}

Please provide:
1. Highly relevant context matches (score 9-10)
2. Moderately relevant matches (score 6-8)
3. Potentially useful matches (score 3-5)
4. Reasoning for each match

Format as a structured list with scores and explanations."""
        
        return self.invoke_model(prompt, system_prompt)
    
    def resolve_conflict(self, conflict_description: str, 
                        options: List[str]) -> BedrockResponse:
        """Help resolve conflicts between different context or rules."""
        # Combine Sage base prompt with specialized instruction
        system_prompt = self.default_system_prompt + "\n\n" + (
            "As a conflict resolution specialist, analyze conflicts objectively "
            "and provide recommendations for resolution."
        )
        
        prompt = f"""Analyze this conflict and suggest resolution:

Conflict: {conflict_description}

Available Options:
{chr(10).join(f'{i+1}. {option}' for i, option in enumerate(options))}

Please provide:
1. Analysis of the conflict
2. Pros and cons of each option
3. Recommended resolution with reasoning
4. Whether user input is required
5. Alternative solutions if applicable

Focus on maintaining consistency and maximizing value for the user."""
        
        return self.invoke_model(prompt, system_prompt)
    
    def determine_emotion(self, message: str, context: Dict[str, Any]) -> BedrockResponse:
        """Determine appropriate emotion for Sage's personality system."""
        # Combine Sage base prompt with specialized instruction
        system_prompt = self.default_system_prompt + "\n\n" + (
            "As part of your personality system, determine the most appropriate "
            "emotional expression based on the message and context."
        )
        
        prompt = f"""Determine appropriate emotion for this interaction:

Message: {message}
Context: {json.dumps(context, indent=2)}

Available emotions: neutral, joyful, serious, hopeful, skeptical, shock, 
sarcastic, ironic, cheeky-wink, sly-wink, frustrated, tired, eyeroll, laughing

Consider:
1. Message tone and content
2. Severity of any issues
3. Type of interaction
4. User relationship level
5. Current system state

Respond with just the emotion name and brief reasoning."""
        
        return self.invoke_model(prompt, system_prompt)
    
    def health_check(self) -> bool:
        """Check if Bedrock client is working properly."""
        try:
            test_response = self.invoke_model(
                "Hello, this is a health check. Please respond with 'OK'.",
                max_tokens=10
            )
            return "OK" in test_response.content or "ok" in test_response.content.lower()
        except Exception as e:
            logging.error(f"Bedrock health check failed: {e}")
            return False
