
import argparse
import io
import sys
from typing import Optional

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from . import __version__
from .models import SearchResult
from .searchers import (
    ArxivSearcher,
    CrossrefSearcher,
    OpenAlexSearcher,
    PubmedSearcher,
    SemanticScholarSearcher,
)
from .exporters import get_exporter

console = Console()

SOURCE_COLORS = {
    "arXiv": "blue",
    "CrossRef": "green",
    "OpenAlex": "magenta",
    "PubMed": "cyan",
    "SemanticScholar": "yellow",
}

SEARCHER_MAP = {
    "arxiv": ("arXiv", ArxivSearcher),
    "crossref": ("CrossRef", CrossrefSearcher),
    "openalex": ("OpenAlex", OpenAlexSearcher),
    "pubmed": ("PubMed", PubmedSearcher),
    "semanticscholar": ("SemanticScholar", SemanticScholarSearcher),
}

def create_parser() -> argparse.ArgumentParser:
    source_choices = list(SEARCHER_MAP.keys()) + ["all"]

    parser = argparse.ArgumentParser(
        prog="scholarsearch",
        description="ScholarSearch - Search academic literature across multiple sources",
        epilog=(
            "Examples:\n"
            '  scholarsearch "machine learning"\n'
            '  scholarsearch -a "Albert Einstein" --source crossref\n'
            '  scholarsearch --user register --username myuser --email my@email.com\n'
            '  scholarsearch --user info --username myuser'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="Search query (keywords, title, or topic)",
    )
    parser.add_argument(
        "-a", "--author",
        help="Search by author name",
    )
    parser.add_argument(
        "-s", "--source",
        choices=source_choices,
        default="all",
        help="Source to search (default: all)",
    )
    parser.add_argument(
        "-n", "--num-results",
        type=int,
        default=10,
        help="Number of results to fetch per source (default: 10)",
    )
    parser.add_argument(
        "-p", "--page",
        type=int,
        default=1,
        help="Page number for pagination (default: 1)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path for export",
    )
    parser.add_argument(
        "--export",
        choices=["json", "csv", "text"],
        default="json",
        help="Export format (default: json)",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"ScholarSearch v{__version__}",
    )

    parser.add_argument(
        "--user",
        choices=["register", "login", "info", "list"],
        help="User management commands",
    )
    parser.add_argument("--username", help="Username for user management")
    parser.add_argument("--email", help="Email address for registration")
    parser.add_argument("--password", help="Password (will prompt if not provided)")
    parser.add_argument("--full-name", help="Full name for registration", default="")
    parser.add_argument("--institution", help="Institution for registration", default="")
    return parser

def _get_searchers(source: str):
    searchers = []
    if source == "all":
        for display_name, cls in SEARCHER_MAP.values():
            searchers.append((display_name, cls()))
    else:
        display_name, cls = SEARCHER_MAP[source]
        searchers.append((display_name, cls()))
    return searchers

def search_source(
    searcher,
    query: str = "",
    author: str = "",
    max_results: int = 10,
    page: int = 1,
) -> SearchResult:
    if query:
        return searcher.search(query, max_results, page)
    return searcher.search_by_author(author, max_results)

def display_results(result: SearchResult):
    if result.error:
        console.print(f"[bold red]X Error from {result.source}:[/] {result.error}")
        return

    if not result.articles:
        console.print(f"[yellow]No results from {result.source}.[/]")
        return

    color = SOURCE_COLORS.get(result.source, "white")

    table = Table(
        title=f"[bold {color}]{result.source}[/] - Results",
        box=box.ROUNDED,
        header_style=f"bold {color}",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold", ratio=3)
    table.add_column("Authors", ratio=2)
    table.add_column("Year", justify="center", width=6)
    table.add_column("Citations", justify="center", width=9)
    table.add_column("Source", width=16)

    for i, article in enumerate(result.articles, 1):
        title = article.title
        if len(title) > 80:
            title = title[:77] + "..."

        authors = article.short_authors
        if len(authors) > 40:
            authors = authors[:37] + "..."

        year = str(article.year) if article.year else "N/A"
        citations = str(article.citation_count) if article.citation_count else "-"

        table.add_row(
            str(i),
            title,
            authors,
            year,
            citations,
            result.source,
        )

    console.print(table)

    total = result.total_results or len(result.articles)
    console.print(
        f"[dim]Showing {len(result.articles)} of {total} results from {result.source}[/]\n"
    )

def export_results(
    articles: list,
    output_path: str,
    format: str = "json",
) -> Optional[str]:
    try:
        exporter = get_exporter(format)
        result_path = exporter.export(articles, output_path)
        console.print(f"[bold green]V[/] Results exported to: [cyan]{result_path}[/]")
        return result_path
    except Exception as e:
        console.print(f"[bold red]X Export failed:[/] {str(e)}")
        return None

def handle_user_command(args):
    from .db import init_db, get_session, create_user, get_user_by_username, get_user_by_email

    init_db()
    session = get_session()

    try:
        if args.user == "register":
            password = args.password
            if not password:
                import getpass
                password = getpass.getpass("Password: ")

            if not args.username or not args.email:
                console.print("[bold red]X[/] --username and --email are required for registration")
                return

            if get_user_by_username(session, args.username):
                console.print(f"[bold red]X[/] Username '[cyan]{args.username}[/]' already exists")
                return

            if get_user_by_email(session, args.email):
                console.print(f"[bold red]X[/] Email '[cyan]{args.email}[/]' already exists")
                return

            user = create_user(
                session=session,
                username=args.username,
                email=args.email,
                password=password,
                full_name=args.full_name,
                institution=args.institution,
            )
            console.print(f"[bold green]V[/] User '[cyan]{user.username}[/]' registered successfully (ID: {user.id})")

        elif args.user == "login":
            password = args.password
            if not password:
                import getpass
                password = getpass.getpass("Password: ")

            if not args.username:
                console.print("[bold red]X[/] --username is required for login")
                return

            from .db import authenticate_user
            user = authenticate_user(session, args.username, password)
            if user:
                console.print(f"[bold green]V[/] Authentication successful for '[cyan]{user.username}[/]'")
                console.print(f"  Name: [white]{user.full_name or 'N/A'}[/]")
                console.print(f"  Email: [white]{user.email}[/]")
            else:
                console.print(f"[bold red]X[/] Invalid username or password")

        elif args.user == "info":
            if not args.username:
                console.print("[bold red]X[/] --username is required for info")
                return

            user = get_user_by_username(session, args.username)
            if not user:
                console.print(f"[bold red]X[/] User '[cyan]{args.username}[/]' not found")
                return

            table = Table(title=f"User: {user.username}", box=box.ROUNDED)
            table.add_column("Field", style="bold cyan")
            table.add_column("Value")
            table.add_row("ID", str(user.id))
            table.add_row("Username", user.username)
            table.add_row("Email", user.email)
            table.add_row("Full Name", user.full_name or "-")
            table.add_row("Institution", user.institution or "-")
            table.add_row("Active", str(user.is_active))
            table.add_row("Created", str(user.created_at)[:19] if user.created_at else "N/A")
            console.print(table)

        elif args.user == "list":
            from .db import User as UserModel
            users = session.query(UserModel).all()
            if not users:
                console.print("[yellow]No users registered yet.[/]")
                return

            table = Table(title=f"Users ({len(users)})", box=box.ROUNDED)
            table.add_column("ID", style="dim")
            table.add_column("Username", style="cyan")
            table.add_column("Email")
            table.add_column("Name")
            table.add_column("Institution")
            table.add_column("Created")
            for u in users:
                table.add_row(
                    str(u.id),
                    u.username,
                    u.email,
                    u.full_name or "-",
                    u.institution or "-",
                    str(u.created_at)[:10] if u.created_at else "N/A",
                )
            console.print(table)

    finally:
        session.close()

def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.user:
        handle_user_command(args)
        return

    if not args.query and not args.author:
        parser.print_help()
        console.print("\n[yellow]Please provide a search query or use -a for author search.[/]")
        sys.exit(1)

    console.print(f"[bold cyan]ScholarSearch v{__version__}[/]\n")

    searchers = _get_searchers(args.source)
    all_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=False,
    ) as progress:
        for name, searcher in searchers:
            task = progress.add_task(f"[cyan]Searching {name}...", total=None)
            result = search_source(
                searcher,
                query=args.query or "",
                author=args.author or "",
                max_results=args.num_results,
                page=args.page,
            )
            progress.update(task, completed=True)
            all_results.append(result)

    console.print()
    for result in all_results:
        display_results(result)

    if args.output:
        all_articles = []
        for r in all_results:
            all_articles.extend(r.articles)
        if all_articles:
            export_results(all_articles, args.output, args.export)
        else:
            console.print("[yellow]No articles to export.[/]")

    total_articles = sum(len(r.articles) for r in all_results)
    console.print(f"[bold]Total:[/] {total_articles} articles found across {len(searchers)} source(s)")

if __name__ == "__main__":
    main()
