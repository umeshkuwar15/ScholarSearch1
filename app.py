import hashlib
import hmac
import json
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
import uvicorn

from scholar_search.searchers import (
    ArxivSearcher,
    CrossrefSearcher,
    OpenAlexSearcher,
    PubmedSearcher,
    SemanticScholarSearcher,
)
from scholar_search.exporters import get_exporter
from scholar_search.db import (
    init_db,
    get_session,
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_username,
    get_user_by_email,
    save_search_history,
    get_user_search_history,
    add_favorite,
    remove_favorite,
    get_user_favorites,
    add_feedback,
    get_paper_feedback,
    save_or_get_paper,
    User,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="ScholarSearch",
    description="Web interface for searching academic literature across arXiv, CrossRef, OpenAlex, PubMed, and Semantic Scholar",
    version="1.0.0",
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).resolve().parent

SESSION_SECRET = "scholarsearch-session-secret-change-in-production-2024"
SESSION_COOKIE = "session_id"
SESSION_MAX_AGE = 7 * 24 * 3600
SESSION_STORE = {}
SESSION_STORE_LOCK = threading.Lock()

def _sign(value: str) -> str:
    return hmac.new(
        SESSION_SECRET.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
    ).hexdigest()

def _make_signed_session_id() -> str:
    session_id = secrets.token_urlsafe(32)
    return f"{session_id}.{_sign(session_id)}"

def _parse_signed_session_id(value: str) -> Optional[str]:
    if not value or "." not in value:
        return None
    session_id, signature = value.rsplit(".", 1)
    expected = _sign(session_id)
    if not hmac.compare_digest(signature, expected):
        return None
    return session_id

def get_session_user(request: Request) -> Optional[User]:
    cookie_value = request.cookies.get(SESSION_COOKIE)
    session_id = _parse_signed_session_id(cookie_value) if cookie_value else None
    if session_id is None:
        return None
    with SESSION_STORE_LOCK:
        user_id = SESSION_STORE.get(session_id)
    if user_id is None:
        return None
    session = get_session()
    try:
        user = get_user_by_id(session, user_id)
        return user
    finally:
        session.close()

def set_session_user(response, user_id: int):
    with SESSION_STORE_LOCK:
        raw_session_id = secrets.token_urlsafe(32)
        SESSION_STORE[raw_session_id] = user_id
    signed_value = f"{raw_session_id}.{_sign(raw_session_id)}"
    response.set_cookie(
        key=SESSION_COOKIE,
        value=signed_value,
        httponly=True,
        max_age=SESSION_MAX_AGE,
        samesite="lax",
        path="/",
    )

def clear_session(request: Request, response):
    cookie_value = request.cookies.get(SESSION_COOKIE)
    session_id = _parse_signed_session_id(cookie_value) if cookie_value else None
    if session_id is not None:
        with SESSION_STORE_LOCK:
            SESSION_STORE.pop(session_id, None)
    response.delete_cookie(key=SESSION_COOKIE, path="/")

def require_login(request: Request):
    user = get_session_user(request)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user

jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    auto_reload=True,
)

def fromjson_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value if isinstance(value, list) else []

jinja_env.filters["fromjson"] = fromjson_filter

static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

SEARCHER_MAP = {
    "arxiv": ("arXiv", ArxivSearcher),
    "crossref": ("CrossRef", CrossrefSearcher),
    "openalex": ("OpenAlex", OpenAlexSearcher),
    "pubmed": ("PubMed", PubmedSearcher),
    "semanticscholar": ("SemanticScholar", SemanticScholarSearcher),
}

def get_searchers(sources: str):
    searchers = []
    sources_list = [s.strip().lower() for s in sources.split(",")] if sources else ["all"]

    if "all" in sources_list:
        for display_name, cls in SEARCHER_MAP.values():
            searchers.append((display_name, cls()))
    else:
        for src in sources_list:
            if src in SEARCHER_MAP:
                display_name, cls = SEARCHER_MAP[src]
                searchers.append((display_name, cls()))

    return searchers

