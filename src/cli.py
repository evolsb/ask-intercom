#!/usr/bin/env python3
"""
Ask-Intercom CLI - Phase 0 Prototype
Usage: ask-intercom "What are the top customer complaints this month?"
"""

import argparse
import asyncio
import logging
import sys

from rich.console import Console
from rich.panel import Panel

from .config import Config
from .query_processor import QueryProcessor


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


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
        "query", help="Natural language question about your Intercom conversations"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

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

    return parser


async def run_query(query: str, config: Config, console: Console) -> None:
    """Execute a single query and display results."""
    try:
        with console.status("[bold green]Processing your query..."):
            processor = QueryProcessor(config)
            result = await processor.process_query(query)

        # Display results with rich formatting
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

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if config.debug:
            raise


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup
    setup_logging(args.debug)
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

        # Run the query
        asyncio.run(run_query(args.query, config, console))

    except KeyboardInterrupt:
        console.print("\n[yellow]Query cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Fatal error:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
