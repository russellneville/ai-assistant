"""Command line interface for Sage."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.sage_main import SageApplication
from .config.loader import ConfigLoader


def _get_video_duration(video_path: Path) -> float:
    """Extract video duration using ffprobe."""
    import subprocess
    
    cmd = [
        'ffprobe', 
        '-v', 'quiet', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return round(duration, 3)
    except subprocess.CalledProcessError as e:
        raise Exception(f"ffprobe failed: {e.stderr}")
    except ValueError as e:
        raise Exception(f"Invalid duration format: {e}")


def _classify_video_emotion(bedrock_client, video_path: Path) -> str:
    """Use AI to classify the emotion of a video based on its filename and context."""
    
    # Get existing emotions for context
    try:
        import json
        with open("personality/expressions-video.json", 'r') as f:
            expressions_data = json.load(f)
        existing_emotions = list(expressions_data["emotions"].keys())
    except:
        existing_emotions = ["neutral", "joyful", "serious", "hopeful", "skeptical", "shock", "sarcastic", "ironic", "cheeky-wink", "sly-wink", "frustrated", "tired", "eyeroll", "laughing", "thinking"]
    
    # Create classification prompt
    prompt = f"""Analyze this video filename and classify its emotional expression: "{video_path.name}"

Based on the filename, determine which emotion category this video most likely represents.

Existing emotion categories:
{', '.join(existing_emotions)}

Guidelines:
- If the filename clearly matches an existing emotion, use that category
- If it represents a new distinct emotion not covered by existing categories, suggest a new emotion name
- Consider the context: this is for an AI assistant's personality expressions
- Use lowercase, hyphenated format for new emotions (e.g., "happy-excited", "confused-thinking")

