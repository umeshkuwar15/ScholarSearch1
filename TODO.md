# Task: COMMENT NIKAL DE - Remove All Comments & Delete Useless Files

## Goal
Remove all comments (inline `#`, docstrings `"""..."""`, HTML `<!-- -->`, JS `//`, Dockerfile/YAML comments) from the codebase and delete useless debug/temp files.

## Steps
- [x] Step 0: Analyze the codebase and identify all files with comments
- [x] Step 1: Create TODO.md tracking file
- [x] Step 2: Delete useless files (`_*.py`, `_*.txt`, `umesh_output.txt`, `scholarsearch_export.csv`, `__pycache__/`, `.pytest_cache/`)
- [x] Step 3: Remove comments from `app.py`
- [x] Step 4: Remove comments from `main.py`, `setup.py`
- [x] Step 5: Remove comments from `scholar_search/` package files (`__init__.py`, `__main__.py`, `cli.py`, `config.py`, `exporters.py`, `models.py`, `view_data.py`)
- [x] Step 6: Remove comments from `scholar_search/db/` files (`__init__.py`, `database.py`, `models.py`, `crud.py`)
- [x] Step 7: Remove comments from `scholar_search/searchers/` files (all 7 files)
- [x] Step 8: Remove comments from templates (`index.html`, `dashboard.html`)
- [x] Step 9: Remove comments from `Dockerfile`, `docker-compose.yml`
- [x] Step 10: Remove comments from `tests/` files
- [x] Step 11: Verify - run `pytest tests/ -v` and `python -c "import app"` - must stay green

