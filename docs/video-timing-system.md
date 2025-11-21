# Sage Video Timing System

## Overview

The Sage Video Timing System provides sophisticated duration-based video management for the personality interface. Instead of simply playing videos without timing consideration, the system now uses the actual duration data from `personality/expressions-video.json` to intelligently control when videos change, creating a more natural and responsive user experience.

## Key Features

### 🎬 Duration-Aware Video Management
- **Precise Timing Control**: Uses actual video durations from JSON configuration
- **Smart State Transitions**: Automatic transitions between idle, task, and emotion states
- **Real-time Synchronization**: Background timer ensures perfect video timing
- **Queue Management**: Multiple emotions can be queued for complex workflows

### 🔄 State Management System

The system operates in three primary states:

1. **Idle State**: Shows random idle videos for their specified duration
2. **Task State**: Cycles through queued task emotions, each playing for their video duration  
3. **Emotion State**: Shows specific emotion videos for messages/responses

```
┌─────────┐    start_task()    ┌──────────┐    queue empty    ┌─────────┐
│  IDLE   │ ─────────────────→ │   TASK   │ ─────────────────→│  IDLE   │
│         │                    │          │                   │         │
└─────────┘                    └──────────┘                   └─────────┘
     ↑                              │                              ↑
     │                              │ get_next_video()             │
     │                              ↓                              │
     │                         ┌──────────┐                       │
     └─────────────────────────│ EMOTION  │───────────────────────┘
                               │          │    duration complete
                               └──────────┘
```

## Implementation Details

### Core Components

#### 1. PersonalitySystem Enhancements

**New Classes:**
```python
class VideoInfo(BaseModel):
    location: str    # Path to video file
    duration: float  # Duration in seconds

class PersonalityExpression(BaseModel):
    videos: List[VideoInfo]  # Now uses VideoInfo objects
    description: str
    use_cases: List[str]
```

**Key Methods:**
- `should_change_video()`: Checks if current video duration has elapsed
- `get_next_video()`: Returns next video based on current state
- `start_task(emotion)`: Begins task with initial emotion
- `add_task_emotion(emotion)`: Adds emotion to task queue
- `complete_task()`: Returns to idle state
- `get_video_status()`: Returns timing and state information

#### 2. Web Server Integration

**Video Timer Loop:**
```python
async def video_timer_loop(self):
    """Main video timing loop that checks when to change videos."""
    while True:
        if self.personality.should_change_video():
            next_video_data = self.personality.get_next_video()
            if next_video_data:
                await self.manager.broadcast({
                    "type": "video_change",
                    "data": next_video_data
                })
        await asyncio.sleep(1.0)
```

**New API Endpoints:**
- `GET /api/video-status`: Get current video timing status
- `POST /api/start-task`: Start a task with specific emotion
- `POST /api/add-task-emotion`: Add emotion to task queue
- `POST /api/complete-task`: Complete current task

#### 3. Frontend JavaScript Updates

**Enhanced Message Handling:**
```javascript
handleMessage(data) {
    if (data.type === 'video_change') {
        this.updatePersonality(data.data);
        console.log('Video changed:', data.data.emotion, data.data.type);
    }
    // ... other message types
}
```

**Improved Video Management:**
```javascript
updatePersonality(messageData) {
    if (messageData.video) {
        const source = face.querySelector('source');
        if (source) {
            source.src = messageData.video;
            face.load();
            face.play().catch(error => {
                console.log('Video play failed:', error);
            });
        }
    }
    
    // Log timing information for debugging
    if (messageData.duration) {
        console.log(`Video duration: ${messageData.duration}s, Emotion: ${messageData.emotion}`);
    }
}
```

## Usage Examples

### Basic Idle Video Cycling

When no tasks are active, Sage shows random idle videos:

```python
# System automatically cycles through idle videos
idle_response = personality.create_idle_response()
# Shows random idle video for its specified duration (5-10 seconds)
# After duration elapses, automatically switches to next random idle video
```

### Task with Multiple Emotions

For complex tasks requiring multiple emotional expressions:

```python
# Start a task with thinking, then show progress, then celebration
personality.start_task("thinking")           # Shows thinking video (5s)
personality.add_task_emotion("hopeful")      # Queued: hopeful video (10s)  
personality.add_task_emotion("joyful")       # Queued: joyful video (4.157s)

# Videos will play in sequence:
# 1. thinking (5s) → 2. hopeful (10s) → 3. joyful (4.157s) → back to idle
```

### Web Server Task Management