Respond with ONLY the emotion name, nothing else."""

    try:
        response = bedrock_client.invoke_model(prompt, max_tokens=50)
        emotion = response.content.strip().lower()
        
        # Clean up the response - remove any extra text
        emotion = emotion.split('\n')[0].split('.')[0].strip()
        
        # Validate format
        if not emotion or len(emotion) > 30:
            raise Exception("Invalid emotion classification response")
            
        return emotion
        
    except Exception as e:
        raise Exception(f"AI classification failed: {e}")


def _prompt_for_emotion() -> str:
    """Prompt user to manually select or enter an emotion."""
    
    # Load existing emotions
    try:
        import json
        with open("personality/expressions-video.json", 'r') as f:
            expressions_data = json.load(f)
        existing_emotions = list(expressions_data["emotions"].keys())
    except:
        existing_emotions = ["neutral", "joyful", "serious", "hopeful", "skeptical", "shock", "sarcastic", "ironic", "cheeky-wink", "sly-wink", "frustrated", "tired", "eyeroll", "laughing", "thinking"]
    
    console.print("\n[yellow]Available emotions:[/yellow]")
    for i, emotion in enumerate(existing_emotions, 1):
        console.print(f"[dim]{i:2d}.[/dim] {emotion}")
    
    console.print(f"[dim]{len(existing_emotions)+1:2d}.[/dim] [italic]Create new emotion[/italic]")
    
    while True:
        try:
            choice = typer.prompt("\nSelect emotion number or enter custom emotion name")
            
            # Check if it's a number
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(existing_emotions):
                    return existing_emotions[choice_num - 1]
                elif choice_num == len(existing_emotions) + 1:
                    custom_emotion = typer.prompt("Enter new emotion name (lowercase, hyphenated)")
                    return custom_emotion.lower().strip()
                else:
                    console.print("[red]Invalid number. Please try again.[/red]")
                    continue
            except ValueError:
                # It's a custom emotion name
                return choice.lower().strip()
                
        except typer.Abort:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)


def _get_existing_video_paths(expressions_data: dict) -> set:
    """Extract all existing video paths from expressions data."""
    existing_paths = set()
    
    # Get paths from emotions
    for emotion_data in expressions_data.get("emotions", {}).values():
        for video in emotion_data.get("videos", []):
            if "location" in video:
                # Normalize path format
                path = video["location"].replace("./personality/video/", "")
                existing_paths.add(path)
    
    # Get paths from idle_videos
    idle_videos = expressions_data.get("idle_videos", {})
    for video in idle_videos.get("videos", []):
        if "location" in video:
            # Normalize path format
            path = video["location"].replace("./personality/video/", "")
            existing_paths.add(path)
    
    # Get paths from sleep and wake
    for special_category in ["sleep", "wake"]:
        if special_category in expressions_data.get("emotions", {}):
            for video in expressions_data["emotions"][special_category].get("videos", []):
                if "location" in video:
                    path = video["location"].replace("./personality/video/", "")
                    existing_paths.add(path)
    
    return existing_paths


def _scan_for_new_videos() -> list:
    """Scan personality/video folder for videos not in expressions-video.json."""
    video_dir = Path("personality/video")
    if not video_dir.exists():
        console.print(f"[red]Error: Video directory not found: {video_dir}[/red]")
        return []
    
    # Load existing expressions data
    try:
        import json
        with open("personality/expressions-video.json", 'r') as f:
            expressions_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading expressions file: {e}[/red]")
        return []
    
    # Get existing video paths
    existing_paths = _get_existing_video_paths(expressions_data)
    
    # Scan for video files
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    all_videos = []
    
    for file_path in video_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            if file_path.name not in existing_paths:
                all_videos.append(file_path)
    
    return sorted(all_videos)


def _prompt_for_video_category() -> str:
    """Prompt user to select video category (emotion, idle_videos, sleep, wake)."""
    console.print("\n[yellow]Select video category:[/yellow]")
    console.print("[dim]1.[/dim] Emotion (specific emotional expression)")
    console.print("[dim]2.[/dim] Idle videos (random background videos)")
    console.print("[dim]3.[/dim] Sleep (when page loses focus)")
    console.print("[dim]4.[/dim] Wake (when page regains focus)")
    
    while True:
        try:
            choice = typer.prompt("\nSelect category (1-4)")
            
            if choice == "1":
                return "emotion"
            elif choice == "2":
                return "idle_videos"
            elif choice == "3":
                return "sleep"
            elif choice == "4":
                return "wake"
            else:
                console.print("[red]Invalid choice. Please select 1-4.[/red]")
                continue
                
        except typer.Abort:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)


def _prompt_for_emotion_method() -> str:
    """Prompt user to choose emotion determination method."""
    console.print("\n[yellow]How would you like to determine the emotion?[/yellow]")
    console.print("[dim]1.[/dim] Manual selection (choose from existing emotions)")
    console.print("[dim]2.[/dim] AI classification (let AI decide based on filename)")
    
    while True:
        try:
            choice = typer.prompt("\nSelect method (1-2)")
            
            if choice == "1":
                return "manual"
            elif choice == "2":
                return "ai"
            else:
                console.print("[red]Invalid choice. Please select 1 or 2.[/red]")
                continue
                
        except typer.Abort:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)


def _prompt_for_weight() -> int:
    """Prompt user for video weight."""
    while True:
        try:
            weight_str = typer.prompt("\nEnter weight (1-100, default 10)", default="10")
            weight = int(weight_str)
            
            if 1 <= weight <= 100:
                return weight
            else:
                console.print("[red]Weight must be between 1 and 100.[/red]")
                continue
                
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")
            continue
        except typer.Abort:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)


app = typer.Typer(
    name="sage",
    help="Sage - AI Project Context Assistant",
    add_completion=False
)
console = Console()


@app.command()
def run(
    config: Optional[Path] = typer.Option(
        None, 
        "--config", 
        "-c", 
        help="Path to configuration file"
    ),
    debug: bool = typer.Option(
        False, 
        "--debug", 
        "-d", 
        help="Enable debug logging"
    )
):
    """Run Sage AI Project Context Assistant."""
    
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    console.print(Panel.fit(
        "[bold blue]Sage - AI Project Context Assistant[/bold blue]\n"
        "[dim]Monitoring projects and maintaining intelligent context stores[/dim]",
        border_style="blue"
    ))
    
    try:
        sage = SageApplication(config)
        asyncio.run(sage.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Received interrupt signal, shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error running Sage: {e}[/red]")
        sys.exit(1)


@app.command()
def init(
    config_path: Optional[Path] = typer.Option(
        Path("config.yaml"), 
        "--config", 
        "-c", 
        help="Path for new configuration file"
    ),
    force: bool = typer.Option(
        False, 
        "--force", 
        "-f", 
        help="Overwrite existing configuration"
    )
):
    """Initialize Sage configuration files."""
    
    console.print("[blue]Initializing Sage configuration...[/blue]")
    
    # Check if config already exists
    if config_path.exists() and not force:
        console.print(f"[red]Configuration file already exists: {config_path}[/red]")
        console.print("[dim]Use --force to overwrite[/dim]")
        return
    
    try:
        # Create default configuration
        ConfigLoader.create_default_config(config_path)
        console.print(f"[green]✓[/green] Created configuration file: {config_path}")
        
        # Create default .sageignore
        ignore_path = config_path.parent / ".sageignore"
        ConfigLoader.create_default_sageignore(ignore_path)
        console.print(f"[green]✓[/green] Created ignore file: {ignore_path}")
        
        console.print("\n[yellow]Next steps:[/yellow]")
        console.print("1. Edit the configuration file to add your projects")
        console.print("2. Configure AWS credentials for Bedrock")
        console.print("3. Run: sage run")
        
    except Exception as e:
        console.print(f"[red]Error initializing configuration: {e}[/red]")
        sys.exit(1)


@app.command()
def status(
    config: Optional[Path] = typer.Option(
        None, 
        "--config", 
        "-c", 
        help="Path to configuration file"
    )
):
    """Show Sage status and configuration."""
    
    try:
        config_loader = ConfigLoader(config)
        config_data = config_loader.load_config()
        
        # Create status table
        table = Table(title="Sage Configuration Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        # Configuration status
        table.add_row("Configuration", "✓ Loaded", f"From: {config_loader.config_path}")
        
        # Projects
        table.add_row(
            "Projects", 
            f"✓ {len(config_data.projects)}", 
            ", ".join(p.path.name for p in config_data.projects)
        )
        
        # Crews
        table.add_row(
            "Crews", 
            f"✓ {len(config_data.crews)}", 
            ", ".join(config_data.crews.keys())
        )
        
        # AWS Configuration
        table.add_row(
            "AWS Region", 
            "✓ Configured", 
            config_data.aws.region
        )
        
        table.add_row(
            "Bedrock Model", 
            "✓ Configured", 
            config_data.aws.bedrock.get("model", "default")
        )
        
        # UI Configuration
        table.add_row(
            "UI Port", 
            "✓ Configured", 
            str(config_data.ui.browser.get("port", 8080))
        )
        
        console.print(table)
        
        # Check for potential issues
        console.print("\n[yellow]Validation:[/yellow]")
        
        # Check if projects exist
        for project in config_data.projects:
            if project.path.exists():
                console.print(f"[green]✓[/green] Project exists: {project.path}")
            else:
                console.print(f"[red]✗[/red] Project not found: {project.path}")
        
        # Check expressions file
        if config_data.ui.personality.expressions_map.exists():
            console.print(f"[green]✓[/green] Expressions file exists")
        else:
            console.print(f"[red]✗[/red] Expressions file not found: {config_data.ui.personality.expressions_map}")
        
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)


@app.command()
def validate(
    config: Optional[Path] = typer.Option(
        None, 
        "--config", 
        "-c", 
        help="Path to configuration file"
    )
):
    """Validate Sage configuration and dependencies."""
    
    console.print("[blue]Validating Sage configuration...[/blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Load configuration
        task = progress.add_task("Loading configuration...", total=None)
        try:
            config_loader = ConfigLoader(config)
            config_data = config_loader.load_config()
            progress.update(task, description="[green]✓ Configuration loaded[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Configuration error: {e}[/red]")
            return
        
        # Validate projects
        task = progress.add_task("Validating projects...", total=None)
        project_errors = []
        for project in config_data.projects:
            if not project.path.exists():
                project_errors.append(f"Project not found: {project.path}")
        
        if project_errors:
            progress.update(task, description=f"[red]✗ {len(project_errors)} project issues[/red]")
        else:
            progress.update(task, description="[green]✓ All projects valid[/green]")
        
        # Check AWS credentials
        task = progress.add_task("Checking AWS credentials...", total=None)
        try:
            import boto3
            boto3.client('bedrock-runtime', region_name=config_data.aws.region)
            progress.update(task, description="[green]✓ AWS credentials configured[/green]")
        except Exception:
            progress.update(task, description="[yellow]⚠ AWS credentials not configured[/yellow]")
        
        # Check expressions file
        task = progress.add_task("Validating personality system...", total=None)
        if config_data.ui.personality.expressions_map.exists():
            progress.update(task, description="[green]✓ Personality expressions found[/green]")
        else:
            progress.update(task, description="[red]✗ Personality expressions missing[/red]")
        
        # Check dependencies
        task = progress.add_task("Checking dependencies...", total=None)
        missing_deps = []
        required_packages = ['crewai', 'boto3', 'watchdog', 'fastapi', 'uvicorn']
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_deps.append(package)
        
        if missing_deps:
            progress.update(task, description=f"[red]✗ Missing: {', '.join(missing_deps)}[/red]")
        else:
            progress.update(task, description="[green]✓ All dependencies available[/green]")
    
    # Summary
    console.print("\n[bold]Validation Summary:[/bold]")
    if project_errors:
        for error in project_errors:
            console.print(f"[red]• {error}[/red]")
    
    if missing_deps:
        console.print(f"[red]• Missing dependencies: {', '.join(missing_deps)}[/red]")
        console.print("[dim]Install with: pip install -e .[/dim]")
    
    if not project_errors and not missing_deps:
        console.print("[green]✓ Configuration is valid and ready to run![/green]")


@app.command()
def test(
    config: Optional[Path] = typer.Option(
        None, 
        "--config", 
        "-c", 
        help="Path to configuration file"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed test output"
    )
):
    """Test Sage configuration and connectivity."""
    
    console.print("[blue]Testing Sage configuration and connectivity...[/blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Load configuration
        task = progress.add_task("Loading configuration...", total=None)
        try:
            config_loader = ConfigLoader(config)
            config_data = config_loader.load_config()
            progress.update(task, description="[green]✓ Configuration loaded successfully[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Configuration failed: {e}[/red]")
            console.print(f"\n[red]Cannot proceed with tests - configuration error: {e}[/red]")
            sys.exit(1)
        
        # Test AWS Bedrock connectivity
        task = progress.add_task("Testing AWS Bedrock connectivity...", total=None)
        try:
            from .core.bedrock_client import BedrockClient
            
            bedrock_client = BedrockClient(config_data.aws)
            
            # Perform health check
            health_ok = bedrock_client.health_check()
            
            if health_ok:
                progress.update(task, description="[green]✓ Bedrock connectivity successful[/green]")
                
                if verbose:
                    # Get additional details about the connection
                    model_id = config_data.aws.bedrock.get("model", "us.anthropic.claude-sonnet-4-20250514-v1:0")
                    region = config_data.aws.region
                    console.print(f"\n[dim]  Model: {model_id}[/dim]")
                    console.print(f"[dim]  Region: {region}[/dim]")
                    
                    # Test a simple query to verify full functionality
                    try:
                        test_response = bedrock_client.invoke_model(
                            "What is 2+2? Respond with just the number.",
                            max_tokens=10
                        )
                        if verbose:
                            console.print(f"[dim]  Test query response: {test_response.content.strip()}[/dim]")
                            console.print(f"[dim]  Tokens used: {test_response.usage.get('total_tokens', 'unknown')}[/dim]")
                    except Exception as e:
                        console.print(f"[yellow]  Warning: Test query failed: {e}[/yellow]")
            else:
                progress.update(task, description="[red]✗ Bedrock health check failed[/red]")
                
        except Exception as e:
            progress.update(task, description=f"[red]✗ Bedrock connection failed: {e}[/red]")
            
            if verbose:
                console.print(f"\n[red]Bedrock Error Details:[/red]")
                console.print(f"[dim]  {str(e)}[/dim]")
                
                # Provide helpful troubleshooting info
                console.print(f"\n[yellow]Troubleshooting Tips:[/yellow]")
                console.print("• Ensure AWS credentials are configured (try: aws sso login)")
                console.print("• Verify your AWS region has Bedrock access")
                console.print("• Check that your AWS account has Bedrock permissions")
                console.print("• Confirm the model ID is correct and available in your region")
        
        # Test project paths
        task = progress.add_task("Validating project paths...", total=None)
        project_errors = []
        valid_projects = 0
        
        for project in config_data.projects:
            if project.path.exists():
                valid_projects += 1
            else:
                project_errors.append(str(project.path))
        
        if project_errors:
            progress.update(task, description=f"[yellow]⚠ {len(project_errors)} project path issues[/yellow]")
            if verbose:
                console.print(f"\n[yellow]Missing project paths:[/yellow]")
                for path in project_errors:
                    console.print(f"[dim]  • {path}[/dim]")
        else:
            progress.update(task, description=f"[green]✓ All {valid_projects} project paths valid[/green]")
        
        # Test personality system
        task = progress.add_task("Testing personality system...", total=None)
        try:
            expressions_path = config_data.ui.personality.expressions_map
            if expressions_path.exists():
                import json
                with open(expressions_path) as f:
                    expressions = json.load(f)
                
                expression_count = len(expressions.get('expressions', {}))
                progress.update(task, description=f"[green]✓ Personality system ready ({expression_count} expressions)[/green]")
                
                if verbose:
                    console.print(f"\n[dim]  Expressions file: {expressions_path}[/dim]")
                    console.print(f"[dim]  Available expressions: {expression_count}[/dim]")
            else:
                progress.update(task, description="[red]✗ Personality expressions file missing[/red]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Personality system error: {e}[/red]")
        
        # Test dependencies
        task = progress.add_task("Checking dependencies...", total=None)
        missing_deps = []
        available_deps = []
        required_packages = {
            'crewai': 'CrewAI framework',
            'boto3': 'AWS SDK',
            'watchdog': 'File monitoring',
            'fastapi': 'Web server',
            'uvicorn': 'ASGI server',
            'pydantic': 'Data validation',
            'typer': 'CLI framework',
            'rich': 'Terminal formatting'
        }
        
        for package, description in required_packages.items():
            try:
                __import__(package)
                available_deps.append(f"{package} ({description})")
            except ImportError:
                missing_deps.append(f"{package} ({description})")
        
        if missing_deps:
            progress.update(task, description=f"[red]✗ Missing {len(missing_deps)} dependencies[/red]")
            if verbose:
                console.print(f"\n[red]Missing dependencies:[/red]")
                for dep in missing_deps:
                    console.print(f"[dim]  • {dep}[/dim]")
        else:
            progress.update(task, description=f"[green]✓ All {len(available_deps)} dependencies available[/green]")
            if verbose:
                console.print(f"\n[dim]Available dependencies:[/dim]")
                for dep in available_deps:
                    console.print(f"[dim]  • {dep}[/dim]")
    
    # Final summary
    console.print("\n[bold]Test Summary:[/bold]")
    
    # Count issues
    total_issues = len(project_errors) + len(missing_deps)
    if not bedrock_client or not bedrock_client.health_check():
        total_issues += 1
    
    if total_issues == 0:
        console.print("[green]✅ All tests passed! Sage is ready to run.[/green]")
        console.print("\n[dim]You can now run: sage run[/dim]")
    else:
        console.print(f"[yellow]⚠ Found {total_issues} issue(s) that should be addressed:[/yellow]")
        
        if missing_deps:
            console.print("[red]• Install missing dependencies with: pip install -e .[/red]")
        
        if project_errors:
            console.print("[red]• Update project paths in your configuration file[/red]")
        
        try:
            if not bedrock_client.health_check():
                console.print("[red]• Configure AWS credentials and verify Bedrock access[/red]")
        except:
            console.print("[red]• Configure AWS credentials and verify Bedrock access[/red]")


@app.command("add-video")
def add_video(
    video_path: Optional[Path] = typer.Argument(
        None,
        help="Path to the video file to add (optional - if not provided, scans for new videos)"
    ),
    config: Optional[Path] = typer.Option(
        None, 
        "--config", 
        "-c", 
        help="Path to configuration file"
    ),
    emotion: Optional[str] = typer.Option(
        None,
        "--emotion",
        "-e",
        help="Force specific emotion category (skip AI classification)"
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Custom description for the video"
    ),
    use_cases: Optional[str] = typer.Option(
        None,
        "--use-cases",
        "-u",
        help="Comma-separated list of use cases"
    ),
    idle: bool = typer.Option(
        False,
        "--idle",
        help="Add video to idle videos collection instead of emotions"
    ),
    weight: int = typer.Option(
        10,
        "--weight",
        "-w",
        help="Selection weight for the video (1-100, default: 10)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without making changes"
    )
):
    """Add a video to Sage's personality system with AI classification. If no video path is provided, scans for new videos."""
    
    # If no video path provided, scan for new videos
    if video_path is None:
        console.print("[blue]Scanning for new videos in personality/video folder...[/blue]")
        
        # Scan for new videos
        new_videos = _scan_for_new_videos()
        
        if not new_videos:
            console.print("[green]No new videos found! All videos in personality/video are already configured.[/green]")
            return
        
        console.print(f"\n[green]Found {len(new_videos)} new video(s):[/green]")
        for i, video in enumerate(new_videos, 1):
            console.print(f"[dim]{i:2d}.[/dim] {video.name}")
        
        # Process each video
        _process_video_batch(new_videos, config, dry_run)
        return
    
    # Single video mode - validate video file exists
    console.print("[blue]Adding video to Sage's personality system...[/blue]")
    
    if not video_path.exists():
        console.print(f"[red]Error: Video file not found: {video_path}[/red]")
        sys.exit(1)
    
    # Check if it's a video file
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    if video_path.suffix.lower() not in video_extensions:
        console.print(f"[red]Error: File does not appear to be a video: {video_path}[/red]")
        console.print(f"[dim]Supported formats: {', '.join(video_extensions)}[/dim]")
        sys.exit(1)
    
    # Process single video
    _process_single_video(video_path, config, emotion, description, use_cases, idle, weight, dry_run)


