#!/usr/bin/env python3
"""
Ask-Intercom CLI - Phase 0 Prototype
Usage: ask-intercom "What are the top customer complaints this month?"
"""

import argparse
import asyncio
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

from .config import Config
from .logger import (
    log_query_result,
    log_query_start,
    set_request_context,
    setup_logging,
)
from .models import SessionState
from .query_processor import QueryProcessor


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Ask natural language questions about your Intercom conversations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ask-intercom "What are the top customer complaints this month?"
  ask-intercom "How many support tickets were opened last week?"
  ask-intercom "What issues did john@company.com report recently?" --debug
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",  # Make query optional
        help="Natural language question about your Intercom conversations",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument(
        "--structured-logs",
        action="store_true",
        help="Output structured JSON logs instead of human-readable format",
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Override the OpenAI model (default: from config)",
    )

    parser.add_argument(
        "--max-conversations",
        type=int,
        default=None,
        help="Maximum number of conversations to analyze (default: 1000)",
    )

    parser.add_argument(
        "--no-limit",
        action="store_true",
        help="Analyze all conversations found (no limit)",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode with persistent session",
    )

    return parser


async def check_large_dataset(
    query: str,
    processor: "QueryProcessor",
    console: Console,
    interactive: bool = False,
) -> bool:
    """Check if query will analyze many conversations and ask for confirmation."""
    try:
        conversation_count, timeframe = await processor.count_conversations_for_query(
            query
        )

        if conversation_count <= 100:
            # Small dataset, proceed without warning
            return True

        # Calculate estimates
        estimated_time = processor._estimate_processing_time(conversation_count)
        estimated_cost = processor._estimate_processing_cost(conversation_count)

        # Show warning
        console.print("\n⚠️  [yellow]Large dataset detected![/yellow]")
        console.print(
            f"📊 Found [bold]{conversation_count}[/bold] conversations in {timeframe.description}"
        )
        console.print(
            f"⏱️  Estimated processing time: [bold]{estimated_time:.1f} seconds[/bold] ({estimated_time / 60:.1f} minutes)"
        )
        console.print(f"💰 Estimated cost: [bold]${estimated_cost:.2f}[/bold]")

        if not interactive:
            # Non-interactive mode: proceed with warning
            console.print(
                "\n🤖 [dim]Proceeding automatically in non-interactive mode...[/dim]"
            )
            return True

        # Interactive mode: ask for confirmation
        console.print("\n❓ Do you want to continue? [Y/n]", end=" ")
        response = console.input().strip().lower()

        if response in ["", "y", "yes"]:
            console.print("✅ [green]Proceeding with analysis...[/green]")
            return True
        else:
            console.print("❌ [red]Analysis cancelled by user[/red]")
            return False

    except Exception as e:
        # If count fails, proceed anyway but log warning
        console.print(f"\n⚠️  [yellow]Could not estimate dataset size: {e}[/yellow]")
        console.print("Proceeding with analysis...")
        return True


