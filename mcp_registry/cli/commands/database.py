"""
Database management CLI commands.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import text

from ...core.database import init_database_sync, get_engine, create_tables
from ...core.config import get_settings

app = typer.Typer(help="Database management commands")
console = Console()


@app.command("init")
def init_database(
    force: bool = typer.Option(False, "--force", "-f", help="Force initialization"),
):
    """🏗️  Initialize the database."""
    
    async def _init():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Initializing database...", total=None)
            
            try:
                init_database_sync()
                await create_tables()
                progress.update(task, description="✅ Database initialized successfully")
                
                settings = get_settings()
                success_panel = Panel.fit(
                    f"[bold green]🎉 Database initialized![/bold green]\n\n"
                    f"[cyan]Database URL:[/cyan] {settings.database_url}\n"
                    f"[cyan]Tables Created:[/cyan] servers, capabilities, capability_discoveries\n\n"
                    f"[dim]The database is ready for use.[/dim]",
                    title="✨ Database Ready",
                    border_style="green"
                )
                console.print(success_panel)
                
            except Exception as e:
                progress.update(task, description=f"❌ Database initialization failed")
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_init())


@app.command("migrate")
def migrate_database(
    message: str = typer.Option("Auto migration", "--message", "-m", help="Migration message"),
    auto: bool = typer.Option(False, "--auto", help="Auto-generate migration"),
):
    """🔄 Create and run database migrations."""
    
    try:
        import subprocess
        
        if auto:
            # Auto-generate migration
            console.print("[yellow]Generating migration...[/yellow]")
            result = subprocess.run([
                "alembic", "revision", "--autogenerate", "-m", message
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ Migration generation failed: {result.stderr}[/red]")
                raise typer.Exit(1)
            
            console.print("[green]✅ Migration generated[/green]")
        
        # Run migrations
        console.print("[yellow]Running migrations...[/yellow]")
        result = subprocess.run([
            "alembic", "upgrade", "head"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[red]❌ Migration failed: {result.stderr}[/red]")
            raise typer.Exit(1)
        
        console.print("[green]✅ Migrations completed successfully[/green]")
        
    except ImportError:
        console.print("[red]❌ Alembic not installed. Install with: pip install alembic[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Alembic command not found. Make sure it's installed and in PATH[/red]")
        raise typer.Exit(1)


@app.command("status")
def database_status():
    """📊 Show database status and information."""
    
    async def _status():
        settings = get_settings()
        
        try:
            # Initialize database first
            init_database_sync()
            
            # Test database connection
            engine = get_engine()
            async with engine.connect() as conn:
                # Get database info
                if "sqlite" in settings.database_url:
                    result = await conn.execute(text("SELECT sqlite_version()"))
                    db_version = result.scalar()
                    db_type = "SQLite"
                else:
                    db_version = "Unknown"
                    db_type = "Other"
                
                # Check if tables exist
                if "sqlite" in settings.database_url:
                    result = await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    tables = [row[0] for row in result.fetchall()]
                else:
                    tables = []
            
            # Create status panel
            status_text = f"""[bold cyan]Database Status[/bold cyan]

[yellow]Connection:[/yellow]
  URL: {settings.database_url}
  Type: {db_type}
  Version: {db_version}
  Status: ✅ Connected

[yellow]Tables:[/yellow]"""
            
            if tables:
                for table in sorted(tables):
                    status_text += f"\n  ✅ {table}"
            else:
                status_text += "\n  ❌ No tables found (run 'mcp-registry db init')"
            
            panel = Panel.fit(status_text, title="🗄️  Database Information", border_style="blue")
            console.print(panel)
            
        except Exception as e:
            error_panel = Panel.fit(
                f"[bold red]❌ Database connection failed[/bold red]\n\n"
                f"[yellow]Error:[/yellow] {e}\n"
                f"[yellow]URL:[/yellow] {settings.database_url}\n\n"
                f"[dim]Make sure the database is accessible and initialized.[/dim]",
                title="🚨 Database Error",
                border_style="red"
            )
            console.print(error_panel)
            raise typer.Exit(1)
    
    asyncio.run(_status())


@app.command("reset")
def reset_database(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """🗑️  Reset the database (WARNING: Deletes all data)."""
    
    if not force:
        confirmed = typer.confirm(
            "⚠️  This will delete ALL data in the database. Are you sure?"
        )
        if not confirmed:
            console.print("[yellow]Reset cancelled.[/yellow]")
            return
    
    async def _reset():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Resetting database...", total=None)
            
            try:
                from ...database.base import Base
                
                engine = get_engine()
                async with engine.begin() as conn:
                    # Drop all tables
                    await conn.run_sync(Base.metadata.drop_all)
                    progress.update(task, description="🗑️  Dropped all tables")
                    
                    # Recreate tables
                    await conn.run_sync(Base.metadata.create_all)
                    progress.update(task, description="✅ Database reset completed")
                
                warning_panel = Panel.fit(
                    f"[bold yellow]⚠️  Database has been reset![/bold yellow]\n\n"
                    f"[red]All data has been deleted.[/red]\n"
                    f"[green]Fresh database schema created.[/green]\n\n"
                    f"[dim]You can now register new servers and discover capabilities.[/dim]",
                    title="🔄 Reset Complete",
                    border_style="yellow"
                )
                console.print(warning_panel)
                
            except Exception as e:
                progress.update(task, description="❌ Database reset failed")
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_reset())