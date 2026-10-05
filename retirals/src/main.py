# This block is a workaround to allow direct execution of `python src/main.py`.
# It adds the 'src' directory to the system path so that absolute imports work.
# The standard way to run this application is `uvicorn src.main:app --reload` from the `retirals` directory.
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
import uvicorn
from os import getenv
import logging

from models import PlannerInputs
from retirement_engine import run_projection, run_monte_carlo
from ai_insights import AIInsightRequest, AIInsightResponse, AIInsightService
from auth import (
    authenticate,
    clear_session_cookie,
    get_session,
    logout,
    require_auth,
    require_same_origin,
    set_session_cookie,
)

app = FastAPI()


def get_client_ip(request: Request) -> str:
    return request.headers.get("cf-connecting-ip", request.client.host)


limiter = Limiter(key_func=get_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/chart.js; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:;"
    )

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" in content_type and request.url.path not in {"/auth/login", "/auth/session"}:
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            marker = b"</head>"
            if marker in body and b"/static/auth.js" not in body:
                injection = b'<script src="/static/auth.js" defer></script>'
                body = body.replace(marker, injection + marker, 1)
                headers = dict(response.headers)
                headers.pop("content-length", None)
                response = Response(
                    content=body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.media_type,
                )
        except Exception:
            logger.exception("Failed to inject authentication UI into HTML response")

    return response


app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "assets")), name="assets")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


@app.post("/auth/login")
@limiter.limit("10/minute")
async def auth_login(request: Request):
    require_same_origin(request)
    payload = await request.json()
    username = str(payload.get("username", ""))
    password = str(payload.get("password", ""))
    session_id = authenticate(username, password, request)
    response = JSONResponse({"authenticated": True})
    set_session_cookie(response, request, session_id)
    return response


@app.get("/auth/session")
async def auth_session(request: Request):
    session = get_session(request)
    return {"authenticated": session is not None}


@app.post("/auth/logout")
async def auth_logout(request: Request):
    require_same_origin(request)
    logout(request)
    response = JSONResponse({"authenticated": False})
    clear_session_cookie(response)
    return response


@app.post("/calculate")
@limiter.limit("10/minute")
def calculate_retirement(request: Request, inputs: PlannerInputs):
    require_auth(request)
    try:
        return run_projection(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("An unexpected error occurred during calculation.", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while calculating the projection.")


@app.post("/calculate-mc")
@limiter.limit("5/minute")
def calculate_monte_carlo(request: Request, inputs: PlannerInputs):
    require_auth(request)
    try:
        return run_monte_carlo(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("An unexpected error occurred during Monte Carlo calculation.", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while running Monte Carlo simulation.")


@app.post("/api/ai-insight")
@limiter.limit("5/minute")
def ai_insight(request: Request, payload: AIInsightRequest):
    require_auth(request)
    try:
        return AIInsightService.process_insight_request(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception:
        logger.error("An unexpected error occurred during AI insight processing.", exc_info=True)
        raise HTTPException(status_code=500, detail="The AI service is temporarily unavailable. Please try again later.")


# Page HTML is served so the existing floating login overlay can render even
# when a user enters a deep link directly. The sensitive operations and all
# financial/AI data endpoints remain server-side protected by require_auth().
# Until a session exists, auth.js keeps the entire page covered and prevents
# interaction; after login it is revealed normally.
@app.get("/")
async def read_index():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    return FileResponse(static_file)


@app.get("/ai-insights")
async def read_ai_insights():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'ai-insights.html')
    return FileResponse(static_file)


@app.get("/methodology")
async def read_methodology():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'methodology.html')
    return FileResponse(static_file)


if __name__ == "__main__":
    port = int(getenv("PORT", 20080))
    print("Starting Parity Retirement Planner Server...")
    print(f"  - Access the planner at http://localhost:{port}/")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