def _process_video_batch(new_videos: list, config: Optional[Path], dry_run: bool):
    """Process a batch of new videos interactively."""
    import json
    
    # Load configuration
    try:
        config_loader = ConfigLoader(config)
        config_data = config_loader.load_config()
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)
    
    # Load expressions data
    try:
        expressions_path = Path("personality/expressions-video.json")
        if not expressions_path.exists():
            console.print(f"[red]Error: Expressions file not found: {expressions_path}[/red]")
            sys.exit(1)
        
        with open(expressions_path, 'r') as f:
            expressions_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading expressions file: {e}[/red]")
        sys.exit(1)
    
    # Ask for emotion determination method once
    emotion_method = _prompt_for_emotion_method()
    
    # Initialize bedrock client if using AI
    bedrock_client = None
    if emotion_method == "ai":
        try:
            from .core.bedrock_client import BedrockClient
            bedrock_client = BedrockClient(config_data.aws)
        except Exception as e:
            console.print(f"[red]Error initializing AI client: {e}[/red]")
            console.print("[yellow]Falling back to manual emotion selection...[/yellow]")
            emotion_method = "manual"
    
    changes_made = False
    
    # Process each video
    for i, video_path in enumerate(new_videos, 1):
        console.print(f"\n[bold]Processing video {i}/{len(new_videos)}: {video_path.name}[/bold]")
        
        # Ask user if they want to add this video
        console.print(f"[yellow]Add this video? (y/n/s to skip):[/yellow] ", end="")
        try:
            choice = input().lower().strip()
            if choice in ['s', 'skip']:
                console.print("[dim]Skipped[/dim]")
                continue
            elif choice not in ['y', 'yes', '']:
                console.print("[dim]Skipped[/dim]")
                continue
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Operation cancelled[/yellow]")
            break
        
        # Get video duration
        try:
            duration = _get_video_duration(video_path)
            console.print(f"[green]Duration: {duration}s[/green]")
        except Exception as e:
            console.print(f"[red]Error extracting duration: {e}[/red]")
            console.print("[dim]Skipping this video[/dim]")
            continue
        
        # Determine video category
        category = _prompt_for_video_category()
        
        classified_emotion = None
        if category == "emotion":
            # Determine emotion
            if emotion_method == "ai" and bedrock_client:
                try:
                    classified_emotion = _classify_video_emotion(bedrock_client, video_path)
                    console.print(f"[green]AI classified as: {classified_emotion}[/green]")
                except Exception as e:
                    console.print(f"[red]AI classification failed: {e}[/red]")
                    classified_emotion = _prompt_for_emotion()
            else:
                classified_emotion = _prompt_for_emotion()
        elif category in ["sleep", "wake"]:
            classified_emotion = category
        
        # Get weight
        weight = _prompt_for_weight()
        
        # Create video entry
        video_entry = {
            "location": f"./personality/video/{video_path.name}",
            "duration": duration,
            "weight": weight
        }
        
        # Add to expressions data
        if category == "idle_videos":
            if "idle_videos" not in expressions_data:
                expressions_data["idle_videos"] = {
                    "description": "Videos to be shown randomly when Sage is waiting for interaction",
                    "videos": []
                }
            expressions_data["idle_videos"]["videos"].append(video_entry)
            action = "Added to idle videos collection"
        elif category in ["sleep", "wake"] or classified_emotion in expressions_data["emotions"]:
            # Add to existing emotion category
            target_emotion = classified_emotion or category
            expressions_data["emotions"][target_emotion]["videos"].append(video_entry)
            action = f"Added to '{target_emotion}' emotion"
        else:
            # Create new emotion category
            new_emotion_data = {
                "videos": [video_entry],
                "description": f"Custom {classified_emotion} expression",
                "use_cases": [f"expressing {classified_emotion}"]
            }
            expressions_data["emotions"][classified_emotion] = new_emotion_data
            action = f"Created new '{classified_emotion}' emotion category"
        
        console.print(f"[green]✓ {action}[/green]")
        changes_made = True
    
    # Save changes if any were made
    if changes_made and not dry_run:
        try:
            with open(expressions_path, 'w') as f:
                json.dump(expressions_data, f, indent=2)
            console.print(f"\n[green]✅ Successfully updated expressions file![/green]")
            console.print(f"[dim]Updated: {expressions_path}[/dim]")
        except Exception as e:
            console.print(f"\n[red]Error saving expressions file: {e}[/red]")
            sys.exit(1)
    elif changes_made and dry_run:
        console.print(f"\n[yellow]This was a dry run - no changes were saved[/yellow]")
    elif not changes_made:
        console.print(f"\n[dim]No videos were added[/dim]")


