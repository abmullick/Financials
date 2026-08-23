# This block is a workaround to allow direct execution of `python src/main.py`.
# It adds the 'src' directory to the system path so that absolute imports work.
# The standard way to run this application is `uvicorn src.main:app --reload` from the `retirals` directory.
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
import uvicorn 
from os import getenv
import logging

from models import PlannerInputs
from retirement_engine import run_projection, run_monte_carlo

# Start the FastAPI application 

app = FastAPI()

def get_client_ip(request: Request) -> str:
    """
    Returns the client's real IP address, considering reverse proxies
    and load balancers (specifically Cloudflare's `CF-Connecting-IP`).
    Falls back to the direct client host if the header is not present.
    """
    return request.headers.get("cf-connecting-ip", request.client.host)

# Configure rate limiting
limiter = Limiter(key_func=get_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure logging to capture detailed errors on the server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Middleware to add security-related HTTP headers to every response.
    This helps protect against common web vulnerabilities.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # A basic Content Security Policy (CSP) to restrict resource loading.
    # This allows scripts and styles only from the app's own origin and trusted CDNs.
    # 'unsafe-inline' is needed for the inline <style> and <script> blocks in index.html.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net/npm/chart.js; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:;"
    )
    return response

app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "assets")), name="assets")

@app.post("/calculate")
@limiter.limit("10/minute")
def calculate_retirement(request: Request, inputs: PlannerInputs):
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
    try:
        return run_monte_carlo(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("An unexpected error occurred during Monte Carlo calculation.", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while running Monte Carlo simulation.")

@app.get("/")
async def read_index():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    return FileResponse(static_file)

@app.get("/methodology")
async def read_methodology():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'methodology.html')
    return FileResponse(static_file)

if __name__ == "__main__":
    port = int(getenv("PORT", 20080))
    print(f"Starting Parity Retirement Planner Server...")
    print(f"  - Access the planner at http://localhost:{port}/")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
