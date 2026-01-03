#!/usr/bin/env python3
"""
Gestion de la base de données WiFi Monitor
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

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
            timestamp DATETIME NOT NULL,
            host TEXT NOT NULL,
            min_latency REAL,
            avg_latency REAL,
            max_latency REAL,
            packet_loss REAL NOT NULL,
            packets_transmitted INTEGER,
            packets_received INTEGER,
            status TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON ping_stats(timestamp)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_host 
        ON ping_stats(host)
    ''')
    
    conn.commit()
    conn.close()

def get_latest_stats(hours=24):
    """
    Récupère les statistiques AGRÉGÉES par hôte (dernières X heures)
    Retourne 1 entrée par hôte avec moyennes calculées + uptime
    """
    conn = get_db_connection()
    cutoff = datetime.now() - timedelta(hours=hours)
    
    cursor = conn.execute("""
        SELECT 
            host,
            AVG(avg_latency) as avg_latency,
            MIN(min_latency) as min_latency,
            MAX(max_latency) as max_latency,
            AVG(packet_loss) as packet_loss,
            COUNT(*) as sample_count,
            MAX(timestamp) as last_seen,
            -- Calcul de l'uptime :  % de mesures avec packet_loss < 100%
            ROUND(100.0 * SUM(CASE WHEN packet_loss < 100 THEN 1 ELSE 0 END) / COUNT(*), 2) as uptime_percent,
            -- Total de paquets perdus
            SUM(CASE WHEN packet_loss = 100 THEN 1 ELSE 0 END) as total_outages
        FROM ping_stats
        WHERE timestamp > ?
        GROUP BY host
        ORDER BY host
    """, (cutoff.strftime('%Y-%m-%d %H:%M:%S'),))
    
    stats = []
    for row in cursor.fetchall():
        stats.append({
            'host': row['host'],
            'avg_latency': round(row['avg_latency'], 3) if row['avg_latency'] else None,
            'min_latency': round(row['min_latency'], 3) if row['min_latency'] else None,
            'max_latency':  round(row['max_latency'], 3) if row['max_latency'] else None,
            'packet_loss': round(row['packet_loss'], 2) if row['packet_loss'] else 0,
            'uptime_percent': row['uptime_percent'],
            'total_outages': row['total_outages'],
            'sample_count': row['sample_count'],
            'last_seen':  row['last_seen']
        })
    
    conn.close()
    return stats

def get_history(hours=24):
    """
    Récupère l'historique DÉTAILLÉ des pings (non agrégé)
    Pour tracer les graphiques
    """
    conn = get_db_connection()
    cutoff = datetime.now() - timedelta(hours=hours)
    
    cursor = conn.execute("""
        SELECT 
            timestamp,
            host,
            avg_latency,
            packet_loss,
            status
        FROM ping_stats
        WHERE timestamp > ?
        ORDER BY timestamp ASC
    """, (cutoff.strftime('%Y-%m-%d %H:%M:%S'),))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'timestamp': row['timestamp'],
            'host': row['host'],
            'avg_latency': round(row['avg_latency'], 3) if row['avg_latency'] else 0,
            'packet_loss':  round(row['packet_loss'], 1) if row['packet_loss'] else 0,
            'status': row['status']
        })
    
    conn.close()
    return history

def get_aggregated_history(hours=24, interval_minutes=60):
    """
    Récupère l'historique AGRÉGÉ par intervalle de temps
    Pour optimiser l'affichage des graphiques sur de longues périodes
    
    Args:
        hours:  Nombre d'heures à récupérer
        interval_minutes: Intervalle d'agrégation en minutes
    
    Returns:
        Liste de données agrégées (moyennes par intervalle)
    """
    conn = get_db_connection()
    cutoff = datetime.now() - timedelta(hours=hours)
    
    # Conversion interval_minutes en format SQLite
    # On arrondit les timestamps à l'intervalle le plus proche
    cursor = conn.execute(f"""
        SELECT 
            datetime(
                strftime('%s', timestamp) - (strftime('%s', timestamp) % ({interval_minutes} * 60)),
                'unixepoch'
            ) as time_bucket,
            host,
            AVG(avg_latency) as avg_latency,
            AVG(packet_loss) as packet_loss,
            AVG(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END) as timeout_rate
        FROM ping_stats
        WHERE timestamp > ?
        GROUP BY time_bucket, host
        ORDER BY time_bucket ASC
    """, (cutoff.strftime('%Y-%m-%d %H:%M:%S'),))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'timestamp': row['time_bucket'],
            'host': row['host'],
            'avg_latency':  round(row['avg_latency'], 3) if row['avg_latency'] else 0,
            'packet_loss': round(row['packet_loss'], 1) if row['packet_loss'] else 0,
            'status': 'timeout' if row['timeout_rate'] > 0.5 else 'success'
        })
    
    conn.close()
    return history

def get_custom_period_history(start_date, end_date, max_points=30):
    """
    Récupère l'historique pour une période personnalisée
    Calcule automatiquement l'intervalle pour limiter à max_points
    
    Args:
        start_date: Date de début (format:  'YYYY-MM-DD HH:MM:SS')
        end_date: Date de fin (format: 'YYYY-MM-DD HH:MM:SS')
        max_points:  Nombre maximum de points à retourner
    
    Returns: 
        Liste de données agrégées
    """
    conn = get_db_connection()
    
    # Calculer la durée totale en minutes
    start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
    total_minutes = int((end_dt - start_dt).total_seconds() / 60)
    
    # Calculer l'intervalle pour avoir environ max_points
    interval_minutes = max(1, total_minutes // max_points)
    
    cursor = conn.execute(f"""
        SELECT 
            datetime(
                strftime('%s', timestamp) - (strftime('%s', timestamp) % ({interval_minutes} * 60)),
                'unixepoch'
            ) as time_bucket,
            host,
            AVG(avg_latency) as avg_latency,
            AVG(packet_loss) as packet_loss,
            AVG(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END) as timeout_rate
        FROM ping_stats
        WHERE timestamp BETWEEN ? AND ?
        GROUP BY time_bucket, host
        ORDER BY time_bucket ASC
    """, (start_date, end_date))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'timestamp': row['time_bucket'],
            'host': row['host'],
            'avg_latency':  round(row['avg_latency'], 3) if row['avg_latency'] else 0,
            'packet_loss': round(row['packet_loss'], 1) if row['packet_loss'] else 0,
            'status': 'timeout' if row['timeout_rate'] > 0.5 else 'success'
        })
    
    conn.close()
    return history
    
def get_summary_stats(hours=24):
    """Récupère un résumé des statistiques"""
    conn = get_db_connection()
    cutoff = datetime.now() - timedelta(hours=hours)
    
    cursor = conn.execute("""
        SELECT 
            COUNT(DISTINCT host) as host_count,
            AVG(avg_latency) as overall_avg_latency,
            AVG(packet_loss) as overall_packet_loss
        FROM ping_stats
        WHERE timestamp > ?
    """, (cutoff.strftime('%Y-%m-%d %H:%M:%S'),))
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        'host_count': row['host_count'],
        'overall_avg_latency': round(row['overall_avg_latency'], 3) if row['overall_avg_latency'] else None,
        'overall_packet_loss': round(row['overall_packet_loss'], 2) if row['overall_packet_loss'] else 0
    }

def get_outages(hours=24):
    """
    Détecte et regroupe les pannes de connexion
    Retourne des périodes de panne avec début, fin et durée
    """
    conn = get_db_connection()
    cutoff = datetime.now() - timedelta(hours=hours)
    
    # Récupérer tous les pings
    cursor = conn.execute("""
        SELECT timestamp, host, status, packet_loss
        FROM ping_stats
        WHERE timestamp > ?
        ORDER BY timestamp ASC
    """, (cutoff.strftime('%Y-%m-%d %H:%M:%S'),))
    
    results = cursor.fetchall()
    conn.close()
    
    # Détecter les pannes (perte de paquets > 50% ou status = 'timeout')
    outages = []
    current_outage = {}
    
    for row in results:
        is_down = row['status'] == 'timeout' or (row['packet_loss'] and row['packet_loss'] >= 50)
        host = row['host']
        
        if is_down:
            if host not in current_outage: 
                # Début d'une nouvelle panne pour cet hôte
                current_outage[host] = {
                    'host': host,
                    'start': row['timestamp'],
                    'end': None,
                    'duration': None,
                    'status': 'ongoing'
                }
        else:
            if host in current_outage: 
                # Fin de la panne pour cet hôte
                current_outage[host]['end'] = row['timestamp']
                current_outage[host]['status'] = 'resolved'
                
                # Calculer la durée
                try:
                    start_dt = datetime.strptime(current_outage[host]['start'], '%Y-%m-%d %H:%M:%S')
                    end_dt = datetime.strptime(current_outage[host]['end'], '%Y-%m-%d %H:%M:%S')
                    duration = end_dt - start_dt
                    current_outage[host]['duration_seconds'] = int(duration.total_seconds())
                    
                    # Format durée lisible
                    minutes, seconds = divmod(int(duration.total_seconds()), 60)
                    hours_dur, minutes = divmod(minutes, 60)
                    if hours_dur > 0:
                        current_outage[host]['duration'] = f"{hours_dur}h {minutes}m {seconds}s"
                    elif minutes > 0:
                        current_outage[host]['duration'] = f"{minutes}m {seconds}s"
                    else:
                        current_outage[host]['duration'] = f"{seconds}s"
                except: 
                    current_outage[host]['duration'] = 'Unknown'
                
                outages.append(current_outage[host])
                del current_outage[host]
    
    # Pannes toujours en cours
    for host, outage in current_outage.items():
        outage['end'] = 'En cours'
        outage['duration'] = 'En cours'
        outage['status'] = 'ongoing'
        outages.append(outage)
    
    return outages