```python
# Start a file analysis task
await web_server.start_task_with_emotions(
    ["thinking", "serious", "hopeful"], 
    "Analyzing project files for context updates..."
)

# Complete with success
await web_server.send_task_completion_notification(
    "Analysis complete! Found 15 new patterns.",
    "joyful"
)
```

## Configuration Format

The `personality/expressions-video.json` file now uses this structure:

```json
{
  "emotions": {
    "joyful": {
      "videos": [
        {
          "location": "./personality/video/sage-thumbs-up-1.mp4",
          "duration": 4.157
        },
        {
          "location": "./personality/video/sage-thumbs-up-2.mp4", 
          "duration": 5.0
        }
      ],
      "description": "Happy and enthusiastic expression",
      "use_cases": ["successful task completion", "positive discoveries"]
    }
  },
  "idle_videos": {
    "videos": [
      {
        "location": "./personality/video/sage-idle-blink-1.mp4",
        "duration": 10.0
      },
      {
        "location": "./personality/video/sage-idle-blink-2.mp4",
        "duration": 5.0
      }
    ]
  }
}
```

## Benefits

### 🎯 Enhanced User Experience
- **Natural Timing**: Videos play for their actual duration, not arbitrary timeouts
- **Smooth Transitions**: No jarring cuts or premature video changes
- **Contextual Responses**: Appropriate emotions for different interaction types
- **Engaging Interactions**: Dynamic personality that responds to system state

### 🔧 Technical Advantages
- **Precise Control**: Exact timing based on actual video content
- **Scalable Architecture**: Async timer system handles multiple connections
- **State Consistency**: Clear state management prevents timing conflicts
- **Debugging Support**: Comprehensive logging and status endpoints

### 🚀 Development Benefits
- **Easy Configuration**: JSON-driven video and timing configuration
- **Extensible Design**: Simple to add new emotions and videos
- **Testing Support**: Built-in status and timing information
- **Production Ready**: Robust error handling and graceful degradation

## Testing

Use the provided test script to verify functionality:

```bash
python test_video_timing.py
```

This will test:
- Video duration loading and timing
- State transitions (idle → task → emotion → idle)
- Task emotion queuing and processing
- Context-based emotion selection
- Enhanced response creation

## API Reference

### PersonalitySystem Methods

```python
# State Management
start_task(emotion: str) -> None
add_task_emotion(emotion: str) -> None  
complete_task() -> None

# Video Control
should_change_video() -> bool
get_next_video() -> Optional[Dict[str, Any]]
get_video_status() -> Dict[str, Any]

# Response Creation
create_idle_response() -> Dict[str, Any]
create_task_emotion_response(emotion: str) -> Dict[str, Any]
create_enhanced_personality_response(message: str, emotion: str, 
                                   additional_data: Optional[Dict], 
                                   is_task: bool = False) -> Dict[str, Any]
```

### WebSocket Messages

**Video Change Message:**
```json
{
  "type": "video_change",
  "data": {
    "video": "./personality/video/sage-joyful-1.mp4",
    "duration": 4.157,
    "emotion": "joyful",
    "type": "task_emotion",
    "description": "Happy and enthusiastic expression",
    "timestamp": "1704672000000"
  }
}
```

**Status Response:**
```json
{
  "current_state": "task",
  "task_queue_length": 2,
  "should_change": false,
  "elapsed_time": 2.5,
  "remaining_time": 2.5,
  "total_duration": 5.0
}
```

## Future Enhancements

### Potential Improvements
- **Video Preloading**: Cache next videos for smoother transitions
- **Adaptive Timing**: Adjust timing based on user interaction patterns
- **Emotion Blending**: Smooth transitions between different emotional states
- **Performance Metrics**: Track video loading and playback performance
- **Custom Timing Rules**: User-configurable timing preferences

### Integration Opportunities
- **Agent Task Integration**: Automatic emotion queuing based on agent activities
- **File Change Reactions**: Specific emotions for different types of file changes
- **Error State Handling**: Dedicated error recovery video sequences
- **User Preference Learning**: Adapt timing based on user behavior patterns

## Conclusion

The Sage Video Timing System transforms the personality interface from a simple video player into an intelligent, responsive, and engaging user experience. By leveraging actual video durations and sophisticated state management, Sage now provides natural, contextually appropriate emotional expressions that enhance the overall interaction quality.

The system is production-ready, thoroughly tested, and designed for easy extension and customization. Whether you're monitoring a single project or managing complex multi-project workflows, Sage's personality system now provides the perfect emotional context for every interaction.