async def run_query(
    query: str,
    config: Config,
    console: Console,
    request_id: str = None,
    session: SessionState = None,
    interactive: bool = False,
) -> bool:
    """Execute a single query and display results."""
    start_time = datetime.now()

    # Set request context if provided
    if request_id:
        set_request_context(request_id)
        log_query_start(request_id, query)

    try:
        # Show different status based on whether it's a follow-up
        if session and session.last_conversations:
            # Check if it's a follow-up question
            processor = QueryProcessor(config)
            if processor._is_followup_question(query):
                status_text = (
                    "[bold green]Analyzing cached conversations for follow-up..."
                )
            else:
                status_text = "[bold green]Fetching new conversations and analyzing..."
        else:
            status_text = (
                "[bold green]Interpreting timeframe and fetching conversations..."
            )

        # Initialize processor first
        if "processor" not in locals():
            processor = QueryProcessor(config)

        # Check for large datasets and get user confirmation
        should_proceed = await check_large_dataset(
            query, processor, console, interactive
        )
        if not should_proceed:
            return False

        # Show initial status
        console.print(f"\n{status_text}", style="bold green")
        console.print("⏳ Processing...", end="", style="dim")
        sys.stdout.flush()

        result = await processor.process_query(query, session)

        # Clear the processing indicator
        console.print("\r✅ Complete!   ", style="bold green")

        duration = (datetime.now() - start_time).total_seconds()

        # Show comprehensive timing breakdown
        console.print("\n⏱️  [bold]Performance Summary[/bold]")
        console.print(f"   • [cyan]Total Request Time:[/cyan] {duration:.2f}s")

        # Add timing details if available
        if hasattr(result, "processing_time_ms"):
            console.print("   • [cyan]Processing Phases:[/cyan]")
            if hasattr(result, "fetch_time_ms"):
                console.print(f"     - Data Fetch: {result.fetch_time_ms:.0f}ms")
            if hasattr(result, "analysis_time_ms"):
                console.print(f"     - AI Analysis: {result.analysis_time_ms:.0f}ms")
            console.print(f"     - Total Backend: {result.processing_time_ms:.0f}ms")

        console.print(
            f"   • [cyan]Conversations Analyzed:[/cyan] {result.conversation_count}"
        )
        if hasattr(result, "cost_info") and result.cost_info:
            console.print(
                f"   • [cyan]Estimated Cost:[/cyan] ${result.cost_info.estimated_cost_usd:.3f}"
            )
            console.print(
                f"   • [cyan]Tokens Used:[/cyan] {result.cost_info.tokens_used:,}"
            )
            console.print(f"   • [cyan]Model:[/cyan] {result.cost_info.model_used}")

        # Performance indicators
        fetch_speed = "⚡ FastIntercomMCP" if duration < 10 else "🐌 Slower backend"
        console.print(f"   • [cyan]Backend:[/cyan] {fetch_speed}")

        if duration < 5:
            perf_emoji = "🚀"
        elif duration < 15:
            perf_emoji = "⚡"
        else:
            perf_emoji = "⏳"
        console.print(
            f"   • [cyan]Performance:[/cyan] {perf_emoji} {duration:.2f}s end-to-end"
        )

        # Log success
        if request_id:
            log_query_result(
                request_id,
                True,
                duration,
                result.conversation_count,
                result.cost_info.tokens_used,
                result.cost_info.estimated_cost_usd,
            )

        # Determine query type and session info
        is_followup = False
        query_type_label = ""

        if session and session.last_conversations:
            processor = (
                QueryProcessor(config) if "processor" not in locals() else processor
            )
            is_followup = processor._is_followup_question(query)
            if is_followup:
                query_type_label = " (Follow-up)"

        # Display results with rich formatting
        if not request_id:  # Full output for single query mode
            console.print("\n" + "=" * 60)
            console.print(f"[bold blue]Query:[/bold blue] {query}{query_type_label}")
            console.print("=" * 60)
        else:  # Interactive mode - show session info
            session_info = f"[bold blue]Session {request_id}:[/bold blue] {query}"
            if is_followup:
                session_info += " [dim yellow](Follow-up)[/dim yellow]"
            console.print(f"\n{session_info}")
            console.print("─" * 60)

        # Main results
        console.print(
            Panel(
                result.summary,
                title="[bold green]Analysis Results[/bold green]",
                border_style="green",
            )
        )

        # Metadata
        metadata = f"""
[dim]Analyzed {result.conversation_count} conversations
Time range: {result.time_range.description}
Model: {result.cost_info.model_used}
Tokens: {result.cost_info.tokens_used:,}
Estimated cost: ${result.cost_info.estimated_cost_usd:.3f}[/dim]
        """
        console.print(metadata.strip())

        return True

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()

        # Log failure
        if request_id:
            log_query_result(request_id, False, duration, error=str(e))

        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if config.debug:
            raise

        return False


async def interactive_mode(config: Config, console: Console) -> None:
    """Run in interactive mode with persistent session."""
    # Generate session ID
    import uuid

    session_id = str(uuid.uuid4())[:8]

    console.print(
        Panel(
            f"[bold]Ask-Intercom Interactive Mode[/bold]\n\n"
            f"Session ID: [cyan]{session_id}[/cyan]\n\n"
            "Enter your queries to analyze Intercom conversations.\n"
            "Ask follow-up questions like 'tell me more about verification issues'.\n"
            "Type 'quit' to exit.",
            border_style="blue",
        )
    )

    message_id = 1
    session = SessionState()  # Create session state for memory

    while True:
        try:
            # Prompt for query
            query = console.input(f"\n[{session_id}:{message_id:03d}] Query: ").strip()

            if not query:
                continue

            if query.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            # Process query
            console.print("Processing... ", end="")
            start_time = datetime.now()

            # Create request ID with session and message info
            request_id = f"{session_id}:{message_id:03d}"

            success = await run_query(
                query, config, console, request_id, session, interactive=True
            )

            if success:
                duration = (datetime.now() - start_time).total_seconds()
                console.print(f"[dim]({duration:.1f}s)[/dim]")

            message_id += 1

        except KeyboardInterrupt:
            console.print("\n[yellow]Query cancelled[/yellow]")
            continue
        except EOFError:
            console.print("\n[yellow]Goodbye![/yellow]")
            break


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup
    setup_logging(
        args.debug, structured=args.structured_logs, interactive=args.interactive
    )
    console = Console()

    try:
        # Load configuration
        config = Config.from_env()
        if args.model:
            config.model = args.model
        if args.max_conversations:
            config.max_conversations = args.max_conversations
        if args.no_limit:
            config.max_conversations = 10000  # Effectively no limit
        if args.debug:
            config.debug = True

        config.validate()

        # Run in appropriate mode
        if args.interactive:
            asyncio.run(interactive_mode(config, console))
        else:
            # Single query mode
            if not args.query:
                parser.error("Query is required in non-interactive mode")
            asyncio.run(run_query(args.query, config, console, interactive=False))

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Fatal error:[/bold red] {str(e)}")
        sys.exit(1)


def interactive_main() -> None:
    """Entry point for interactive mode."""
    import sys

    # Override sys.argv to force interactive mode
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0], "--interactive"]

    try:
        main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()
