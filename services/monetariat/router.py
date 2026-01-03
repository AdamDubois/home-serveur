#!/usr/bin/env python3
"""
Routes FastAPI pour Monétariat
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from . import database as db

# Configuration
router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialiser la DB au démarrage
db.init_db()

# Models Pydantic
class NewCategory(BaseModel):
    nom: str
    type: str

class NewTransaction(BaseModel):
    date: str
    compte_id: int
    montant: float
    categorie_id: Optional[int] = None
    description: Optional[str] = None
    necessite: Optional[str] = None
    mode_paiement_id: Optional[int] = None
    type: str
    compte_destination_id: Optional[int] = None

@router.get("/", response_class=HTMLResponse)
async def monetariat_dashboard(request: Request):
    """Page principale du dashboard Monétariat"""
    html_path = BASE_DIR / "templates" / "monetariat" / "dashboard.html"
    return FileResponse(html_path)

# API Routes
@router.get("/api/accounts")
async def api_get_accounts():
    """Récupère tous les comptes"""
    return db.get_all_accounts()

@router.get("/api/categories/{cat_type}")
async def api_get_categories(cat_type:  str):
    """Récupère les catégories par type (depense/revenu)"""
    return db.get_categories_by_type(cat_type)

@router.get("/api/payment-methods")
async def api_get_payment_methods():
    """Récupère tous les modes de paiement"""
    return db.get_all_payment_methods()

@router.post("/api/categories")
async def api_add_category(category: NewCategory):
    """Ajoute une nouvelle catégorie"""
    result = db.add_category(category.nom, category.type)
    if result:
        return result
    else:
        return JSONResponse(
            status_code=400,
            content={"error":  "Catégorie déjà existante"}
        )

@router.post("/api/transactions")
async def api_add_transaction(transaction: NewTransaction):
    """Ajoute une nouvelle transaction"""
    transaction_id = db.add_transaction(transaction.dict())
    return {"id": transaction_id, "status": "success"}

@router.get("/api/transactions")
async def api_get_transactions(limit: int = 100):
    """Récupère toutes les transactions"""
    return db.get_all_transactions(limit)