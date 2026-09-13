import os
import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, request, render_template
from utils import DATA_DIR, get_cached_df, normalize_sector_name, _get_matrix_scores, clean_and_normalize

analiz_paneli_bp = Blueprint('analiz_paneli', __name__)

@analiz_paneli_bp.route('/analiz-paneli', methods=['GET'])
def render_page():
    return render_template(
        'analiz_paneli.html',
        active_page='analiz_paneli',
        tab_title='Analiz Paneli',
        tab_desc='BIST şirketlerinin kur bazlı hibrit model başarıları ve karşılaştırmaları.'
    )

@analiz_paneli_bp.route('/api/sectors', methods=['GET'])
def get_sectors():
    """Lists available sectors from the local USD V1 dataset in standardized format."""
    try:
        standard_sectors = [
            "SANAYI_VE_IMALAT",
            "FINANS_VE_YATIRIM",
            "INSAAT_VE_GAYRIMENKUL",
            "TEKNOLOJI_VE_HIZMET",
            "ENERJI_VE_HAMMADDE",
            "GIDA_VE_TARIM",
            "TICARET_VE_PAZARLAMA"
        ]
        return jsonify({"sectors": standard_sectors})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analiz_paneli_bp.route('/api/sector_accuracy', methods=['GET'])
def get_sector_accuracy():
    """Returns model accuracy per sector — reads stored values from Karar Matrisi Excel."""
    model_type = request.args.get('model', 'kz')
    currency = request.args.get('currency', 'USD').upper()
    try:
        scores = _get_matrix_scores(currency)
        sectors = [
            "SANAYI_VE_IMALAT",
            "FINANS_VE_YATIRIM",
            "INSAAT_VE_GAYRIMENKUL",
            "TEKNOLOJI_VE_HIZMET",
            "ENERJI_VE_HAMMADDE",
            "GIDA_VE_TARIM",
            "TICARET_VE_PAZARLAMA"
        ]
        result = {}
        for sector in sectors:
            row = scores.get(sector, {})
            for k, v in row.items():
                kn = clean_and_normalize(str(k))  # e.g. clsknzskr
                is_kz  = "clskz" in kn and "skor" in kn
                is_yon = "clsyn" in kn and "skor" in kn or "clsyon" in kn and "skor" in kn
                match = is_kz if model_type == "kz" else is_yon
                if match and v is not None:
                    try:
                        result[sector] = round(float(v), 2)
                        break
                    except (ValueError, TypeError):
                        pass
        return jsonify({"accuracies": result})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@analiz_paneli_bp.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Gets the Jigsaw Decision Matrix and comparison metrics locally with USD fallback."""
    requested_currency = request.args.get('currency', 'USD').upper()
    currency = requested_currency
    fallback = False
    
    matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
    compare_path = os.path.join(DATA_DIR, "metrics", f"1_V1_V2_Metrik_Karsilastirma_{currency}.xlsx")
    
    # Fallback to USD if file doesn't exist
    if not os.path.exists(matrix_path) or not os.path.exists(compare_path):
        currency = 'USD'
        fallback = True
        matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
        compare_path = os.path.join(DATA_DIR, "metrics", f"1_V1_V2_Metrik_Karsilastirma_{currency}.xlsx")
        
    try:
        if not os.path.exists(matrix_path) or not os.path.exists(compare_path):
            return jsonify({"error": "Academic metrics Excel sheets not found locally."}), 404
            
        df_best = pd.read_excel(matrix_path, sheet_name="En_Iyi_Yapboz_Matrisi")
        df_best_clean = df_best.replace({np.nan: None}).to_dict(orient="records")
        # Scores in Excel are already the stored academic values — no live re-computation needed
        
        df_worst = pd.read_excel(matrix_path, sheet_name="En_Kotu_Yapboz_Matrisi")
        df_worst_clean = df_worst.replace({np.nan: None}).to_dict(orient="records")
        
        df_notes = pd.read_excel(matrix_path, sheet_name="Açıklama_Notları")
        df_notes_clean = df_notes.replace({np.nan: None}).to_dict(orient="records")
        
        def clean_df_keys(df):
            new_cols = {}
            for col in df.columns:
                clean_col = str(col).replace("Sektör", "Sektor").replace("Sektr", "Sektor")
                clean_col = clean_col.replace("Yön", "Yon").replace("Yn", "Yon")
                new_cols[col] = clean_col
            return df.rename(columns=new_cols).replace({np.nan: None}).to_dict(orient="records")

        df_comp = pd.read_excel(compare_path, sheet_name="Karsilastirma_Ozeti")
        df_comp_clean = clean_df_keys(df_comp)
        
        df_v1 = pd.read_excel(compare_path, sheet_name="v1_Tum_Metrikler")
        df_v1_clean = clean_df_keys(df_v1)
        
        df_v2 = pd.read_excel(compare_path, sheet_name="v2_Tum_Metrikler")
        df_v2_clean = clean_df_keys(df_v2)
        
        return jsonify({
            "best_jigsaw": df_best_clean,
            "worst_jigsaw": df_worst_clean,
            "notes": df_notes_clean,
            "comparison": df_comp_clean,
            "v1_metrics": df_v1_clean,
            "v2_metrics": df_v2_clean,
            "fallback": fallback,
            "requested_currency": requested_currency,
            "used_currency": currency
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analiz_paneli_bp.route('/api/sector_mape', methods=['GET'])
def get_sector_mape():
    """Returns regression hit-rate score per sector from Karar Matrisi (Reg_Sayısal_Skor)."""
    currency = request.args.get('currency', 'USD').upper()
    try:
        scores = _get_matrix_scores(currency)
        sectors = [
            "SANAYI_VE_IMALAT",
            "FINANS_VE_YATIRIM",
            "INSAAT_VE_GAYRIMENKUL",
            "TEKNOLOJI_VE_HIZMET",
            "ENERJI_VE_HAMMADDE",
            "GIDA_VE_TARIM",
            "TICARET_VE_PAZARLAMA"
        ]
        result = {}
        for sector in sectors:
            row = scores.get(sector, {})
            for k, v in row.items():
                kn = clean_and_normalize(str(k))
                # Match Reg_Sayısal_Skor: normalized to 'regsayisalskor' roughly
                if "reg" in kn and "say" in kn and "skor" in kn:
                    try:
                        result[sector] = round(float(v), 1)
                        break
                    except (ValueError, TypeError):
                        pass
        return jsonify({"mapes": result})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500
