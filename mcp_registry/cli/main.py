"""
Main CLI application using Typer.

Rich command-line interface for MCP Registry management.
"""

import asyncio
from typing import Optional, List
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ..core.config import get_settings
from .commands import server, discovery, database, config as config_cmd, proxy

# Create the main Typer app
app = typer.Typer(
    name="mcp-registry",
    help="🚀 MCP Registry - Enterprise Model Context Protocol Server Management",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=False,
)

# Add command groups
app.add_typer(server.app, name="server", help="🖥️  Server management commands")
app.add_typer(discovery.app, name="discover", help="🔍 Capability discovery commands")
app.add_typer(database.app, name="db", help="🗄️  Database management commands")
app.add_typer(config_cmd.app, name="config", help="⚙️  Configuration management")
app.add_typer(proxy.app, name="proxy", help="🔄 MCP Proxy server commands")

console = Console()


@app.command()
def version():
    """Show version information."""
    from .. import __version__, __author__
    
    panel = Panel.fit(
        f"[bold blue]MCP Registry[/bold blue]\n"
        f"Version: [green]{__version__}[/green]\n"
        f"Author: [yellow]{__author__}[/yellow]",
        title="📦 Version Info",
        border_style="blue"
    )
    console.print(panel)


@app.command()
def status():
    """Show system status and health."""
    settings = get_settings()
    
    # Create status table
    table = Table(title="🏥 System Status", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Add rows
    table.add_row("Application", "✅ Running", f"Version {settings.app_version}")
    table.add_row("Database", "✅ Connected", settings.database_url)
    table.add_row("API Server", "🔄 Configurable", f"{settings.api_host}:{settings.api_port}")
    table.add_row("Debug Mode", "🐛 Enabled" if settings.debug else "🔒 Disabled", "")
    
    console.print(table)


@app.command()
def start(
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Host to bind to"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port to bind to"),
    workers: Optional[int] = typer.Option(None, "--workers", "-w", help="Number of worker processes"),
    reload: Optional[bool] = typer.Option(None, "--reload", "-r", help="Enable auto-reload"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    log_level: Optional[str] = typer.Option(None, "--log-level", "-l", help="Log level"),
):
    """🚀 Start the MCP Registry API server."""
    
    from ..core.config import get_settings
    
    # Get settings and override with CLI arguments
    settings = get_settings()
    
    # Use CLI args or fall back to settings
    final_host = host or settings.host
    final_port = port or settings.port
    final_workers = workers or settings.workers
    final_reload = reload if reload is not None else (settings.reload or debug)
    final_log_level = log_level or ("debug" if debug else "info")
    
    # Workers and reload are mutually exclusive
    if final_reload and final_workers > 1:
        console.print("[yellow]⚠️  Warning: Disabling workers when reload is enabled[/yellow]")
        final_workers = 1
    
    with console.status("[bold green]Starting MCP Registry server..."):
        try:
            import uvicorn
            
            # Show startup info
            startup_panel = Panel.fit(
                f"[bold green]🚀 Starting MCP Registry[/bold green]\n\n"
                f"[cyan]Host:[/cyan] {final_host}\n"
                f"[cyan]Port:[/cyan] {final_port}\n"
                f"[cyan]Workers:[/cyan] {final_workers}\n"
                f"[cyan]Reload:[/cyan] {final_reload}\n"
                f"[cyan]Debug:[/cyan] {debug or settings.debug}\n"
                f"[cyan]Log Level:[/cyan] {final_log_level}\n\n"
                f"[yellow]API Docs:[/yellow] http://{final_host}:{final_port}/docs\n"
                f"[yellow]Health Check:[/yellow] http://{final_host}:{final_port}/health",
                title="🌟 Server Configuration",
                border_style="green"
            )
            console.print(startup_panel)
            
            # Start the server with proper app reference for reload
            if final_reload:
                # Use string reference for reload support
                uvicorn.run(
                    "mcp_registry.api.app:create_app",
                    host=final_host,
                    port=final_port,
                    reload=True,
                    log_level=final_log_level,
                    access_log=True,
                    factory=True
                )
            else:
                # Use app instance for production
                from ..api.app import create_app
                uvicorn.run(
                    create_app(),
                    host=final_host,
                    port=final_port,
                    workers=final_workers,
                    log_level=final_log_level,
                    access_log=True
                )
            
        except ImportError:
            console.print("[red]❌ Error: uvicorn not installed. Install with: pip install uvicorn[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]❌ Error starting server: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def init(
    database_url: Optional[str] = typer.Option(None, "--db", help="Database URL"),
    force: bool = typer.Option(False, "--force", help="Force initialization"),
):
    """🏗️  Initialize MCP Registry (database, config, etc.)."""
    
    async def _init():
        from ..database.base import init_db
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Initialize database
            task1 = progress.add_task("Initializing database...", total=None)
            try:
                await init_db()
                progress.update(task1, description="✅ Database initialized")
            except Exception as e:
                progress.update(task1, description=f"❌ Database initialization failed: {e}")
                raise typer.Exit(1)
            
            # Create config file if it doesn't exist
            task2 = progress.add_task("Creating configuration...", total=None)
            config_path = Path(".env")
            if not config_path.exists() or force:
                settings = get_settings()
                config_content = f"""# MCP Registry Configuration
MCP_DATABASE_URL={database_url or settings.database_url}
MCP_API_HOST={settings.api_host}
MCP_API_PORT={settings.api_port}
MCP_SECRET_KEY={settings.secret_key}
MCP_LOG_LEVEL={settings.log_level}
MCP_DEBUG={str(settings.debug).lower()}
"""
                config_path.write_text(config_content)
                progress.update(task2, description="✅ Configuration created")
            else:
                progress.update(task2, description="⚠️  Configuration exists (use --force to overwrite)")
    
    try:
        asyncio.run(_init())
        
        success_panel = Panel.fit(
            "[bold green]🎉 MCP Registry initialized successfully![/bold green]\n\n"
            "[cyan]Next steps:[/cyan]\n"
            "1. [yellow]mcp-registry start[/yellow] - Start the API server\n"
            "2. [yellow]mcp-registry server register[/yellow] - Register your first server\n"
            "3. [yellow]mcp-registry discover run[/yellow] - Discover capabilities\n\n"
            "[dim]Visit http://localhost:8080/docs for API documentation[/dim]",
            title="✨ Initialization Complete",
            border_style="green"
        )
        console.print(success_panel)
        
    except Exception as e:
        console.print(f"[red]❌ Initialization failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()