from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.routes import grid, meta, point, public, stations, validation

app = FastAPI(
    title="Counting the Cold API",
    description="Chill (hours, Utah, Dynamic Model portions) and GDD for any California lat/lon.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(point.router)
app.include_router(stations.router)
app.include_router(validation.router)
app.include_router(grid.router)
app.include_router(public.router)
