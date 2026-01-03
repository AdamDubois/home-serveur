#!/usr/bin/env python3
"""
Routes FastAPI pour Monétariat
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from datetime import date
from typing import Optional
from pathlib import Path

from . import database as db

# Configuration
router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent

# Initialiser la DB au démarrage
db.init_db()

# Modèles
class ExpenseCreate(BaseModel):
    amount: float
    category: str
    necessity_level: str
    expense_date: date
    description: Optional[str] = None
    payment_method: Optional[str] = None

@router.get("/", response_class=HTMLResponse)
async def monetariat_home():
    """Page d'ajout de dépense"""
    html_path = BASE_DIR / "templates" / "monetariat" / "form.html"
    return FileResponse(html_path)

@router.get("/dashboard", response_class=HTMLResponse)
async def monetariat_dashboard():
    """Dashboard des dépenses"""
    html_path = BASE_DIR / "templates" / "monetariat" / "dashboard.html"
    return FileResponse(html_path)

@router.post("/api/expenses")
async def create_expense(expense: ExpenseCreate):
    """Créer une dépense"""
    conn = db.get_db_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO expenses 
               (amount, category, necessity_level, expense_date, description, payment_method) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (expense.amount, expense.category, expense.necessity_level, 
             str(expense.expense_date), expense.description, expense.payment_method)
        )
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/api/expenses")
async def get_expenses(limit: int = 100):
    """Récupérer les dépenses"""
    conn = db.get_db_connection()
    cursor = conn.execute(
        """SELECT * FROM expenses 
           ORDER BY expense_date DESC, created_at DESC 
           LIMIT ?""",
        (limit,)
    )
    expenses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return expenses

@router.get("/api/expenses/stats")
async def get_stats():
    """Statistiques"""
    conn = db.get_db_connection()
    
    # Par catégorie
    cursor = conn.execute("""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM expenses 
        GROUP BY category 
        ORDER BY total DESC
    """)
    by_category = [dict(row) for row in cursor.fetchall()]
    
    # Total
    cursor = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses")
    total = cursor.fetchone()["total"]
    
    # Ce mois
    cursor = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM expenses 
        WHERE strftime('%Y-%m', expense_date) = strftime('%Y-%m', 'now')
    """)
    this_month = cursor.fetchone()["total"]
    
    conn.close()
    
    return {
        "by_category":  by_category,
        "total": float(total),
        "this_month": float(this_month)
    }