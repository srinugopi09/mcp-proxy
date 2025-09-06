"""
Server management CLI commands.
"""

import asyncio
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from ...core.database import get_session_maker
from ...services.registry import RegistryService
from ...models.server import ServerCreate, ServerUpdate, ServerStatus, TransportType
from ...core.exceptions import ServerNotFoundError, ServerAlreadyExistsError

app = typer.Typer(help="Server management commands")
console = Console()


@app.command("register")
def register_server(
    name: str = typer.Option(..., "--name", "-n", help="Server name"),
    url: str = typer.Option(..., "--url", "-u", help="Server URL (must end with /mcp)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Server description"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    transport: TransportType = typer.Option(TransportType.AUTO, "--transport", help="Transport type"),
):
    """📝 Register a new MCP server."""
    
    async def _register():
        session_maker = get_session_maker()
        async with session_maker() as session:
            service = RegistryService(session)
            
            # Parse tags
            tag_list = []
            if tags:
                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            
            # Create server data
            server_data = ServerCreate(
                name=name,
                url=url,
                description=description,
                tags=tag_list,
                transport=transport
            )
            
            try:
                server = await service.create_server(server_data)
                
                # Show success
                success_panel = Panel.fit(
                    f"[bold green]✅ Server registered successfully![/bold green]\n\n"
                    f"[cyan]ID:[/cyan] {server['id']}\n"
                    f"[cyan]Name:[/cyan] {server['name']}\n"
                    f"[cyan]URL:[/cyan] {server['url']}\n"
                    f"[cyan]Transport:[/cyan] {server['transport']}\n"
                    f"[cyan]Status:[/cyan] {server['status']}",
                    title="🎉 Registration Complete",
                    border_style="green"
                )
                console.print(success_panel)
                
                # Suggest next steps
                rprint("\n[dim]Next steps:[/dim]")
                rprint(f"[yellow]mcp-registry discover scan --server-id {server['id']}[/yellow] - Discover capabilities")
                rprint(f"[yellow]mcp-registry server show {server['id']}[/yellow] - View server details")
                
            except ServerAlreadyExistsError as e:
                console.print(f"[red]❌ Error: {e.message}[/red]")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]❌ Registration failed: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_register())


