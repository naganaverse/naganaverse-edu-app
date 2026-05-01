import sys
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from fastapi import FastAPI
from database.connection import init_pool, close_pool
from loguru import logger

app = FastAPI(title="Naganaverse Sandbox API")

@app.on_event("startup")
async def startup():
    await init_pool()
    logger.info("Sandbox API started. Ready for experimentation!")

@app.on_event("shutdown")
async def shutdown():
    await close_pool()
    logger.info("Sandbox API shut down.")

@app.get("/")
async def root():
    return {"message": "Welcome to the Naganaverse Development Sandbox", "status": "active"}

# Add your experimental routes here
@app.get("/experiment")
async def experiment():
    # Example: Test a new repository query here
    return {"result": "Experimental logic goes here"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) # Running on 8001 to avoid conflict with main API
