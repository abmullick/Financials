# This block is a workaround to allow direct execution of `python src/main.py`.
# It adds the 'src' directory to the system path so that absolute imports work.
# The standard way to run this application is `uvicorn src.main:app --reload` from the `retirals` directory.
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn 
from os import getenv

from models import PlannerInputs
from retirement_engine import run_projection

# Start the FastAPI application 

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "assets")), name="assets")

@app.post("/calculate")
def calculate_retirement(inputs: PlannerInputs):
    try:
        return run_projection(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/")
async def read_index():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    return FileResponse(static_file)

if __name__ == "__main__":
    port = int(getenv("PORT", 20080))
    print(f"Starting Parity Retirement Planner Server...")
    print(f"  - Access the planner at http://localhost:{port}/")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)