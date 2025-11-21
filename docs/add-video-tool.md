# Sage Add-Video Tool

The `sage add-video` command allows you to easily add new videos to Sage's personality system with automatic duration extraction and AI-powered emotion classification. It supports both single video addition and batch processing of new videos found in the personality/video folder.

## Usage

```bash
sage add-video [VIDEO_PATH] [OPTIONS]
```

**Note:** If no VIDEO_PATH is provided, the tool will scan the `./personality/video` folder for new videos not yet configured in `expressions-video.json` and process them interactively.

## Basic Examples

### Scan and add new videos interactively
```bash
sage add-video
```
This will:
1. Scan `./personality/video` for videos not in `expressions-video.json`
2. Show a list of found videos
3. Process each video file-by-file with user prompts
4. Allow skipping videos with 's'
5. Ask for emotion determination method (manual or AI)
6. Provide options for idle_videos, sleep, and wake categories
7. Prompt for weight values

### Add a video with AI classification
```bash
sage add-video /path/to/my-video.mp4
```

### Add a video to a specific emotion category
```bash
sage add-video /path/to/my-video.mp4 --emotion joyful
```

### Add a video with custom description and use cases
```bash
sage add-video /path/to/my-video.mp4 \
  --emotion excited \
  --description "Enthusiastic celebration expression" \
  --use-cases "project completion,milestone achievements,positive feedback"
```

### Preview changes without making them (dry run)
```bash
sage add-video /path/to/my-video.mp4 --dry-run
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--config` | `-c` | Path to configuration file |
| `--emotion` | `-e` | Force specific emotion category (skip AI classification) |
| `--description` | `-d` | Custom description for the video |
| `--use-cases` | `-u` | Comma-separated list of use cases |
| `--dry-run` | | Show what would be done without making changes |

## How It Works

1. **Video Validation**: Checks if the video file exists and has a supported format (.mp4, .avi, .mov, .mkv, .webm)

2. **Duration Extraction**: Uses ffmpeg/ffprobe to extract the precise video duration

3. **AI Classification**: If no emotion is specified, uses AWS Bedrock to analyze the video filename and classify the appropriate emotion category

4. **Manual Fallback**: If AI classification fails, prompts the user to manually select or create an emotion category

5. **File Management**: Copies the video to the `personality/video/` directory if it's not already there

6. **Data Structure Update**: Updates the `personality/expressions-video.json` file with the new video entry

## AI Classification

The AI classification system:
- Analyzes the video filename to determine the most appropriate emotion
- Considers existing emotion categories first
- Can suggest new emotion categories if the video represents a distinct emotion
- Uses the format: lowercase, hyphenated (e.g., "happy-excited", "confused-thinking")

## Existing Emotion Categories

The tool recognizes these existing emotions:
- neutral
- joyful
- serious
- hopeful
- skeptical
- shock
- sarcastic
- ironic
- cheeky-wink
- sly-wink
- frustrated
- tired
- eyeroll
- laughing
- thinking

## Video Entry Format

Videos are stored in the following format:
```json
{
  "location": "./personality/video/video-name.mp4",
  "duration": 5.0
}
```

## Requirements

- ffmpeg/ffprobe must be installed and available in PATH
- AWS Bedrock access configured (for AI classification)
- Sage configuration file properly set up

## Troubleshooting

### "ffprobe failed" error
- Ensure ffmpeg is installed: `brew install ffmpeg` (macOS) or equivalent
- Check that the video file is not corrupted

### "AI classification failed" error
- Check AWS credentials: `aws sso login`
- Verify Bedrock access in your AWS region
- Use `--emotion` flag to skip AI classification

### "Expressions file not found" error
- Ensure you're running the command from the Sage project directory
- Check that `personality/expressions-video.json` exists

## Interactive Scanning Mode

When run without arguments (`sage add-video`), the tool enters interactive scanning mode:

### Workflow
1. **Scan**: Automatically scans `./personality/video` folder
2. **Compare**: Checks against existing videos in `expressions-video.json`
3. **List**: Shows all new videos found
4. **Process**: Goes through each video file-by-file

### User Prompts
For each video, you'll be prompted for:

#### 1. Add Video Confirmation
- **Prompt**: "Add this video? (y/n/s to skip):"
- **Options**: 
  - `y` or `yes` or `Enter`: Add the video
  - `n` or `no`: Skip this video
  - `s` or `skip`: Skip this video

#### 2. Video Category Selection
- **Prompt**: "Select video category:"
- **Options**:
  1. **Emotion** (specific emotional expression)
  2. **Idle videos** (random background videos)
  3. **Sleep** (when page loses focus)
  4. **Wake** (when page regains focus)

#### 3. Emotion Determination Method (for Emotion category)
- **Prompt**: "How would you like to determine the emotion?"
- **Options**:
  1. **Manual selection** (choose from existing emotions)
  2. **AI classification** (let AI decide based on filename)

#### 4. Weight Selection
- **Prompt**: "Enter weight (1-100, default 10):"
- **Range**: 1-100 (higher numbers = more likely to be selected)
- **Default**: 10

### Special Categories

#### Idle Videos
- Used for random background animations when Sage is waiting
- Higher weights make videos appear more frequently
- Typical weight range: 5-75

#### Sleep/Wake Videos
- **Sleep**: Played when browser tab loses focus
- **Wake**: Played when browser tab regains focus
- Usually only need 1-2 videos per category
- Weight affects selection if multiple videos exist

## Video Categories and Weighting

### Emotion Categories
All existing emotion categories are available:
- neutral, joyful, serious, hopeful, skeptical
- shock, sarcastic, ironic, cheeky-wink, sly-wink
- frustrated, tired, eyeroll, laughing, thinking
- sleep, wake (special categories)

### Weight Guidelines
- **1-10**: Rare/special videos
- **10-25**: Normal frequency
- **25-50**: Common videos
- **50-100**: Very frequent videos

## Examples

### Interactive scanning session
```bash
sage add-video
# Scanning for new videos in personality/video folder...
# Found 3 new video(s):
#  1. sage-new-laugh.mp4
#  2. sage-confused-look.mp4
#  3. sage-sleepy-yawn.mp4
# 
# Processing video 1/3: sage-new-laugh.mp4
# Add this video? (y/n/s to skip): y
# Duration: 4.2s
# Select video category:
#  1. Emotion (specific emotional expression)
#  2. Idle videos (random background videos)
#  3. Sleep (when page loses focus)
#  4. Wake (when page regains focus)
# Select category (1-4): 1
# How would you like to determine the emotion?
#  1. Manual selection (choose from existing emotions)
#  2. AI classification (let AI decide based on filename)
# Select method (1-2): 2
# AI classified as: laughing
# Enter weight (1-100, default 10): 15
# ✓ Added to 'laughing' emotion
```

### Adding a new celebration video
```bash
sage add-video celebration.mp4 --emotion joyful --description "Victory celebration gesture"
```

### Creating a new emotion category
```bash
sage add-video confused-look.mp4 --emotion confused --description "Puzzled and uncertain expression"
```

### Testing before making changes
```bash
sage add-video new-video.mp4 --dry-run
```

### Batch processing with dry run
```bash
sage add-video --dry-run
```

This tool makes it easy to expand Sage's personality system with new video expressions while maintaining the proper data structure and metadata. The interactive scanning mode is particularly useful when you have multiple new videos to process efficiently.
