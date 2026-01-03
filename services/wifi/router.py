#!/usr/bin/env python3
"""
Routes FastAPI pour le WiFi Monitor
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from . import database as db

# Configuration
router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialiser la DB au démarrage
db.init_db()

@router.get("/", response_class=HTMLResponse)
async def wifi_dashboard(request: Request):
    """Page principale du dashboard WiFi"""
    html_path = BASE_DIR / "templates" / "wifi" / "dashboard.html"
    return FileResponse(html_path)

@router.get("/api/stats")
async def api_stats(hours: int = 24):
    """API pour récupérer les statistiques"""
    stats = db.get_latest_stats(hours)
    return stats

@router.get("/api/summary")
async def api_summary(hours: int = 24):
    """API pour le résumé"""
    summary = db.get_summary_stats(hours)
    return summary

@router.get("/api/outages")
async def api_outages(hours: int = 24):
    """API pour les pannes"""
    outages = db.get_outages(hours)
    return outages