def render_template(template_name: str, **context) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(**context)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_session_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    html = render_template("login.html", request=request, error=None, username="")
    return HTMLResponse(content=html)

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    session = get_session()
    try:
        user = authenticate_user(session, username, password)
        if not user:
            html = render_template(
                "login.html",
                request=request,
                error="Invalid username or password",
                username=username,
            )
            return HTMLResponse(content=html, status_code=401)

        response = RedirectResponse(url="/", status_code=303)
        set_session_user(response, user.id)
        return response
    finally:
        session.close()

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = get_session_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    html = render_template(
        "register.html",
        request=request,
        error=None,
        username="",
        email="",
        full_name="",
        institution="",
    )
    return HTMLResponse(content=html)

@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    institution: str = Form(""),
):
    session = get_session()
    try:
        if get_user_by_username(session, username):
            html = render_template(
                "register.html",
                request=request,
                error="Username already exists",
                username=username,
                email=email,
                full_name=full_name,
                institution=institution,
            )
            return HTMLResponse(content=html, status_code=400)
        if get_user_by_email(session, email):
            html = render_template(
                "register.html",
                request=request,
                error="Email already exists",
                username=username,
                email=email,
                full_name=full_name,
                institution=institution,
            )
            return HTMLResponse(content=html, status_code=400)

        create_user(
            session=session,
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            institution=institution,
        )
        return RedirectResponse(url="/login", status_code=303)
    finally:
        session.close()

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=303)
    clear_session(request, response)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(require_login)):
    session = get_session()
    try:
        history = get_user_search_history(session, user.id)
        favorites = get_user_favorites(session, user.id)

        html = render_template(
            "dashboard.html",
            request=request,
            user=user,
            history=history,
            favorites=favorites,
        )
        return HTMLResponse(content=html)
    finally:
        session.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_session_user(request)
    if user:
        html = render_template(
            "index.html",
            request=request,
            results=None,
            query="",
            author="",
            source="all",
            total=0,
            error=None,
            user=user,
            favorite_paper_ids=set(),
            page=1,
            num_results=10,
        )
        return HTMLResponse(content=html)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    user: User = Depends(require_login),
    q: str = Query("", description="Search query"),
    author: str = Query("", description="Author name"),
    source: str = Query("all", description="Source(s) to search"),
    num_results: int = Query(10, ge=1, le=50, description="Number of results per source"),
    page: int = Query(1, ge=1, description="Page number"),
):
    if not q and not author:
        html = render_template(
            "index.html",
            request=request,
            results=None,
            query=q,
            author=author,
            source=source,
            total=0,
            error="Please provide a search query or author name.",
            user=user,
        )
        return HTMLResponse(content=html)

    searchers = get_searchers(source)
    all_results = []

    for name, searcher in searchers:
        if author:
            result = searcher.search_by_author(author, num_results)
        else:
            result = searcher.search(q, num_results, page)
        all_results.append(result)

    total_articles = sum(len(r.articles) for r in all_results)

    if user:
        session = get_session()
        try:
            save_search_history(
                session=session,
                user_id=user.id,
                query=q or "",
                author=author or "",
                source=source,
                num_results=num_results,
                page=page,
                total_found=total_articles,
            )
        finally:
            session.close()

    favorite_paper_ids = set()
    if user:
        session = get_session()
        try:
            for fav in get_user_favorites(session, user.id):
                if fav.paper:
                    favorite_paper_ids.add(fav.paper.id)
        finally:
            session.close()

    html = render_template(
        "index.html",
        request=request,
        results=all_results,
        query=q,
        author=author,
        source=source,
        total=total_articles,
        error=None,
        user=user,
        favorite_paper_ids=favorite_paper_ids,
        page=page,
        num_results=num_results,
    )
    return HTMLResponse(content=html)