@app.command("list")
def list_servers(
    status: Optional[ServerStatus] = typer.Option(None, "--status", "-s", help="Filter by status"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Filter by tags"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit results"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json)"),
):
    """📋 List registered servers."""
    
    async def _list():
        async for session in get_session():
            repo = ServerRepository(session)
            
            # Parse tags
            tag_list = None
            if tags:
                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            
            try:
                servers = await repo.list_servers(
                    status=status,
                    tags=tag_list,
                    limit=limit
                )
                
                if not servers:
                    console.print("[yellow]No servers found.[/yellow]")
                    return
                
                if format == "json":
                    import json
                    server_data = []
                    for server in servers:
                        server_dict = {
                            "id": server.id,
                            "name": server.name,
                            "url": server.url,
                            "status": server.status,
                            "transport": server.transport,
                            "created_at": server.created_at.isoformat(),
                        }
                        server_data.append(server_dict)
                    
                    console.print(json.dumps(server_data, indent=2))
                else:
                    # Table format
                    table = Table(title=f"🖥️  Registered Servers ({len(servers)})")
                    table.add_column("Name", style="cyan", no_wrap=True)
                    table.add_column("Status", style="green")
                    table.add_column("Transport", style="blue")
                    table.add_column("URL", style="yellow")
                    table.add_column("Created", style="dim")
                    
                    for server in servers:
                        status_icon = {
                            "healthy": "✅",
                            "unhealthy": "❌", 
                            "unknown": "❓",
                            "error": "🚨"
                        }.get(server.status, "❓")
                        
                        table.add_row(
                            server.name,
                            f"{status_icon} {server.status}",
                            server.transport,
                            server.url,
                            server.created_at.strftime("%Y-%m-%d %H:%M")
                        )
                    
                    console.print(table)
                
            except Exception as e:
                console.print(f"[red]❌ Failed to list servers: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_list())


@app.command("show")
def show_server(
    server_id: str = typer.Argument(..., help="Server ID"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed information"),
):
    """🔍 Show detailed information about a server."""
    
    async def _show():
        async for session in get_session():
            repo = ServerRepository(session)
            
            try:
                server = await repo.get_by_id(server_id)
                if not server:
                    console.print(f"[red]❌ Server '{server_id}' not found[/red]")
                    raise typer.Exit(1)
                
                # Basic information
                info_text = f"""[bold cyan]Server Information[/bold cyan]

[yellow]Basic Details:[/yellow]
  ID: {server.id}
  Name: {server.name}
  URL: {server.url}
  Description: {server.description or 'N/A'}
  Transport: {server.transport}
  Status: {server.status}
  Created: {server.created_at}
  Updated: {server.updated_at}
"""
                
                if detailed:
                    # Add server-introspected information
                    if server.server_name or server.server_version:
                        info_text += f"""
[yellow]Server Information:[/yellow]
  Server Name: {server.server_name or 'N/A'}
  Server Version: {server.server_version or 'N/A'}
  Protocol Version: {server.protocol_version or 'N/A'}
"""
                    
                    # Add performance metrics
                    if server.total_discoveries > 0:
                        success_rate = (server.successful_discoveries / server.total_discoveries) * 100
                        info_text += f"""
[yellow]Performance Metrics:[/yellow]
  Total Discoveries: {server.total_discoveries}
  Successful: {server.successful_discoveries}
  Success Rate: {success_rate:.1f}%
  Avg Response Time: {server.avg_response_time_ms}ms
  Last Ping: {server.last_ping_time or 'N/A'}
"""
                
                panel = Panel.fit(info_text, title="🖥️  Server Details", border_style="blue")
                console.print(panel)
                
            except Exception as e:
                console.print(f"[red]❌ Failed to show server: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_show())


@app.command("update")
def update_server(
    server_id: str = typer.Argument(..., help="Server ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New server name"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="New server URL"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    transport: Optional[TransportType] = typer.Option(None, "--transport", help="New transport type"),
):
    """✏️  Update server information."""
    
    async def _update():
        async for session in get_session():
            repo = ServerRepository(session)
            
            # Build update data
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if url is not None:
                update_data["url"] = url
            if description is not None:
                update_data["description"] = description
            if transport is not None:
                update_data["transport"] = transport
            
            if not update_data:
                console.print("[yellow]No updates specified.[/yellow]")
                return
            
            try:
                server_update = ServerUpdate(**update_data)
                server = await repo.update(server_id, server_update)
                
                console.print(f"[green]✅ Server '{server.name}' updated successfully![/green]")
                
            except ServerNotFoundError as e:
                console.print(f"[red]❌ Error: {e.message}[/red]")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]❌ Update failed: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_update())


@app.command("delete")
def delete_server(
    server_id: str = typer.Argument(..., help="Server ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """🗑️  Delete a server."""
    
    async def _delete():
        async for session in get_session():
            repo = ServerRepository(session)
            
            try:
                # Get server info first
                server = await repo.get_by_id(server_id)
                if not server:
                    console.print(f"[red]❌ Server '{server_id}' not found[/red]")
                    raise typer.Exit(1)
                
                # Confirm deletion
                if not force:
                    confirmed = Confirm.ask(
                        f"Are you sure you want to delete server '{server.name}' ({server.url})?"
                    )
                    if not confirmed:
                        console.print("[yellow]Deletion cancelled.[/yellow]")
                        return
                
                # Delete server
                success = await repo.delete(server_id)
                if success:
                    console.print(f"[green]✅ Server '{server.name}' deleted successfully![/green]")
                else:
                    console.print("[red]❌ Failed to delete server[/red]")
                    raise typer.Exit(1)
                
            except Exception as e:
                console.print(f"[red]❌ Deletion failed: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_delete())