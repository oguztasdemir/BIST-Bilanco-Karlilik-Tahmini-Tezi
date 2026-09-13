import os
import sys
import webbrowser
from flask import Flask, redirect

# Make sure the current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, static_folder="static")

# ── STATIC FILE ROUTING ────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect('/analiz-paneli')

# ── BLUEPRINT REGISTRATIONS ───────────────────────────────────────────────────
from routes import (
    analiz_paneli_bp,
    trend_analizi_bp,
    kar_tahmini_bp,
    tahminleyici_bp,
    rakip_analizi_bp,
    yonetici_paneli_bp
)

app.register_blueprint(analiz_paneli_bp)
app.register_blueprint(trend_analizi_bp)
app.register_blueprint(kar_tahmini_bp)
app.register_blueprint(tahminleyici_bp)
app.register_blueprint(rakip_analizi_bp)
app.register_blueprint(yonetici_paneli_bp)

# ── APPLICATION STARTUP ───────────────────────────────────────────────────────
if __name__ == '__main__':
    # Automatically open web browser on startup
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:5000")
        
    import threading
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)