@app.post("/api/favorites/add")
async def api_add_favorite(
    request: Request,
    paper_data: dict,
):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first")

    session = get_session()
    try:
        paper = save_or_get_paper(session, paper_data)
        fav = add_favorite(session, user.id, paper.id)
        return {"status": "ok", "favorite_id": fav.id, "paper_id": paper.id}
    finally:
        session.close()

@app.post("/api/favorites/remove")
async def api_remove_favorite(
    request: Request,
    data: dict,
):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first")

    paper_id = data.get("paper_id")
    if not paper_id:
        raise HTTPException(status_code=400, detail="paper_id required")

    session = get_session()
    try:
        removed = remove_favorite(session, user.id, paper_id)
        return {"status": "ok", "removed": removed}
    finally:
        session.close()

@app.get("/api/favorites")
async def api_get_favorites(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first")

    session = get_session()
    try:
        favorites = get_user_favorites(session, user.id)
        return {
            "status": "ok",
            "favorites": [f.to_dict() for f in favorites],
        }
    finally:
        session.close()

@app.post("/api/feedback/add")
async def api_add_feedback(
    request: Request,
    feedback_data: dict,
):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first")

    paper_data = feedback_data.get("paper", {})
    rating = feedback_data.get("rating", 0)
    comment = feedback_data.get("comment", "")
    is_public = feedback_data.get("is_public", False)

    if not paper_data.get("title"):
        raise HTTPException(status_code=400, detail="Paper title is required")

    session = get_session()
    try:
        paper = save_or_get_paper(session, paper_data)
        fb = add_feedback(session, user.id, paper.id, rating, comment, is_public)
        return {"status": "ok", "feedback_id": fb.id}
    finally:
        session.close()

@app.get("/api/feedback/{paper_id}")
async def api_get_feedback(paper_id: int):
    session = get_session()
    try:
        feedbacks = get_paper_feedback(session, paper_id)
        return {
            "status": "ok",
            "feedback": [f.to_dict() for f in feedbacks],
        }
    finally:
        session.close()

@app.get("/api/history")
async def api_get_history(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first")

    session = get_session()
    try:
        history = get_user_search_history(session, user.id)
        return {
            "status": "ok",
            "history": [h.to_dict() for h in history],
        }
    finally:
        session.close()

@app.get("/api/search")
async def api_search(
    request: Request,
    user: User = Depends(require_login),
    q: str = Query("", description="Search query"),
    author: str = Query("", description="Author name"),
    source: str = Query("all", description="Source(s) to search"),
    num_results: int = Query(10, ge=1, le=50),
    page: int = Query(1, ge=1),
    export: str = Query("", description="Export format (json, csv, text)"),
    save_history: bool = Query(True, description="Save to search history"),
):
    if not q and not author:
        raise HTTPException(status_code=400, detail="Provide 'q' (query) or 'author' parameter")

    searchers = get_searchers(source)
    all_articles = []

    for name, searcher in searchers:
        if author:
            result = searcher.search_by_author(author, num_results)
        else:
            result = searcher.search(q, num_results, page)
        all_articles.extend(result.articles)

    if user and save_history:
        session = get_session()
        try:
            save_search_history(
                session=session,
                user_id=user.id,
                query=q or "",
                author=author or "",
                source=source,
                num_results=num_results,
                page=page,
                total_found=len(all_articles),
            )
        finally:
            session.close()

    if export:
        export_format = export.lower()
        filename = f"scholarsearch_export.{export_format}"
        filepath = str(BASE_DIR / filename)
        try:
            exporter = get_exporter(export_format)
            exporter.export(all_articles, filepath)
            return FileResponse(filepath, filename=filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    return {
        "query": q or author,
        "total": len(all_articles),
        "articles": [a.to_dict() for a in all_articles],
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

def run_server():
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )

if __name__ == "__main__":
    run_server()
