# Routes package initialization
from .analiz_paneli import analiz_paneli_bp
from .trend_analizi import trend_analizi_bp
from .kar_tahmini import kar_tahmini_bp
from .tahminleyici import tahminleyici_bp
from .rakip_analizi import rakip_analizi_bp
from .yonetici_paneli import yonetici_paneli_bp

__all__ = [
    'analiz_paneli_bp',
    'trend_analizi_bp',
    'kar_tahmini_bp',
    'tahminleyici_bp',
    'rakip_analizi_bp',
    'yonetici_paneli_bp'
]

