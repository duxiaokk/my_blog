from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from routers import auth, chat, comments, pages, posts
from web_deps import get_or_set_csrf_cookie

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
IMAGE_DIR = os.path.join(BASE_DIR, "image")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ado_Jk Personal Blog", docs_url=None, redoc_url=None)
app.mount("/static/images", StaticFiles(directory=IMAGE_DIR), name="static_images")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(comments.router)
app.include_router(posts.router)
app.include_router(pages.router)
app.include_router(chat.router)


@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        accept = (request.headers.get("accept") or "").lower()
        wants_html = "text/html" in accept or "*/*" in accept
        if request.method.upper() == "GET" and wants_html:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        detail = exc.detail if isinstance(exc.detail, str) and exc.detail.strip() else "\u672a\u767b\u5f55"
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": detail})
    return await http_exception_handler(request, exc)


@app.get("/docs", include_in_schema=False)
def swagger_docs():
    openapi_url = app.openapi_url or "/openapi.json"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <title>{app.title} - Swagger UI</title>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
        <script>
        window.onload = function() {{
            window.ui = SwaggerUIBundle({{
                url: "{openapi_url}",
                dom_id: "#swagger-ui",
                deepLinking: true,
                persistAuthorization: true,
                presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
                layout: "BaseLayout",
                requestInterceptor: function(request) {{
                    var match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
                    if (match && match[1]) {{
                        request.headers["X-CSRF-Token"] = decodeURIComponent(match[1]);
                    }}
                    request.credentials = "same-origin";
                    return request;
                }}
            }});
        }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


@app.middleware("http")
async def csrf_cookie_middleware(request: Request, call_next):
    response = await call_next(request)
    try:
        get_or_set_csrf_cookie(request, response)
    except Exception:
        logger.exception("failed to set csrf cookie")
    return response
