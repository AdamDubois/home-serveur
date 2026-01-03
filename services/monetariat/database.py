#!/usr/bin/env python3
"""
Gestion de la base de données Monétariat
"""

import sqlite3
from pathlib import Path
from datetime import datetime

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "databases" / "monetariat.db"

def get_db_connection():
    """Crée une connexion à la base de données"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Table des comptes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            solde_initial REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des catégories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            type TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nom, type)
        )
    ''')
    
    # Table des modes de paiement
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Table des transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            compte_id INTEGER NOT NULL,
            montant REAL NOT NULL,
            categorie_id INTEGER,
            description TEXT,
            necessite TEXT,
            mode_paiement_id INTEGER,
            type TEXT NOT NULL,
            compte_destination_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (compte_id) REFERENCES accounts(id),
            FOREIGN KEY (categorie_id) REFERENCES categories(id),
            FOREIGN KEY (mode_paiement_id) REFERENCES payment_methods(id),
            FOREIGN KEY (compte_destination_id) REFERENCES accounts(id)
        )
    ''')
    
    # Insérer les comptes par défaut
    cursor.execute('SELECT COUNT(*) FROM accounts')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO accounts (nom, type, solde_initial) VALUES ('Débit', 'debit', 0)")
        cursor.execute("INSERT INTO accounts (nom, type, solde_initial) VALUES ('Épargne', 'epargne', 0)")
        cursor.execute("INSERT INTO accounts (nom, type, solde_initial) VALUES ('Crédit', 'credit', 0)")
    
    # Insérer les catégories par défaut - DÉPENSES
    default_expense_categories = [
        'Alimentation', 'Transport', 'Logement', 'Loisirs', 
        'Santé', 'Abonnement', 'Autres'
    ]
    for cat in default_expense_categories: 
        cursor.execute(
            "INSERT OR IGNORE INTO categories (nom, type) VALUES (?, 'depense')",
            (cat,)
        )
    
    # Insérer les catégories par défaut - REVENUS
    default_income_categories = ['Salaire', 'Remboursement', 'Autres']
    for cat in default_income_categories:
        cursor.execute(
            "INSERT OR IGNORE INTO categories (nom, type) VALUES (?, 'revenu')",
            (cat,)
        )
    
    # Insérer les modes de paiement par défaut
    default_payment_methods = ['Comptant', 'Débit', 'Crédit', 'Virement', 'Chèque']
    for method in default_payment_methods:
        cursor.execute(
            "INSERT OR IGNORE INTO payment_methods (nom) VALUES (?)",
            (method,)
        )
    
    conn.commit()
    conn.close()

# Fonctions CRUD

def get_all_accounts():
    """Récupère tous les comptes"""
    conn = get_db_connection()
    accounts = conn.execute('SELECT * FROM accounts ORDER BY id').fetchall()
    conn.close()
    return [dict(row) for row in accounts]

def get_categories_by_type(cat_type):
    """Récupère les catégories par type (depense/revenu)"""
    conn = get_db_connection()
    categories = conn.execute(
        'SELECT * FROM categories WHERE type = ? ORDER BY nom',
        (cat_type,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in categories]

def get_all_payment_methods():
    """Récupère tous les modes de paiement"""
    conn = get_db_connection()
    methods = conn.execute('SELECT * FROM payment_methods ORDER BY nom').fetchall()
    conn.close()
    return [dict(row) for row in methods]

def add_category(nom, cat_type):
    """Ajoute une nouvelle catégorie"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO categories (nom, type) VALUES (?, ?)',
            (nom, cat_type)
        )
        conn.commit()
        category_id = cursor.lastrowid
        conn.close()
        return {'id': category_id, 'nom': nom, 'type':  cat_type}
    except sqlite3.IntegrityError:
        conn.close()
        return None

def add_transaction(data):
    """Ajoute une nouvelle transaction"""
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO transactions 
        (date, compte_id, montant, categorie_id, description, necessite, 
         mode_paiement_id, type, compte_destination_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['date'],
        data['compte_id'],
        data['montant'],
        data.get('categorie_id'),
        data.get('description'),
        data.get('necessite'),
        data.get('mode_paiement_id'),
        data['type'],
        data.get('compte_destination_id')
    ))
    conn.commit()
    transaction_id = cursor.lastrowid
    conn.close()
    return transaction_id

def get_all_transactions(limit=100):
    """Récupère toutes les transactions"""
    conn = get_db_connection()
    transactions = conn.execute('''
        SELECT 
            t.*,
            a.nom as compte_nom,
            c.nom as categorie_nom,
            pm.nom as mode_paiement_nom,
            ad.nom as compte_destination_nom
        FROM transactions t
        LEFT JOIN accounts a ON t.compte_id = a.id
        LEFT JOIN categories c ON t.categorie_id = c.id
        LEFT JOIN payment_methods pm ON t.mode_paiement_id = pm.id
        LEFT JOIN accounts ad ON t.compte_destination_id = ad.id
        ORDER BY t.date DESC, t.created_at DESC
        LIMIT ? 
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in transactions]