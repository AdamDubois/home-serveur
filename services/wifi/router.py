#!/usr/bin/env python3
"""
Routes FastAPI pour le WiFi Monitor
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .  import database as db

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

# Routes API compatibles avec l'ancien dashboard
@router.get("/api/stats")
async def api_stats(hours: int = 24):
    """API pour les statistiques globales (format compatible ancien dashboard)"""
    stats_list = db.get_latest_stats(hours)
    
    # Convertir en dictionnaire avec host comme clé (format ancien dashboard)
    stats_dict = {}
    for stat in stats_list:
        stats_dict[stat['host']] = {
            'total_pings': stat['sample_count'],
            'avg_latency': stat['avg_latency'],
            'min_latency': stat['min_latency'],
            'max_latency': stat['max_latency'],
            'avg_packet_loss': stat['packet_loss'],
            'timeouts': stat['total_outages'],
            'uptime':  stat['uptime_percent']  # Renommer uptime_percent -> uptime
        }
    
    return stats_dict

@router.get("/api/history/{hours}")
async def api_history(hours:  int = 24):
    """API pour l'historique détaillé (pour graphiques)"""
    history = db.get_history(hours)
    return history

@router.get("/api/summary")
async def api_summary(hours: int = 24):
    """API pour le résumé"""
    summary = db.get_summary_stats(hours)
    return summary

@router.get("/api/outages/{hours}")
async def api_outages(hours: int = 24):
    """API pour les pannes (compatible ancien dashboard)"""
    outages = db.get_outages(hours)
    return outages