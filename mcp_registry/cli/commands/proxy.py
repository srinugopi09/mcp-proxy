"""
MCP Proxy CLI commands for running proxy servers.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

from ...core.database import get_session_maker
from ...services.proxy import ProxyService
from ...core.exceptions import ServerNotFoundError

app = typer.Typer(help="MCP Proxy commands")
console = Console()


@app.command("run")
def run_proxy(
    server_id: str = typer.Argument(..., help="Server ID to proxy"),
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport type (stdio, http, sse)"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port for HTTP/SSE transport"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Proxy server name"),
):
    """🔄 Run a FastMCP proxy server for a registered MCP server."""
    
    # Validate arguments
    if transport in ["http", "sse"] and port is None:
        console.print("[red]❌ Error: --port is required for HTTP/SSE transport[/red]")
        raise typer.Exit(1)
    
    async def _run_proxy():
        session_maker = get_session_maker()
        async with session_maker() as session:
            service = ProxyService(session)
            
            try:
                # Show startup info
                startup_panel = Panel.fit(
                    f"[bold green]🔄 Starting MCP Proxy Server[/bold green]\n\n"
                    f"[cyan]Server ID:[/cyan] {server_id}\n"
                    f"[cyan]Transport:[/cyan] {transport}\n"
                    f"[cyan]Port:[/cyan] {port if port else 'N/A (stdio)'}\n"
                    f"[cyan]Name:[/cyan] {name or 'Auto-generated'}\n\n"
                    f"[yellow]Connecting to registered MCP server...[/yellow]",
                    title="🚀 Proxy Server Startup",
                    border_style="green"
                )
                console.print(startup_panel)
                
                # Run the proxy server
                await service.run_proxy_server(
                    server_id=server_id,
                    transport=transport,
                    port=port,
                    proxy_name=name
                )
                
            except ServerNotFoundError:
                console.print(f"[red]❌ Server '{server_id}' not found in registry[/red]")
                console.print("[yellow]Use 'mcp-registry server list' to see available servers[/yellow]")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]❌ Proxy server failed: {e}[/red]")
                raise typer.Exit(1)
    
    try:
        asyncio.run(_run_proxy())
    except KeyboardInterrupt:
        console.print("\n[yellow]Proxy server stopped by user[/yellow]")


@app.command("test")
def test_connection(
    server_id: str = typer.Argument(..., help="Server ID to test"),
):
    """🧪 Test connection to a registered MCP server."""
    
    async def _test():
        session_maker = get_session_maker()
        async with session_maker() as session:
            service = ProxyService(session)
            
            try:
                with console.status(f"[bold green]Testing connection to server {server_id}..."):
                    proxy_server = await service.create_proxy_server(server_id)
                    
                    success_panel = Panel.fit(
                        f"[bold green]✅ Connection successful![/bold green]\n\n"
                        f"[cyan]Server ID:[/cyan] {server_id}\n"
                        f"[cyan]Proxy Name:[/cyan] {proxy_server.name}\n"
                        f"[cyan]Version:[/cyan] {proxy_server.version}\n\n"
                        f"[dim]Ready to run proxy server[/dim]",
                        title="🎉 Connection Test",
                        border_style="green"
                    )
                    console.print(success_panel)
                
            except ServerNotFoundError:
                console.print(f"[red]❌ Server '{server_id}' not found in registry[/red]")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]❌ Connection test failed: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_test())


@app.command("list")
def list_proxy_servers():
    """📋 List available servers that can be proxied."""
    
    async def _list():
        session_maker = get_session_maker()
        async with session_maker() as session:
            from ...services.registry import RegistryService
            registry_service = RegistryService(session)
            
            try:
                servers = await registry_service.list_servers()
                
                if not servers:
                    console.print("[yellow]No servers registered. Use 'mcp-registry server register' to add servers.[/yellow]")
                    return
                
                console.print(f"\n[bold cyan]Available Servers for Proxying ({len(servers)} found)[/bold cyan]\n")
                
                for server in servers:
                    # Show server info with proxy command
                    server_panel = Panel.fit(
                        f"[bold white]{server['name']}[/bold white]\n"
                        f"[cyan]ID:[/cyan] {server['id']}\n"
                        f"[cyan]URL:[/cyan] {server['url']}\n"
                        f"[cyan]Transport:[/cyan] {server.get('transport', 'auto')}\n"
                        f"[cyan]Status:[/cyan] {server['status']}\n\n"
                        f"[yellow]Proxy Commands:[/yellow]\n"
                        f"[dim]mcp-registry proxy run {server['id']}[/dim]\n"
                        f"[dim]mcp-registry proxy run {server['id']} --transport http --port 8001[/dim]",
                        title=f"🖥️  {server['name']}",
                        border_style="blue"
                    )
                    console.print(server_panel)
                    console.print()
                
            except Exception as e:
                console.print(f"[red]❌ Failed to list servers: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_list())