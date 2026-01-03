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

@router.get("/api/history/custom")
async def api_custom_history(start:  str, end: str):
    """
    API pour une période personnalisée
    
    Args: 
        start: Date de début (format:  YYYY-MM-DD)
        end: Date de fin (format: YYYY-MM-DD)
    
    Returns:
        Historique agrégé (max 30 points)
    """
    try:
        # Convertir en datetime avec heure 00:00:00
        start_datetime = f"{start} 00:00:00"
        end_datetime = f"{end} 23:59:59"
        
        history = db.get_custom_period_history(start_datetime, end_datetime, max_points=30)
        return history
    except Exception as e: 
        return {"error": str(e)}
        
@router.get("/api/history/{period}")
async def api_history(period: str):
    """
    API pour l'historique avec agrégation automatique selon la période
    
    Périodes supportées:
    - 1:  Dernière heure (données brutes)
    - 6: 6 dernières heures (agrégé 30 min)
    - 24: 24 dernières heures (agrégé 1h)
    - 168: Dernière semaine (agrégé 12h)
    - 720:  Dernier mois (agrégé 1 jour)
    - 4320: 6 derniers mois (agrégé 15 jours)
    - 8760: 1 an (agrégé 1 mois)
    """
    # Mapping période → (heures, intervalle_minutes)
    periods = {
        "1": (1, 1),              # 1h → données brutes (1 min)
        "6": (6, 30),             # 6h → agrégé 30 min
        "24": (24, 60),           # 24h → agrégé 1h
        "168": (168, 720),        # 7j → agrégé 12h
        "720": (720, 1440),       # 30j → agrégé 1 jour
        "4320": (4320, 21600),    # 6 mois → agrégé 15 jours
        "8760": (8760, 43200),    # 1 an → agrégé 1 mois
    }
    
    if period not in periods:
        return {"error": "Invalid period"}
    
    hours, interval = periods[period]
    
    # Pour les courtes périodes, utiliser les données brutes
    if interval == 1:
        history = db.get_history(hours)
    else:
        history = db.get_aggregated_history(hours, interval)
    
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