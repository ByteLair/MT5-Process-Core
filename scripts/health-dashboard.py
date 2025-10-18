#!/usr/bin/env python3
"""
Health Check API - Simple web interface for health check logs
Provides REST API and simple HTML dashboard
"""

from flask import Flask, jsonify, render_template_string, request
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'health-checks', 'health_checks.db')

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    """Main dashboard HTML"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MT5 Trading - Health Check Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 30px;
            }
            h1 {
                color: #667eea;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }
            .stat-card.healthy { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
            .stat-card.warning { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
            .stat-card.error { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
            .stat-value {
                font-size: 2.5em;
                font-weight: bold;
                margin: 10px 0;
            }
            .stat-label {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .checks-table {
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px;
                text-align: left;
                font-weight: 600;
            }
            td {
                padding: 12px 15px;
                border-bottom: 1px solid #eee;
            }
            tr:hover {
                background: #f5f5f5;
            }
            .status-badge {
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: bold;
                display: inline-block;
            }
            .status-healthy { background: #38ef7d; color: white; }
            .status-unhealthy { background: #f5576c; color: white; }
            .status-warning { background: #feca57; color: #333; }
            .status-down { background: #ee5a6f; color: white; }
            .timestamp {
                color: #666;
                font-size: 0.9em;
            }
            .refresh-info {
                text-align: center;
                margin-top: 20px;
                color: #666;
                font-size: 0.9em;
            }
            .alert-section {
                margin: 30px 0;
                padding: 20px;
                background: #fff3cd;
                border-left: 5px solid #ffc107;
                border-radius: 5px;
            }
            .alert-section h2 {
                color: #856404;
                margin-bottom: 15px;
            }
            .alert-item {
                padding: 10px;
                margin: 10px 0;
                background: white;
                border-radius: 5px;
                border-left: 3px solid #f5576c;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .live-indicator {
                display: inline-block;
                width: 10px;
                height: 10px;
                background: #38ef7d;
                border-radius: 50%;
                animation: pulse 2s infinite;
                margin-right: 5px;
            }
        </style>
        <script>
            async function loadDashboard() {
                try {
                    // Load stats
                    const statsRes = await fetch('/api/stats');
                    const stats = await statsRes.json();
                    
                    document.getElementById('total-checks').textContent = stats.total_checks;
                    document.getElementById('healthy-checks').textContent = stats.healthy_checks;
                    document.getElementById('unhealthy-checks').textContent = stats.unhealthy_checks;
                    document.getElementById('active-alerts').textContent = stats.active_alerts;
                    
                    // Load recent checks
                    const checksRes = await fetch('/api/recent-checks?limit=20');
                    const checks = await checksRes.json();
                    
                    const tbody = document.getElementById('checks-tbody');
                    tbody.innerHTML = '';
                    
                    checks.forEach(check => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td class="timestamp">${new Date(check.timestamp).toLocaleString()}</td>
                            <td>${check.check_type}</td>
                            <td>${check.component_name}</td>
                            <td><span class="status-badge status-${check.status}">${check.status}</span></td>
                            <td>${check.response_time_ms || 0}ms</td>
                            <td>${check.details || '-'}</td>
                        `;
                    });
                    
                    // Load alerts
                    const alertsRes = await fetch('/api/alerts');
                    const alerts = await alertsRes.json();
                    
                    const alertsDiv = document.getElementById('alerts-container');
                    if (alerts.length > 0) {
                        alertsDiv.style.display = 'block';
                        const alertsList = document.getElementById('alerts-list');
                        alertsList.innerHTML = '';
                        alerts.forEach(alert => {
                            const div = document.createElement('div');
                            div.className = 'alert-item';
                            div.innerHTML = `
                                <strong>${alert.component_name}</strong> - ${alert.alert_type}<br>
                                <small>${alert.message}</small><br>
                                <small class="timestamp">${new Date(alert.timestamp).toLocaleString()}</small>
                            `;
                            alertsList.appendChild(div);
                        });
                    } else {
                        alertsDiv.style.display = 'none';
                    }
                    
                } catch (error) {
                    console.error('Error loading dashboard:', error);
                }
            }
            
            // Load dashboard on page load
            window.onload = () => {
                loadDashboard();
                // Refresh every 30 seconds
                setInterval(loadDashboard, 30000);
            };
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🏥 Health Check Dashboard</h1>
            <p class="subtitle">
                <span class="live-indicator"></span>
                Real-time monitoring | Auto-refresh every 30s
            </p>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-label">Total Checks (24h)</div>
                    <div class="stat-value" id="total-checks">-</div>
                </div>
                <div class="stat-card healthy">
                    <div class="stat-label">Healthy</div>
                    <div class="stat-value" id="healthy-checks">-</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Unhealthy</div>
                    <div class="stat-value" id="unhealthy-checks">-</div>
                </div>
                <div class="stat-card error">
                    <div class="stat-label">Active Alerts</div>
                    <div class="stat-value" id="active-alerts">-</div>
                </div>
            </div>
            
            <div id="alerts-container" class="alert-section" style="display: none;">
                <h2>🚨 Active Alerts</h2>
                <div id="alerts-list"></div>
            </div>
            
            <div class="checks-table">
                <h2 style="padding: 20px; color: #667eea;">📊 Recent Health Checks</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Type</th>
                            <th>Component</th>
                            <th>Status</th>
                            <th>Response Time</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody id="checks-tbody">
                        <tr><td colspan="6" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <div class="refresh-info">
                Dashboard updates automatically every 30 seconds<br>
                Database: {{ db_path }}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, db_path=DB_PATH)

@app.route('/api/stats')
def api_stats():
    """Get statistics for last 24 hours"""
    conn = get_db()
    cur = conn.cursor()
    
    # Get stats from last 24 hours
    stats = {
        'total_checks': cur.execute(
            "SELECT COUNT(*) FROM health_checks WHERE timestamp > datetime('now', '-24 hours')"
        ).fetchone()[0],
        'healthy_checks': cur.execute(
            "SELECT COUNT(*) FROM health_checks WHERE timestamp > datetime('now', '-24 hours') AND status='healthy'"
        ).fetchone()[0],
        'unhealthy_checks': cur.execute(
            "SELECT COUNT(*) FROM health_checks WHERE timestamp > datetime('now', '-24 hours') AND status IN ('unhealthy', 'down', 'critical')"
        ).fetchone()[0],
        'active_alerts': cur.execute(
            "SELECT COUNT(*) FROM alerts WHERE resolved=0"
        ).fetchone()[0]
    }
    
    conn.close()
    return jsonify(stats)

@app.route('/api/recent-checks')
def api_recent_checks():
    """Get recent health checks"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = get_db()
    cur = conn.cursor()
    
    checks = cur.execute(
        """SELECT * FROM health_checks 
           ORDER BY timestamp DESC 
           LIMIT ?""",
        (limit,)
    ).fetchall()
    
    conn.close()
    
    return jsonify([dict(check) for check in checks])

@app.route('/api/alerts')
def api_alerts():
    """Get active alerts"""
    conn = get_db()
    cur = conn.cursor()
    
    alerts = cur.execute(
        """SELECT * FROM alerts 
           WHERE resolved=0 
           ORDER BY timestamp DESC"""
    ).fetchall()
    
    conn.close()
    
    return jsonify([dict(alert) for alert in alerts])

@app.route('/api/component/<component>')
def api_component_history(component):
    """Get history for specific component"""
    hours = request.args.get('hours', 24, type=int)
    
    conn = get_db()
    cur = conn.cursor()
    
    history = cur.execute(
        """SELECT * FROM health_checks 
           WHERE component_name=? 
           AND timestamp > datetime('now', '-{} hours')
           ORDER BY timestamp DESC""".format(hours),
        (component,)
    ).fetchall()
    
    conn.close()
    
    return jsonify([dict(h) for h in history])

if __name__ == '__main__':
    # Ensure database exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=False)
