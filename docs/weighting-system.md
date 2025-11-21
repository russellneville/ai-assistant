# Sage Video Weighting System

## Overview

The Sage video weighting system allows fine-tuned control over video selection probability within each emotion category. Instead of purely random selection, videos can be assigned weights that make them more or less likely to be chosen.

## Weight Scale

- **Range**: 1-100
- **Default**: 10 (normal probability)
- **Higher numbers** = more likely to be selected
- **Lower numbers** = less likely to be selected

### Weight Guidelines

| Weight Range | Frequency | Use Case | Example |
|--------------|-----------|----------|---------|
| 1-3 | Very Rare | Easter eggs, special occasions | Holiday-themed videos |
| 4-6 | Rare | Specific contexts, subtle variations | Subtle micro-expressions |
| 7-9 | Less Common | Secondary expressions | Alternative reactions |
| 10 | Normal | Default frequency | Standard expressions |
| 11-15 | More Common | Preferred expressions | Well-liked reactions |
| 16-25 | Common | Go-to expressions | Frequently appropriate |
| 26-50 | Very Common | Primary expressions | Main personality traits |
| 51-100 | Dominant | Critical expressions | Core identity videos |

## JSON Structure

### Before (Current)
```json
{
  "location": "./personality/video/sage-idle-blink-1.mp4",
  "duration": 10.0
}
```

### After (With Weighting)
```json
{
  "location": "./personality/video/sage-idle-blink-1.mp4",
  "duration": 10.0,
  "weight": 10
}
```

## Selection Algorithm

The weighted random selection works as follows:

1. **Calculate Total Weight**: Sum all weights in the emotion category
2. **Generate Random Number**: Between 1 and total weight
3. **Find Selection**: Iterate through videos, adding weights until the random number is reached
4. **Return Video**: The video whose cumulative weight range contains the random number

### Example Calculation

Given videos with weights [5, 10, 25, 10]:
- Total weight: 50
- Random number: 23
- Cumulative weights: [5, 15, 40, 50]
- Selection: Video 3 (weight 25) because 23 falls in range 16-40

## Implementation Plan

### Phase 1: JSON Configuration Update ✅ COMPLETED
- [x] Add `weight` field to all existing videos with default value of 10
- [x] Update `personality/expressions-video.json` structure
- [x] Update technical specifications section
- [x] Maintain backward compatibility (missing weight defaults to 10)

### Phase 2: Python Code Enhancement ✅ COMPLETED
- [x] Update `VideoInfo` model in `sage/ui/personality.py` to include weight field
- [x] Implement weighted random selection algorithm
- [x] Modify `PersonalitySystem` class methods:
  - [x] `create_personality_response()`
  - [x] `create_idle_response()`
  - [x] `create_task_emotion_response()`
- [x] Add weight validation and error handling

### Phase 3: Add-Video Tool Enhancement 🔄 PENDING
- [ ] Add `--weight` option to CLI tool
- [ ] Update `docs/add-video-tool.md` documentation
- [ ] Provide weight selection guidance in tool output
- [ ] Add weight validation (1-100 range)

### Phase 4: Testing and Validation ✅ COMPLETED
- [x] Test weighted selection algorithm
- [x] Verify backward compatibility
- [x] Test edge cases (all weights = 1, single video, etc.)
- [x] Update validation methods in `PersonalitySystem`

## Practical Examples

### Neutral Emotion Weighting Example
```json
"neutral": {
  "videos": [
    {
      "location": "./personality/video/sage-idle-blink-1.mp4",
      "duration": 10.0,
      "weight": 30
    },
    {
      "location": "./personality/video/sage-idle-blink-2.mp4",
      "duration": 5.0,
      "weight": 15
    },
    {
      "location": "./personality/video/sage-idle-blink-3.mp4",
      "duration": 5.0,
      "weight": 10
    },
    {
      "location": "./personality/video/sage-idle-blink-4.mp4",
      "duration": 5.0,
      "weight": 5
    }
  ]
}
```

**Probability Analysis:**
- Total weight: 60 (30+15+10+5)
- `sage-idle-blink-1.mp4`: 50% chance (30/60)
- `sage-idle-blink-2.mp4`: 25% chance (15/60)
- `sage-idle-blink-3.mp4`: 16.7% chance (10/60)
- `sage-idle-blink-4.mp4`: 8.3% chance (5/60)

**Relative Comparisons:**
- Video 1 is 6x more likely than Video 4 (30 vs 5)
- Video 1 is 2x more likely than Video 2 (30 vs 15)
- Video 2 is 1.5x more likely than Video 3 (15 vs 10)

### Joyful Emotion Weighting
```json
"joyful": {
  "videos": [
    {
      "location": "./personality/video/sage-thumbs-up-1.mp4",
      "duration": 4.157,
      "weight": 25
    },
    {
      "location": "./personality/video/sage-thumbs-up-2.mp4",
      "duration": 5.0,
      "weight": 20
    },
    {
      "location": "./personality/video/sage-rock-on-big.mp4",
      "duration": 5.0,
      "weight": 15
    },
    {
      "location": "./personality/video/sage-rock-on-wild.mp4",
      "duration": 5.0,
      "weight": 5
    }
  ]
}
```

## CLI Usage Examples

### Adding a video with specific weight
```bash
sage add-video celebration.mp4 --emotion joyful --weight 30
```

### Adding a rare easter egg video
```bash
sage add-video holiday-special.mp4 --emotion neutral --weight 2
```

### Adding a dominant expression
```bash
sage add-video primary-thinking.mp4 --emotion thinking --weight 50
```

## Backward Compatibility

- Videos without a `weight` field will default to weight 10
- Existing JSON files will continue to work without modification
- The system gracefully handles mixed configurations (some videos with weights, some without)

## Technical Considerations

### Performance
- Weighted selection is O(n) where n is the number of videos in the category
- For typical emotion categories (3-5 videos), performance impact is negligible
- Total weight calculation is cached per emotion category

### Validation
- Weights must be integers between 1 and 100
- Invalid weights default to 10 with a warning
- Zero or negative weights are rejected

### Error Handling
- If all videos in a category have weight 0 (invalid), fall back to equal probability
- If weight calculation fails, fall back to random selection
- Log warnings for invalid weight configurations

## Migration Strategy

1. **Gradual Rollout**: Add weights to high-impact emotions first (neutral, joyful, serious)
2. **User Testing**: Monitor video selection patterns after weight implementation
3. **Fine-tuning**: Adjust weights based on user feedback and usage patterns
4. **Documentation**: Update all relevant documentation and examples

## Future Enhancements

- **Dynamic Weights**: Adjust weights based on user interaction patterns
- **Context-Aware Weights**: Different weights for different contexts (time of day, project type)
- **Weight Profiles**: Predefined weight configurations for different personality modes
- **Analytics**: Track which videos are selected most often to optimize weights
