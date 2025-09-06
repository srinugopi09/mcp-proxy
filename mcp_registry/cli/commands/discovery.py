"""
Capability discovery CLI commands.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ...core.database import get_session_maker
from ...services.discovery import DiscoveryService
from ...models.capability import CapabilityType

app = typer.Typer(help="Capability discovery commands")
console = Console()


@app.command("scan")
def scan_capabilities(
    server_id: Optional[str] = typer.Option(None, "--server-id", "-s", help="Specific server ID to scan"),
    all_servers: bool = typer.Option(False, "--all", "-a", help="Scan all registered servers"),
):
    """🔍 Scan and discover capabilities from MCP servers."""
    
    async def _scan():
        session_maker = get_session_maker()
        async with session_maker() as session:
            service = DiscoveryService(session)
            
            if server_id:
                # Scan specific server
                with console.status(f"[bold green]Discovering capabilities for server {server_id}..."):
                    try:
                        capabilities = await service.discover_server_capabilities(server_id)
                        
                        success_panel = Panel.fit(
                            f"[bold green]✅ Discovery completed![/bold green]\n\n"
                            f"[cyan]Server ID:[/cyan] {server_id}\n"
                            f"[cyan]Capabilities Found:[/cyan] {len(capabilities)}\n\n"
                            f"[dim]Use 'mcp-registry discover list' to view details[/dim]",
                            title="🎉 Capability Discovery",
                            border_style="green"
                        )
                        console.print(success_panel)
                        
                        # Show summary
                        if capabilities:
                            table = Table(title="Discovered Capabilities")
                            table.add_column("Name", style="cyan")
                            table.add_column("Type", style="magenta")
                            table.add_column("Description", style="white")
                            
                            for cap in capabilities[:10]:  # Show first 10
                                table.add_row(
                                    cap.get("name", "Unknown"),
                                    cap.get("type", "Unknown"),
                                    cap.get("description", "No description")[:50] + "..." if len(cap.get("description", "")) > 50 else cap.get("description", "")
                                )
                            
                            console.print(table)
                            
                            if len(capabilities) > 10:
                                rprint(f"[dim]... and {len(capabilities) - 10} more capabilities[/dim]")
                        
                    except Exception as e:
                        console.print(f"[red]❌ Discovery failed: {e}[/red]")
                        raise typer.Exit(1)
            
            elif all_servers:
                # Scan all servers
                with console.status("[bold green]Scanning all registered servers..."):
                    try:
                        results = await service.scan_all_servers()
                        
                        # Show results
                        results_panel = Panel.fit(
                            f"[bold green]✅ Scan completed![/bold green]\n\n"
                            f"[cyan]Total Servers:[/cyan] {results['total_servers']}\n"
                            f"[green]Successful:[/green] {results['successful']}\n"
                            f"[red]Failed:[/red] {results['failed']}",
                            title="📊 Scan Results",
                            border_style="green"
                        )
                        console.print(results_panel)
                        
                        # Show detailed results
                        if results['results']:
                            table = Table(title="Server Scan Results")
                            table.add_column("Server", style="cyan")
                            table.add_column("Status", style="white")
                            table.add_column("Capabilities", style="magenta")
                            table.add_column("Details", style="dim")
                            
                            for result in results['results']:
                                status_color = "green" if result['status'] == 'success' else "red"
                                status_icon = "✅" if result['status'] == 'success' else "❌"
                                
                                details = ""
                                if result['status'] == 'success':
                                    details = f"{result['capabilities_count']} found"
                                else:
                                    details = result.get('error', 'Unknown error')[:30] + "..."
                                
                                table.add_row(
                                    result['server_name'],
                                    f"[{status_color}]{status_icon} {result['status']}[/{status_color}]",
                                    str(result.get('capabilities_count', 0)) if result['status'] == 'success' else "0",
                                    details
                                )
                            
                            console.print(table)
                        
                    except Exception as e:
                        console.print(f"[red]❌ Scan failed: {e}[/red]")
                        raise typer.Exit(1)
            
            else:
                console.print("[yellow]Please specify --server-id or --all[/yellow]")
                raise typer.Exit(1)
    
    asyncio.run(_scan())


@app.command("list")
def list_capabilities(
    server_id: Optional[str] = typer.Option(None, "--server-id", "-s", help="Filter by server ID"),
    capability_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by capability type"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of results"),
):
    """📋 List discovered capabilities."""
    
    async def _list():
        session_maker = get_session_maker()
        async with session_maker() as session:
            service = DiscoveryService(session)
            
            try:
                capabilities = await service.list_capabilities(limit=limit)
                
                if not capabilities:
                    console.print("[yellow]No capabilities found. Run 'mcp-registry discover scan --all' first.[/yellow]")
                    return
                
                # Filter by server_id if specified
                if server_id:
                    capabilities = [cap for cap in capabilities if cap.get('server_id') == server_id]
                
                # Filter by type if specified
                if capability_type:
                    capabilities = [cap for cap in capabilities if cap.get('type') == capability_type]
                
                if not capabilities:
                    console.print(f"[yellow]No capabilities found matching the filters.[/yellow]")
                    return
                
                # Display results
                table = Table(title=f"Discovered Capabilities ({len(capabilities)} found)")
                table.add_column("Name", style="cyan")
                table.add_column("Type", style="magenta")
                table.add_column("Server", style="green")
                table.add_column("Description", style="white")
                
                for cap in capabilities:
                    description = cap.get("description", "No description")
                    if len(description) > 60:
                        description = description[:60] + "..."
                    
                    table.add_row(
                        cap.get("name", "Unknown"),
                        cap.get("type", "Unknown"),
                        cap.get("server_id", "Unknown")[:8] + "...",
                        description
                    )
                
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]❌ Failed to list capabilities: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_list())


@app.command("run")
def run_discovery(
    server_id: str = typer.Option(..., "--server-id", "-s", help="Server ID to discover"),
    force: bool = typer.Option(False, "--force", "-f", help="Force refresh even if recently discovered"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Discovery timeout in seconds"),
):
    """🔍 Run capability discovery for a server."""
    
    async def _discover():
        async for session in get_session():
            server_repo = ServerRepository(session)
            
            try:
                # Get server info
                server = await server_repo.get_by_id(server_id)
                if not server:
                    console.print(f"[red]❌ Server '{server_id}' not found[/red]")
                    raise typer.Exit(1)
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    
                    task = progress.add_task(
                        f"Discovering capabilities for '{server.name}'...", 
                        total=None
                    )
                    
                    # TODO: Implement actual discovery service call
                    # For now, simulate discovery
                    await asyncio.sleep(2)
                    
                    progress.update(task, description="✅ Discovery completed")
                
                # Show results
                result_panel = Panel.fit(
                    f"[bold green]🎉 Discovery completed for '{server.name}'[/bold green]\n\n"
                    f"[cyan]Server:[/cyan] {server.name}\n"
                    f"[cyan]URL:[/cyan] {server.url}\n"
                    f"[cyan]Status:[/cyan] Discovery successful\n"
                    f"[cyan]Capabilities Found:[/cyan] 0 (simulated)\n\n"
                    f"[dim]Use 'mcp-registry discover list --server-id {server_id}' to view capabilities[/dim]",
                    title="🔍 Discovery Results",
                    border_style="green"
                )
                console.print(result_panel)
                
            except Exception as e:
                console.print(f"[red]❌ Discovery failed: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_discover())


@app.command("list")
def list_capabilities(
    server_id: Optional[str] = typer.Option(None, "--server-id", "-s", help="Filter by server ID"),
    capability_type: Optional[CapabilityType] = typer.Option(None, "--type", "-t", help="Filter by capability type"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int = typer.Option(50, "--limit", "-l", help="Limit results"),
):
    """📋 List discovered capabilities."""
    
    async def _list():
        async for session in get_session():
            cap_repo = CapabilityRepository(session)
            
            try:
                if server_id:
                    # Get capabilities for specific server
                    capabilities = await cap_repo.get_server_capabilities(
                        server_id, capability_type
                    )
                    total = len(capabilities)
                else:
                    # Search all capabilities
                    capabilities, total = await cap_repo.search_capabilities(
                        query=query,
                        capability_type=capability_type,
                        limit=limit
                    )
                
                if not capabilities:
                    console.print("[yellow]No capabilities found.[/yellow]")
                    return
                
                # Create table
                table = Table(title=f"🔧 Discovered Capabilities ({total})")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("Type", style="green")
                table.add_column("Server", style="blue")
                table.add_column("Description", style="yellow")
                table.add_column("Discovered", style="dim")
                
                for cap in capabilities:
                    # Get server name (would need to join in real implementation)
                    server_name = cap.server_id[:8] + "..."  # Simplified
                    
                    table.add_row(
                        cap.name,
                        cap.type,
                        server_name,
                        (cap.description or "")[:50] + ("..." if cap.description and len(cap.description) > 50 else ""),
                        cap.discovered_at.strftime("%Y-%m-%d %H:%M") if cap.discovered_at else "N/A"
                    )
                
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]❌ Failed to list capabilities: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_list())


@app.command("search")
def search_capabilities(
    query: str = typer.Argument(..., help="Search query"),
    capability_type: Optional[CapabilityType] = typer.Option(None, "--type", "-t", help="Filter by capability type"),
    limit: int = typer.Option(50, "--limit", "-l", help="Limit results"),
):
    """🔎 Search capabilities across all servers."""
    
    async def _search():
        async for session in get_session():
            cap_repo = CapabilityRepository(session)
            
            try:
                capabilities, total = await cap_repo.search_capabilities(
                    query=query,
                    capability_type=capability_type,
                    limit=limit
                )
                
                if not capabilities:
                    console.print(f"[yellow]No capabilities found matching '{query}'.[/yellow]")
                    return
                
                # Show search results
                console.print(f"[green]Found {total} capabilities matching '{query}'[/green]\n")
                
                for cap in capabilities:
                    capability_panel = Panel.fit(
                        f"[bold cyan]{cap.name}[/bold cyan] ({cap.type})\n"
                        f"{cap.description or 'No description'}\n\n"
                        f"[dim]Server: {cap.server_id[:8]}... | Discovered: {cap.discovered_at.strftime('%Y-%m-%d %H:%M') if cap.discovered_at else 'N/A'}[/dim]",
                        border_style="blue"
                    )
                    console.print(capability_panel)
                
            except Exception as e:
                console.print(f"[red]❌ Search failed: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_search())


@app.command("stats")
def show_stats():
    """📊 Show capability discovery statistics."""
    
    async def _stats():
        async for session in get_session():
            cap_repo = CapabilityRepository(session)
            server_repo = ServerRepository(session)
            
            try:
                cap_stats = await cap_repo.get_capability_stats()
                server_stats = await server_repo.get_stats()
                
                # Create stats table
                table = Table(title="📊 Discovery Statistics")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green", justify="right")
                
                table.add_row("Total Servers", str(server_stats["total_servers"]))
                table.add_row("Total Capabilities", str(cap_stats["total_capabilities"]))
                table.add_row("Servers with Capabilities", str(cap_stats["servers_with_capabilities"]))
                
                # Add capability type breakdown
                if cap_stats["capability_counts"]:
                    table.add_row("", "")  # Separator
                    table.add_row("[bold]Capability Types[/bold]", "")
                    for cap_type, count in cap_stats["capability_counts"].items():
                        table.add_row(f"  {cap_type.title()}", str(count))
                
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]❌ Failed to get stats: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_stats())