def _process_single_video(video_path: Path, config: Optional[Path], emotion: Optional[str], 
                         description: Optional[str], use_cases: Optional[str], idle: bool, 
                         weight: int, dry_run: bool):
    """Process a single video (original functionality)."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Load configuration
        task = progress.add_task("Loading configuration...", total=None)
        try:
            config_loader = ConfigLoader(config)
            config_data = config_loader.load_config()
            progress.update(task, description="[green]✓ Configuration loaded[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Configuration error: {e}[/red]")
            sys.exit(1)
        
        # Get video duration using ffmpeg
        task = progress.add_task("Extracting video duration...", total=None)
        try:
            duration = _get_video_duration(video_path)
            progress.update(task, description=f"[green]✓ Duration: {duration}s[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Duration extraction failed: {e}[/red]")
            sys.exit(1)
        
        # Skip emotion classification if adding to idle videos
        if idle:
            classified_emotion = None
            progress.add_task("Adding to idle videos collection", total=None)
        elif emotion:
            classified_emotion = emotion
            progress.add_task(f"Using specified emotion: {emotion}", total=None)
        else:
            task = progress.add_task("Classifying video emotion with AI...", total=None)
            try:
                from .core.bedrock_client import BedrockClient
                bedrock_client = BedrockClient(config_data.aws)
                
                classified_emotion = _classify_video_emotion(bedrock_client, video_path)
                progress.update(task, description=f"[green]✓ Classified as: {classified_emotion}[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]✗ AI classification failed: {e}[/red]")
                console.print("[yellow]Falling back to manual classification...[/yellow]")
                classified_emotion = _prompt_for_emotion()
        
        # Load current expressions
        task = progress.add_task("Loading personality expressions...", total=None)
        try:
            expressions_path = Path("personality/expressions-video.json")
            if not expressions_path.exists():
                console.print(f"[red]Error: Expressions file not found: {expressions_path}[/red]")
                sys.exit(1)
            
            import json
            with open(expressions_path, 'r') as f:
                expressions_data = json.load(f)
            
            progress.update(task, description="[green]✓ Expressions loaded[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Failed to load expressions: {e}[/red]")
            sys.exit(1)
        
        # Prepare video entry
        task = progress.add_task("Preparing video entry...", total=None)
        
        # Copy video to personality/video directory if not already there
        target_dir = Path("personality/video")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if video_path.parent != target_dir:
            target_path = target_dir / video_path.name
            if target_path.exists():
                console.print(f"[yellow]Warning: Video already exists in personality directory: {target_path}[/yellow]")
                overwrite = typer.confirm("Overwrite existing video?")
                if not overwrite:
                    console.print("[yellow]Operation cancelled[/yellow]")
                    sys.exit(0)
            
            if not dry_run:
                import shutil
                shutil.copy2(video_path, target_path)
                console.print(f"[green]✓ Copied video to: {target_path}[/green]")
            else:
                console.print(f"[dim]Would copy video to: {target_path}[/dim]")
            
            video_location = f"./personality/video/{video_path.name}"
        else:
            video_location = f"./personality/video/{video_path.name}"
        
        video_entry = {
            "location": video_location,
            "duration": duration,
            "weight": weight
        }
        
        progress.update(task, description="[green]✓ Video entry prepared[/green]")
        
        # Add to expressions data
        task = progress.add_task("Updating expressions data...", total=None)
        
        if idle:
            # Add to idle videos collection
            if "idle_videos" not in expressions_data:
                expressions_data["idle_videos"] = {
                    "description": "Videos to be shown randomly when Sage is waiting for interaction",
                    "videos": []
                }
            expressions_data["idle_videos"]["videos"].append(video_entry)
            action = "Added to idle videos collection"
        elif classified_emotion in expressions_data["emotions"]:
            # Add to existing emotion
            expressions_data["emotions"][classified_emotion]["videos"].append(video_entry)
            action = f"Added to existing '{classified_emotion}' emotion"
        else:
            # Create new emotion category
            new_emotion_data = {
                "videos": [video_entry],
                "description": description or f"Custom {classified_emotion} expression",
                "use_cases": use_cases.split(",") if use_cases else [f"expressing {classified_emotion}"]
            }
            expressions_data["emotions"][classified_emotion] = new_emotion_data
            action = f"Created new '{classified_emotion}' emotion category"
        
        progress.update(task, description=f"[green]✓ {action}[/green]")
    
    # Show summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]• Video:[/green] {video_path}")
    console.print(f"[green]• Duration:[/green] {duration}s")
    console.print(f"[green]• Weight:[/green] {weight}")
    if idle:
        console.print(f"[green]• Type:[/green] Idle video")
    else:
        console.print(f"[green]• Emotion:[/green] {classified_emotion}")
    console.print(f"[green]• Action:[/green] {action}")
    
    if dry_run:
        console.print(f"\n[yellow]This was a dry run - no changes were made[/yellow]")
        return
    
    # Save updated expressions
    try:
        with open(expressions_path, 'w') as f:
            json.dump(expressions_data, f, indent=2)
        console.print(f"\n[green]✅ Successfully updated expressions file![/green]")
        console.print(f"[dim]Updated: {expressions_path}[/dim]")
    except Exception as e:
        console.print(f"\n[red]Error saving expressions file: {e}[/red]")
        sys.exit(1)


@app.command()
def version():
    """Show Sage version information."""
    from . import __version__, __author__
    
    console.print(Panel.fit(
        f"[bold blue]Sage v{__version__}[/bold blue]\n"
        f"[dim]AI Project Context Assistant[/dim]\n"
        f"[dim]By: {__author__}[/dim]",
        border_style="blue"
    ))


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
