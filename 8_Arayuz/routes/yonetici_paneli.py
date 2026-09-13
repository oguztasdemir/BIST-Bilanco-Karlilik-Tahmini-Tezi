from flask import Blueprint, render_template

yonetici_paneli_bp = Blueprint('yonetici_paneli', __name__)

@yonetici_paneli_bp.route('/yonetici-paneli', methods=['GET'])
def render_page():
    return render_template(
        'yonetici_paneli.html',
        active_page='yonetici_paneli',
        tab_title='Yönetici Paneli',
        tab_desc='Sistem mimarisi, veri tabanı şemaları ve Stacking topluluk modeli eğitim parametreleri.'
    )
