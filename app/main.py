from .access import AccessControl
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .core import Request, analyze, ComparisonRequest, compare
from .guard import InputGuard

app = FastAPI(title="AI Readiness Auditor", version="0.4.0")
app.add_middleware(InputGuard)
STATIC = Path(__file__).with_name("static")
app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/analyze")
def run(request: Request):
    try:
        return analyze(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/guide")
def user_guide():
    return FileResponse(STATIC / "guide.html")


@app.post("/compare")
def compare_assessments(request: ComparisonRequest):
    try:
        return compare(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from .planner import PlanRequest, plan


@app.post("/plan")
def create_plan(request: PlanRequest):
    try:
        return plan(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


app.add_middleware(AccessControl)
