# 🔍 ScholarSearch

A powerful tool for searching academic literature across **5 scholarly APIs**: arXiv, CrossRef, OpenAlex, PubMed, and Semantic Scholar.

## Features

- 🌐 **5 search sources** - arXiv, CrossRef, OpenAlex, PubMed, Semantic Scholar
- 👤 **Author search** - Find papers by specific authors
- 📄 **Export results** - JSON, CSV, or plain text
- 🎨 **Beautiful CLI** - Rich, colorized terminal output with tables
- 🌐 **Web Interface** - Modern FastAPI web UI with dark theme
- 📊 **Citation data** - Citation counts from CrossRef, OpenAlex, Semantic Scholar
- 🔑 **No API keys required** - All sources are freely accessible
- 🐳 **Docker support** - Containerized deployment with Docker Compose
- ✅ **Test suite** - Comprehensive tests with pytest

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## MySQL setup

The application uses MySQL Server through PyMySQL. Create the database in MySQL Workbench:

```sql
CREATE DATABASE IF NOT EXISTS scholarsearch_db;
```

Copy `.env.example` to `.env` and set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`,
`MYSQL_PASSWORD`, and `MYSQL_DATABASE`. The application checks that MySQL and the
database are reachable at startup, then creates missing tables from the SQLAlchemy
models. It does not import the old `scholarsearch.db` file.

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
# Edit .env with your MySQL credentials, then:
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

In Workbench, refresh the `scholarsearch_db` schema after starting the app to see
its tables. For Docker Compose, `MYSQL_HOST` defaults to `host.docker.internal`;
set the other `MYSQL_*` values in the environment or Compose `.env` file.

## CLI Usage

```bash
python main.py "machine learning"
python main.py -a "Albert Einstein"
python main.py "quantum computing" -n 20 -o results.json
```

### Options

| Option | Description |
|--------|-------------|
| `query` | Search query (keywords, title, topic) |
| `-a, --author` | Search by author name |
| `-s, --source` | Source: `arxiv`, `crossref`, `openalex`, `pubmed`, `semanticscholar`, or `all` |
| `-n, --num-results` | Results per source (default: 10) |
| `-p, --page` | Page number for pagination |
| `-o, --output` | Output file path for export |
| `--export` | Format: `json`, `csv`, or `text` |
| `-v, --version` | Show version |

### Examples

```bash
# Search all sources
python main.py "deep learning"

# Specific source + author
python main.py -a "Yoshua Bengio" -s semanticscholar

# Export to CSV
python main.py "reinforcement learning" --export csv -o papers.csv

# PubMed search
python main.py "CRISPR gene editing" -s pubmed
```

## 🎨 Web Interface

```bash
python app.py
# → http://127.0.0.1:8000
```

### REST API

```bash
# Search
curl "http://127.0.0.1:8000/api/search?q=machine+learning"

# Author search
curl "http://127.0.0.1:8000/api/search?author=Andrew+Ng"

# Export CSV
curl "http://127.0.0.1:8000/api/search?q=quantum&export=csv" -o results.csv

# Health check
curl "http://127.0.0.1:8000/health"
```

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up --build

# Or build manually
docker build -t scholarsearch .
docker run -p 8000:8000 scholarsearch
```

## ✅ Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
scholarsearch/
├── main.py                 # CLI entry point
├── app.py                  # Web interface (FastAPI)
├── setup.py                # Package setup
├── Dockerfile              # Docker config
├── docker-compose.yml      # Docker Compose
├── pytest.ini              # Test config
├── requirements.txt        # Dependencies
├── README.md               # Documentation
├── templates/
│   └── index.html          # Web UI template
├── tests/
│   ├── test_models.py      # Model tests
│   ├── test_exporters.py   # Export tests
│   ├── test_searchers.py   # Searcher tests
│   └── test_cli.py         # CLI tests
└── scholar_search/
    ├── __init__.py
    ├── __main__.py
    ├── cli.py              # CLI interface
    ├── config.py           # Configuration
    ├── models.py           # Data models
    ├── exporters.py        # Export functionality
    └── searchers/
        ├── __init__.py
        ├── base_searcher.py
        ├── arxiv_searcher.py
        ├── crossref_searcher.py
        ├── openalex_searcher.py
        ├── pubmed_searcher.py
        └── semantic_scholar_searcher.py
```

## 📊 Supported Sources

| Source | Type | API Key | Rate Limit |
|--------|------|---------|------------|
| **arXiv** | Preprints | None | None |
| **CrossRef** | Published research | None | 50/s |
| **OpenAlex** | Comprehensive catalog | None | 10/s |
| **PubMed** | Biomedical literature | Optional | 3/s (no key), 10/s (with key) |
| **Semantic Scholar** | Academic papers | None | 100/min |

## Requirements

- Python 3.8+
- requests, rich, fastapi, uvicorn, jinja2
