from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import webhooks, leads, analytics

app = FastAPI(title="Happy Robot Club Mate", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(webhooks.router, prefix="/webhooks", tags=["HappyRobot"])
app.include_router(leads.router,    prefix="/leads",    tags=["Leads"])
app.include_router(analytics.router,prefix="/analytics",tags=["Analytics"])
