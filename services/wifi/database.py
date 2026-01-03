#!/usr/bin/env python3
"""
Gestion de la base de données WiFi Monitor
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "databases" / "wifi.db"

def get_db_connection():
    """Crée une connexion à la base de données"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données si elle n'existe pas"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ping_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            host TEXT NOT NULL,
            packets_transmitted INTEGER,
            packets_received INTEGER,
            packet_loss REAL,
            min_latency REAL,
            avg_latency REAL,
            max_latency REAL,
            stddev_latency REAL,
            status TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON ping_stats(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_host ON ping_stats(host)')
    
    conn.commit()
    conn.close()

def get_latest_stats(hours=24):
    """Récupère les dernières statistiques"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        SELECT timestamp, host, avg_latency, packet_loss, status
        FROM ping_stats
        WHERE timestamp > ?
        ORDER BY timestamp ASC
    ''', (since,))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def get_summary_stats(hours=24):
    """Génère un résumé des statistiques"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        SELECT 
            host,
            COUNT(*) as total_checks,
            AVG(avg_latency) as avg_latency,
            MIN(min_latency) as min_latency,
            MAX(max_latency) as max_latency,
            AVG(packet_loss) as avg_loss,
            SUM(CASE WHEN packet_loss > 0 THEN 1 ELSE 0 END) as checks_with_loss
        FROM ping_stats
        WHERE timestamp > ? 
        GROUP BY host
    ''', (since,))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def get_outages(hours=24):
    """Détecte et retourne les pannes réseau"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        SELECT timestamp, host, status, packet_loss
        FROM ping_stats
        WHERE timestamp > ?  AND (status = 'timeout' OR packet_loss >= 100)
        ORDER BY timestamp DESC
    ''', (since,))
    
    raw_outages = cursor.fetchall()
    conn.close()
    
    # Grouper les pannes consécutives
    outages = []
    current_outage = None
    
    for row in raw_outages:
        if current_outage is None or current_outage['host'] != row['host']:
            if current_outage:
                outages.append(current_outage)
            current_outage = {
                'host': row['host'],
                'start': row['timestamp'],
                'end': row['timestamp'],
                'status': 'resolved' if row != raw_outages[0] else 'ongoing'
            }
        else: 
            current_outage['start'] = row['timestamp']
    
    if current_outage: 
        outages.append(current_outage)
    
    # Calculer les durées
    for outage in outages: 
        start_dt = datetime.strptime(outage['start'], '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(outage['end'], '%Y-%m-%d %H:%M:%S')
        duration = end_dt - start_dt
        
        minutes = int(duration.total_seconds() / 60)
        seconds = int(duration.total_seconds() % 60)
        outage['duration'] = f"{minutes}m {seconds}s"
    
    return outages