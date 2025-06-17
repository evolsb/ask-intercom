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
        help="Maximum number of conversations to analyze",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode with persistent session",
    )

    return parser


async def run_query(
    query: str, config: Config, console: Console, request_id: str = None
) -> bool:
    """Execute a single query and display results."""
    start_time = datetime.now()

    # Set request context if provided
    if request_id:
        set_request_context(request_id)
        log_query_start(request_id, query)

    try:
        with console.status("[bold green]Processing your query..."):
            processor = QueryProcessor(config)
            result = await processor.process_query(query)

        duration = (datetime.now() - start_time).total_seconds()

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

        # Display results with rich formatting
        if not request_id:  # Full output for single query mode
            console.print("\n" + "=" * 60)
            console.print(f"[bold blue]Query:[/bold blue] {query}")
            console.print("=" * 60)

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
    console.print(
        Panel(
            "[bold]Ask-Intercom Interactive Mode[/bold]\n\n"
            "Enter your queries to analyze Intercom conversations.\n"
            "Type 'quit' to exit.",
            border_style="blue",
        )
    )

    request_id = 1

    while True:
        try:
            # Prompt for query
            query = console.input(f"\n[{request_id:03d}] Query: ").strip()

            if not query:
                continue

            if query.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            # Process query
            console.print("Processing... ", end="")
            start_time = datetime.now()

            success = await run_query(query, config, console, f"{request_id:03d}")

            if success:
                duration = (datetime.now() - start_time).total_seconds()
                console.print(f"[dim]({duration:.1f}s)[/dim]")

            request_id += 1

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
            asyncio.run(run_query(args.query, config, console))

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
