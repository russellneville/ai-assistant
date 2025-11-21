"""Personality system for Sage UI."""

import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..core.bedrock_client import BedrockClient


class VideoInfo(BaseModel):
    """Represents a video with location and duration."""
    location: str
    duration: float
    weight: int = 10  # Default weight for backward compatibility


class PersonalityExpression(BaseModel):
    """Represents a personality expression."""
    videos: List[VideoInfo]
    description: str
    use_cases: List[str]


class PersonalitySystem:
    """Manages Sage's personality and emotional expressions."""
    
    def __init__(self, expressions_file: Path, bedrock_client: Optional[BedrockClient] = None):
        """Initialize personality system with expressions configuration."""
        self.expressions_file = expressions_file
        self.bedrock_client = bedrock_client
        self.expressions: Dict[str, PersonalityExpression] = {}
        self.context_mapping: Dict[str, Any] = {}
        self.fallback_emotions: List[str] = ["neutral", "hopeful"]
        self.default_emotion = "neutral"
        self.idle_videos: List[VideoInfo] = []
        self.current_state = "idle"  # "idle", "task", "emotion"
        self.current_video_start_time = None
        self.current_video_duration = None
        self.task_queue = []  # Queue of emotions to show during tasks
        self.is_sleeping = False  # Track sleep state
        self.sleep_pending = False  # Track if sleep should happen after current video
        
        self._load_expressions()
    
    def _load_expressions(self) -> None:
        """Load personality expressions from configuration file."""
        try:
            with open(self.expressions_file, 'r') as f:
                config = json.load(f)
            
            # Load expressions
            for emotion, data in config.get('emotions', {}).items():
                self.expressions[emotion] = PersonalityExpression(**data)
            
            # Load context mapping
            self.context_mapping = config.get('context_mapping', {})
            self.fallback_emotions = config.get('fallback_emotions', ["neutral", "hopeful"])
            
            # Load idle videos
            idle_config = config.get('idle_videos', {})
            idle_videos_data = idle_config.get('videos', [])
            self.idle_videos = [VideoInfo(**video) for video in idle_videos_data]
            
            # Set default emotion
            self.default_emotion = 'neutral'
            
            logging.info(f"Loaded {len(self.expressions)} personality expressions and {len(self.idle_videos)} idle videos")
            
        except Exception as e:
            logging.error(f"Error loading personality expressions: {e}")
            # Create minimal fallback expressions
            self.expressions = {
                "neutral": PersonalityExpression(
                    videos=[VideoInfo(location="./personality/video/sage-idle-blink-1.mp4", duration=10.0)],
                    description="Default neutral expression",
                    use_cases=["general communication"]
                )
            }
    
    def get_emotion_for_context(self, message: str, context: Dict[str, Any]) -> str:
        """Determine appropriate emotion based on message and context."""
        if self.bedrock_client:
            try:
                # Use AI to determine emotion
                response = self.bedrock_client.determine_emotion(message, context)
                emotion = response.content.strip().lower()
                
                # Extract just the emotion name if there's additional text
                for available_emotion in self.expressions.keys():
                    if available_emotion in emotion:
                        if available_emotion in self.expressions:
                            return available_emotion
                        
            except Exception as e:
                logging.warning(f"Error determining emotion with AI: {e}")
        
        # Fallback to rule-based emotion selection
        return self._determine_emotion_by_rules(context)
    
    def _determine_emotion_by_rules(self, context: Dict[str, Any]) -> str:
        """Determine emotion using rule-based logic."""
        candidates = []
        
        # Check error severity
        error_severity = context.get('error_severity')
        if error_severity in self.context_mapping.get('error_severity', {}):
            candidates.extend(self.context_mapping['error_severity'][error_severity])
        
        # Check interaction type
        interaction_type = context.get('interaction_type')
        if interaction_type in self.context_mapping.get('interaction_type', {}):
            candidates.extend(self.context_mapping['interaction_type'][interaction_type])
        
        # Check user relationship
        user_relationship = context.get('user_relationship')
        if user_relationship in self.context_mapping.get('user_relationship', {}):
            candidates.extend(self.context_mapping['user_relationship'][user_relationship])
        
        # Filter candidates to only available expressions
        valid_candidates = [c for c in candidates if c in self.expressions]
        
        if valid_candidates:
            # Random selection from valid candidates for variety
            return random.choice(valid_candidates)
        
        # Use fallback emotions
        valid_fallbacks = [e for e in self.fallback_emotions if e in self.expressions]
        return random.choice(valid_fallbacks) if valid_fallbacks else self.default_emotion
    
    def get_expression_data(self, emotion: str) -> Optional[PersonalityExpression]:
        """Get expression data for a specific emotion."""
        return self.expressions.get(emotion)
    
    def get_emotion_for_message_type(self, message_type: str) -> str:
        """Get appropriate emotion for specific message types."""
        type_mapping = {
            'greeting': 'joyful',
            'error': 'serious',
            'warning': 'skeptical',
            'success': 'joyful',
            'progress': 'hopeful',
            'question': 'neutral',
            'conflict': 'serious',
            'humor': 'laughing',
            'frustration': 'frustrated',
            'processing': 'tired'
        }
        
        emotion = type_mapping.get(message_type, self.default_emotion)
        return emotion if emotion in self.expressions else self.default_emotion
    
    def get_random_positive_emotion(self) -> str:
        """Get a random positive emotion for variety."""
        positive_emotions = ['joyful', 'hopeful', 'cheeky-wink', 'sly-wink', 'laughing']
        available_positive = [e for e in positive_emotions if e in self.expressions]
        
        if available_positive:
            return random.choice(available_positive)
        return self.default_emotion
    
    def create_personality_response(self, message: str, emotion: str, 
                                  additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a complete personality response with emotion and message."""
        expression = self.get_expression_data(emotion)
        
        response = {
            'message': message,
            'emotion': emotion,
            'timestamp': str(int(time.time() * 1000))  # JavaScript timestamp
        }
        
        if expression:
            # Select a weighted random video from the available videos for this emotion
            selected_video = self._weighted_random_selection(expression.videos)
            if selected_video:
                response.update({
                    'video': selected_video.location,
                    'duration': selected_video.duration,
                    'description': expression.description
                })
                
                # Update current video tracking
                self.current_state = "emotion"
                self.current_video_start_time = time.time()
                self.current_video_duration = selected_video.duration
        
        if additional_data:
            response.update(additional_data)
        
        return response
    
    def get_context_for_file_change(self, change_type: str, file_path: str) -> Dict[str, Any]:
        """Create context for file change events."""
        context = {
            'interaction_type': 'status_update',
            'error_severity': 'low'
        }
        
        if change_type in ['deleted', 'moved']:
            context['error_severity'] = 'medium'
        elif 'error' in file_path.lower() or 'exception' in file_path.lower():
            context['error_severity'] = 'high'
            context['interaction_type'] = 'warning'
        
        return context
    
    def get_context_for_system_event(self, event_type: str, severity: str = 'medium') -> Dict[str, Any]:
        """Create context for system events."""
        context = {
            'error_severity': severity,
            'interaction_type': 'status_update'
        }
        
        event_mappings = {
            'startup': {'interaction_type': 'greeting'},
            'shutdown': {'interaction_type': 'greeting'},
            'error': {'interaction_type': 'warning', 'error_severity': 'high'},
            'conflict': {'interaction_type': 'conflict_resolution'},
            'success': {'interaction_type': 'celebration'},
            'discovery': {'interaction_type': 'discovery'},
            'processing': {'interaction_type': 'heavy_processing'}
        }
        
        if event_type in event_mappings:
            context.update(event_mappings[event_type])
        
        return context
    
    def get_available_emotions(self) -> List[str]:
        """Get list of all available emotions."""
        return list(self.expressions.keys())
    
    def _weighted_random_selection(self, videos: List[VideoInfo]) -> Optional[VideoInfo]:
        """Select a video using weighted random selection."""
        if not videos:
            return None
        
        # Calculate total weight
        total_weight = sum(video.weight for video in videos)
        
        if total_weight <= 0:
            # Fallback to equal probability if all weights are invalid
            return random.choice(videos)
        
        # Generate random number within total weight
        random_value = random.randint(1, total_weight)
        
        # Find the video that corresponds to this random value
        cumulative_weight = 0
        for video in videos:
            cumulative_weight += video.weight
            if random_value <= cumulative_weight:
                return video
        
        # Fallback (should not reach here)
        return videos[-1]
    
    def get_random_idle_video(self) -> Optional[VideoInfo]:
        """Get a weighted random idle video for waiting periods."""
        if self.idle_videos:
            return self._weighted_random_selection(self.idle_videos)
        return None
    
    def create_idle_response(self) -> Dict[str, Any]:
        """Create an idle video response for waiting periods."""
        idle_video = self.get_random_idle_video()
        
        response = {
            'message': '',
            'emotion': 'idle',
            'timestamp': str(int(time.time() * 1000)),
            'type': 'idle'
        }
        
        if idle_video:
            response['video'] = idle_video.location
            response['duration'] = idle_video.duration
            response['description'] = 'Waiting for interaction'
            
            # Update current video tracking
            self.current_state = "idle"
            self.current_video_start_time = time.time()
            self.current_video_duration = idle_video.duration
        
        return response
    
    def validate_expressions_config(self) -> Dict[str, Any]:
        """Validate the expressions configuration and return status."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {
                'total_expressions': len(self.expressions),
                'missing_videos': [],
                'total_idle_videos': len(self.idle_videos),
                'context_mappings': len(self.context_mapping)
            }
        }
        
        # Check if expression videos exist
        for emotion, expression in self.expressions.items():
            missing_videos = []
            for video_info in expression.videos:
                if not Path(video_info.location).exists():
                    missing_videos.append(video_info.location)
            
            if missing_videos:
                validation_result['stats']['missing_videos'].append({
                    'emotion': emotion,
                    'missing': missing_videos
                })
                validation_result['warnings'].append(f"Videos not found for {emotion}: {', '.join(missing_videos)}")
        
        # Check if idle videos exist
        missing_idle_videos = []
        for video_info in self.idle_videos:
            if not Path(video_info.location).exists():
                missing_idle_videos.append(video_info.location)
        
        if missing_idle_videos:
            validation_result['warnings'].append(f"Idle videos not found: {', '.join(missing_idle_videos)}")
        
        # Check if fallback emotions exist
        for emotion in self.fallback_emotions:
            if emotion not in self.expressions:
                validation_result['errors'].append(f"Fallback emotion not found: {emotion}")
                validation_result['valid'] = False
        
        # Check if default emotion exists
        if self.default_emotion not in self.expressions:
            validation_result['errors'].append(f"Default emotion not found: {self.default_emotion}")
            validation_result['valid'] = False
        
        return validation_result
    
    def start_task(self, emotion: str) -> None:
        """Start a task with the specified emotion."""
        self.current_state = "task"
        self.task_queue.append(emotion)
        logging.info(f"Task started with emotion: {emotion}")
    
    def add_task_emotion(self, emotion: str) -> None:
        """Add another emotion to the task queue."""
        if self.current_state == "task":
            self.task_queue.append(emotion)
            logging.info(f"Added emotion to task queue: {emotion}")
    
    def complete_task(self) -> None:
        """Complete the current task and return to idle state."""
        self.current_state = "idle"
        self.task_queue.clear()
        self.current_video_start_time = None
        self.current_video_duration = None
        logging.info("Task completed, returning to idle state")
    
    def should_change_video(self) -> bool:
        """Check if it's time to change the current video based on duration."""
        if self.current_video_start_time is None or self.current_video_duration is None:
            return True
        
        elapsed_time = time.time() - self.current_video_start_time
        return elapsed_time >= self.current_video_duration
    
    def get_next_video(self) -> Optional[Dict[str, Any]]:
        """Get the next video to display based on current state."""
        # Check if sleep is pending after current video completes
        if self.sleep_pending and self.should_change_video():
            return self.go_to_sleep()
        
        # Handle sleep state - stay sleeping (no video changes while sleeping)
        if self.current_state == "sleep" or self.is_sleeping:
            return None  # No video changes while sleeping
        
        if self.current_state == "idle":
            # Continue showing random idle videos
            return self.create_idle_response()
        elif self.current_state == "task" and self.task_queue:
            # Get next emotion from task queue
            emotion = self.task_queue.pop(0)
            return self.create_task_emotion_response(emotion)
        elif self.current_state == "task" and not self.task_queue:
            # Task queue is empty, return to idle
            self.complete_task()
            return self.create_idle_response()
        elif self.current_state == "emotion":
            # Emotion video finished, return to idle
            self.current_state = "idle"
            self.current_video_start_time = None
            self.current_video_duration = None
            return self.create_idle_response()
        else:
            # Default to idle for any unknown state
            self.current_state = "idle"
            return self.create_idle_response()
    
    def create_task_emotion_response(self, emotion: str) -> Dict[str, Any]:
        """Create a response for a task emotion."""
        expression = self.get_expression_data(emotion)
        
        response = {
            'message': '',
            'emotion': emotion,
            'timestamp': str(int(time.time() * 1000)),
            'type': 'task_emotion'
        }
        
        if expression:
            # Select a weighted random video from the available videos for this emotion
            selected_video = self._weighted_random_selection(expression.videos)
            if selected_video:
                response.update({
                    'video': selected_video.location,
                    'duration': selected_video.duration,
                    'description': expression.description
                })
                
                # Update current video tracking
                self.current_state = "task"
                self.current_video_start_time = time.time()
                self.current_video_duration = selected_video.duration
        
        return response
    
    def create_enhanced_personality_response(self, message: str, emotion: str, 
                                           additional_data: Optional[Dict[str, Any]] = None,
                                           is_task: bool = False) -> Dict[str, Any]:
        """Create a complete personality response with duration-aware video management."""
        expression = self.get_expression_data(emotion)
        
        response = {
            'message': message,
            'emotion': emotion,
            'timestamp': str(int(time.time() * 1000))
        }
        
        if expression:
            # Select a weighted random video from the available videos for this emotion
            selected_video = self._weighted_random_selection(expression.videos)
            if selected_video:
                response.update({
                    'video': selected_video.location,
                    'duration': selected_video.duration,
                    'description': expression.description
                })
                
                # Update current video tracking
                if is_task:
                    self.current_state = "task"
                else:
                    self.current_state = "emotion"
                
                self.current_video_start_time = time.time()
                self.current_video_duration = selected_video.duration
        
        if additional_data:
            response.update(additional_data)
        
        return response
    
    def get_video_status(self) -> Dict[str, Any]:
        """Get current video status and timing information."""
        status = {
            'current_state': self.current_state,
            'task_queue_length': len(self.task_queue),
            'should_change': self.should_change_video()
        }
        
        if self.current_video_start_time and self.current_video_duration:
            elapsed = time.time() - self.current_video_start_time
            remaining = max(0, self.current_video_duration - elapsed)
            status.update({
                'elapsed_time': elapsed,
                'remaining_time': remaining,
                'total_duration': self.current_video_duration
            })
        
        return status
    
    def go_to_sleep(self) -> Dict[str, Any]:
        """Put Sage to sleep - triggered when page loses focus."""
        if self.is_sleeping:
            return None  # Already sleeping
        
        # If currently playing a video, mark sleep as pending
        if self.current_state in ["emotion", "task"] and not self.should_change_video():
            self.sleep_pending = True
            logging.info("Sleep pending - will sleep after current video completes")
            return None
        
        # Go to sleep immediately
        self.is_sleeping = True
        self.sleep_pending = False
        self.current_state = "sleep"
        
        expression = self.get_expression_data("sleep")
        response = {
            'message': '',
            'emotion': 'sleep',
            'timestamp': str(int(time.time() * 1000)),
            'type': 'sleep'
        }
        
        if expression:
            selected_video = self._weighted_random_selection(expression.videos)
            if selected_video:
                response.update({
                    'video': selected_video.location,
                    'duration': selected_video.duration,
                    'description': expression.description
                })
                
                # Update current video tracking - sleep video doesn't loop
                self.current_video_start_time = time.time()
                self.current_video_duration = selected_video.duration
        
        logging.info("Sage went to sleep")
        return response
    
    def wake_up(self) -> Dict[str, Any]:
        """Wake Sage up - triggered when page regains focus."""
        if not self.is_sleeping:
            return None  # Not sleeping
        
        self.is_sleeping = False
        self.sleep_pending = False
        self.current_state = "emotion"  # Wake up is an emotion, then return to idle
        
        expression = self.get_expression_data("wake")
        response = {
            'message': '',
            'emotion': 'wake',
            'timestamp': str(int(time.time() * 1000)),
            'type': 'wake'
        }
        
        if expression:
            selected_video = self._weighted_random_selection(expression.videos)
            if selected_video:
                response.update({
                    'video': selected_video.location,
                    'duration': selected_video.duration,
                    'description': expression.description
                })
                
                # Update current video tracking
                self.current_video_start_time = time.time()
                self.current_video_duration = selected_video.duration
        
        logging.info("Sage woke up")
        return response
    
    def is_sleep_pending(self) -> bool:
        """Check if sleep is pending after current video."""
        return self.sleep_pending
    
    def get_sleep_state(self) -> Dict[str, Any]:
        """Get current sleep state information."""
        return {
            'is_sleeping': self.is_sleeping,
            'sleep_pending': self.sleep_pending,
            'current_state': self.current_state
        }
