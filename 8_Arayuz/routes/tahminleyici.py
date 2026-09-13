import os
import pandas as pd
import numpy as np
from flask import Blueprint, jsonify, request, render_template
from utils import (
    DATA_DIR,
    MODELS_DIR,
    get_cached_df,
    get_cached_model,
    get_v2_columns,
    align_features_for_model,
    scale_v2_features,
    predict_regression_value,
    get_dec_row,
    normalize_sector_name,
    clean_and_normalize
)

tahminleyici_bp = Blueprint('tahminleyici', __name__)

@tahminleyici_bp.route('/kar-zarar-siniflandirma', methods=['GET'])
def render_kar_zarar():
    return render_template(
        'kar_zarar_siniflandirma.html',
        active_page='kar_zarar_siniflandirma',
        tab_title='Kâr/Zarar Sınıflandırma',
        tab_desc='Yapay zekâ modellerimiz ile Net Dönem Kârının sektör medyanını aşıp aşmayacağının tahmini.'
    )

@tahminleyici_bp.route('/yon-siniflandirma', methods=['GET'])
def render_yon():
    return render_template(
        'yon_siniflandirma.html',
        active_page='yon_siniflandirma',
        tab_title='Yön Sınıflandırma',
        tab_desc='Yapay zekâ modellerimiz ile Net Dönem Kârının cari döneme göre artış veya azalış tahmini.'
    )

@tahminleyici_bp.route('/api/company_features', methods=['GET'])
def get_company_features():
    """Gets the features of a company for a specific period from the local datasets."""
    sector = request.args.get('sector')
    company = request.args.get('company')
    period = request.args.get('period')
    version = request.args.get('version', 'V2').upper() # V1 or V2
    currency = request.args.get('currency', 'USD').upper()
    
    if not sector or not company or not period:
        return jsonify({"error": "sector, company, and period are required"}), 400
        
    try:
        period_num = int(period)
        if version == 'ZEKI_ELEME':
            dataset_path = os.path.join(DATA_DIR, "zeki_eleme", f"3_Final_Filtreli_Veri_{currency}.xlsx")
        elif version == 'V1':
            dataset_path = os.path.join(DATA_DIR, "datasets", "v1", f"2_BIST_{currency}_VIF.xlsx")
        else:
            dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
            if not os.path.exists(dataset_path):
                dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
            
        meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu"] # Net Dönem Karı/Zararı is a feature!
            
        if not os.path.exists(dataset_path):
            return jsonify({"error": f"Local dataset not found for currency {currency} and version {version}."}), 404
            
        df = get_cached_df(dataset_path, sector)
        row = df[(df["Firma Adı"] == company) & (df["Dönem"] == period_num)]
        
        if row.empty:
            return jsonify({"error": "No data found for this company and period"}), 404
            
        row_dict = row.iloc[0].to_dict()
        
        # Detect target column (e.g. contains t+1)
        target_cols = [col for col in df.columns if "t+1" in col]
        target_col = target_cols[0] if target_cols else None
        
        # Meta values
        meta_vals = {col: row_dict.get(col) for col in meta_cols if col in row_dict}
        if target_col:
            meta_vals[target_col] = row_dict.get(target_col)
            
        # Features
        feature_cols = [col for col in df.columns if col not in meta_cols and col != target_col]
        numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
        
        # Filter out engineered/sector/lag/season/anomaly features
        filtered_numeric = []
        for col in numeric_features:
            col_lower = col.lower().strip()
            if col_lower.startswith("sektor") or col_lower.startswith("sektör"):
                continue
            if "mevsim" in col_lower:
                continue
            if "anomali" in col_lower:
                continue
            if "_lag" in col_lower:
                continue
            filtered_numeric.append(col)
            
        features = {col: float(row_dict.get(col, 0.0)) for col in filtered_numeric}
        
        # Replace NaN/None values with 0.0
        for k, v in features.items():
            if np.isnan(v):
                features[k] = 0.0
                
        # Determine current mevsim and anomali
        current_mevsim = 1
        current_anomali = 0
        
        # Read from row if available
        if "Mevsimsellik" in row_dict:
            current_mevsim = int(row_dict["Mevsimsellik"])
        else:
            # Fallback calculation based on Period
            current_mevsim = (period_num - 1) % 4 + 1
            
        if "Anomali_Durumu" in row_dict:
            current_anomali = int(row_dict["Anomali_Durumu"])
        elif "Anomali" in row_dict:
            current_anomali = int(row_dict["Anomali"])
                
        # Current period net profit
        current_profit = row_dict.get("Net Dönem Karı/Zararı", row_dict.get("Net Dönem Karı", 0.0))
        if pd.isna(current_profit):
            current_profit = 0.0
            
        return jsonify({
            "features": features, 
            "meta": meta_vals,
            "current_mevsim": current_mevsim,
            "current_anomali": current_anomali,
            "target_col": target_col,
            "current_profit": float(current_profit)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tahminleyici_bp.route('/api/predict', methods=['POST'])
def predict():
    """Performs prediction using the locally copied hybrid champion models with aligned features."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body is required"}), 400
        
    sector = data.get('sector')
    currency = data.get('currency', 'USD').upper()
    company = data.get('company')
    period = data.get('period')
    custom_features = data.get('features', {})
    current_profit = float(data.get('current_profit', 0.0))
    mevsim = data.get('mevsim')
    anomali = data.get('anomali')
    
    if not sector or not company or not period:
        return jsonify({"error": "sector, company, and period are required"}), 400
        
    try:
        # Load the Decision Jigsaw Matrix to find selected versions
        matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Main_Karar_Matrisi.xlsx")
        if not os.path.exists(matrix_path):
            matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
            
        if not os.path.exists(matrix_path):
            return jsonify({"error": f"Decision matrix not found locally for {currency}."}), 404
            
        df_dec = get_cached_df(matrix_path, "En_Iyi_Yapboz_Matrisi")
        dec_row = get_dec_row(df_dec, sector)
        if dec_row is None:
            return jsonify({"error": f"Sector {sector} not found in Decision Matrix"}), 404

        stored_sector = str(dec_row.get("Sektör") or dec_row.get("Sektor") or sector)
        cls_yon_ver = str(next((dec_row.get(k) for k in dec_row.index if "cls" in str(k).lower() and ("yn" in str(k).lower() or "yön" in str(k).lower()) and "ver" in str(k).lower()), "V1")).strip()
        cls_kz_ver  = str(next((dec_row.get(k) for k in dec_row.index if "cls" in str(k).lower() and "kz" in str(k).lower() and "ver" in str(k).lower()), "V1")).strip()
        reg_ver     = str(next((dec_row.get(k) for k in dec_row.index if "reg" in str(k).lower() and ("say" in str(k).lower()) and "ver" in str(k).lower()), "V1")).strip()

        # Extract V2 columns/features if V2 is active for either classification
        expected_feats_v2 = []
        if cls_yon_ver == "V2" or cls_kz_ver == "V2":
            df_v2_cols = get_v2_columns(sector, currency)
            meta_cols_v2 = ["Dönem", "Firma Adı", "Anomali_Durumu"]
            target_cols_v2 = [col for col in df_v2_cols if "t+1" in col]
            target_col_v2 = target_cols_v2[0] if target_cols_v2 else None
            expected_feats_v2 = [col for col in df_v2_cols if col not in meta_cols_v2 and col != target_col_v2]
        
        # ── A. REGRESSION PREDICTION (t+1 Net Dönem Karı) ─────────────────────
        pred_val, reg_alg = predict_regression_value(sector, company, period, currency, custom_features, mevsim, anomali)
            
        # ── B. CLASSIFICATION YÖN PREDICTION (Yön Sınıflandırma) ────────────────
        cls_yon_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{stored_sector}_Yon_Tahmini_{currency}.pkb")
        cls_yon_cache = get_cached_model(cls_yon_path)
        if not cls_yon_cache:
            cls_yon_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{sector}_Yon_Tahmini_{currency}.pkb")
            cls_yon_cache = get_cached_model(cls_yon_path)
        if not cls_yon_cache:
            return jsonify({"error": f"Direction classification model not found for {sector}"}), 404
            
        if cls_yon_ver == "V1":
            model_yon = cls_yon_cache["model"]
            scaler_yon = cls_yon_cache.get("scaler", None)
            threshold_yon = cls_yon_cache.get("threshold", 0.5)
            
            expected_feats_yon = cls_yon_cache.get("features", [])
            if not expected_feats_yon:
                if scaler_yon is not None and hasattr(scaler_yon, "feature_names_in_"):
                    expected_feats_yon = list(scaler_yon.feature_names_in_)
                elif hasattr(model_yon, "feature_names_in_"):
                    expected_feats_yon = list(model_yon.feature_names_in_)
                    
            df_aligned_yon = align_features_for_model(sector, company, period, currency, "V1", expected_feats_yon, custom_features, model_yon, mevsim=mevsim, anomali=anomali)
            
            if scaler_yon is not None:
                df_aligned_yon[df_aligned_yon.columns] = scaler_yon.transform(df_aligned_yon)
                
            probs_yon = model_yon.predict_proba(df_aligned_yon)[:, 1]
            pred_yon_val = int(probs_yon[0] >= threshold_yon)
            cls_yon_alg = f"{type(model_yon).__name__} (V1)"
        else:
            models_yon = cls_yon_cache["models"]
            best_name_yon = cls_yon_cache["best_model_name"]
            model_yon = models_yon[best_name_yon]
            
            df_aligned_yon = align_features_for_model(sector, company, period, currency, "V2", expected_feats_v2, custom_features, model_yon, mevsim=mevsim, anomali=anomali)
            df_aligned_yon = scale_v2_features(df_aligned_yon, sector, currency)
            
            pred_yon_val = int(model_yon.predict(df_aligned_yon)[0])
            cls_yon_alg = f"{best_name_yon} (V2)"
            
        # ── C. CLASSIFICATION KAR-ZARAR PREDICTION (Kâr/Zarar Sınıflandırma) ──────
        cls_kz_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{stored_sector}_Kar_Zarar_Tahmini_{currency}.pkb")
        cls_kz_cache = get_cached_model(cls_kz_path)
        if not cls_kz_cache:
            cls_kz_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{sector}_Kar_Zarar_Tahmini_{currency}.pkb")
            cls_kz_cache = get_cached_model(cls_kz_path)
        if not cls_kz_cache:
            return jsonify({"error": f"Profitability classification model not found for {sector}"}), 404
            
        if cls_kz_ver == "V1":
            model_kz = cls_kz_cache["model"]
            scaler_kz = cls_kz_cache.get("scaler", None)
            threshold_kz = cls_kz_cache.get("threshold", 0.5)
            
            expected_feats_kz = cls_kz_cache.get("features", [])
            if not expected_feats_kz:
                if scaler_kz is not None and hasattr(scaler_kz, "feature_names_in_"):
                    expected_feats_kz = list(scaler_kz.feature_names_in_)
                elif hasattr(model_kz, "feature_names_in_"):
                    expected_feats_kz = list(model_kz.feature_names_in_)
                    
            df_aligned_kz = align_features_for_model(sector, company, period, currency, "V1", expected_feats_kz, custom_features, model_kz, mevsim=mevsim, anomali=anomali)
            
            if scaler_kz is not None:
                df_aligned_kz[df_aligned_kz.columns] = scaler_kz.transform(df_aligned_kz)
                
            probs_kz = model_kz.predict_proba(df_aligned_kz)[:, 1]
            pred_kz_val = int(probs_kz[0] >= threshold_kz)
            cls_kz_alg = f"{type(model_kz).__name__} (V1)"
        else:
            models_kz = cls_kz_cache["models"]
            best_name_kz = cls_kz_cache["best_model_name"]
            model_kz = models_kz[best_name_kz]
            
            df_aligned_kz = align_features_for_model(sector, company, period, currency, "V2", expected_feats_v2, custom_features, model_kz, mevsim=mevsim, anomali=anomali)
            df_aligned_kz = scale_v2_features(df_aligned_kz, sector, currency)
            
            pred_kz_val = int(model_kz.predict(df_aligned_kz)[0])
            cls_kz_alg = f"{best_name_kz} (V2)"
            
        reg_dir_val = 1 if pred_val > current_profit else 0
        
        # ── D. FETCH ACTUAL TARGETS FOR PERFORMANCE COMPARISON ────────────────
        actual_reg_val = None
        actual_kz_val = None
        actual_yon_val = None
        
        try:
            unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
            if not os.path.exists(unscaled_path):
                unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
                
            if os.path.exists(unscaled_path):
                df_actual = get_cached_df(unscaled_path, sector)
                row_actual = df_actual[(df_actual["Firma Adı"] == company) & (df_actual["Dönem"] == int(period))]
                if not row_actual.empty:
                    row_actual_dict = row_actual.iloc[0].to_dict()
                    t_cols = [col for col in df_actual.columns if "t+1" in col]
                    if t_cols:
                        t_col = t_cols[0]
                        actual_reg_val = row_actual_dict.get(t_col)
                        if pd.notna(actual_reg_val):
                            actual_reg_val = float(actual_reg_val)
                            
                            df_p = df_actual[df_actual["Dönem"] == int(period)]
                            median_t1 = df_p[t_col].median() if not df_p.empty and t_col in df_p.columns else 0.0
                            actual_kz_val = 1 if actual_reg_val > median_t1 else 0
                            
                            current_profit_col = None
                            for c in ["Net Dönem Karı/Zararı", "Net Dönem Karı"]:
                                if c in df_actual.columns:
                                    current_profit_col = c
                                    break
                            
                            if current_profit_col:
                                curr_prof = row_actual_dict.get(current_profit_col, 0.0)
                            else:
                                curr_prof = current_profit
                                
                            actual_yon_val = 1 if actual_reg_val > curr_prof else 0
        except Exception as ex:
            print(f"Error fetching actual comparison values: {ex}")
            
        return jsonify({
            "regression": {
                "prediction": pred_val,
                "algorithm": reg_alg,
                "version": reg_ver,
                "jigsaw_score": float(dec_row["Reg_Sayısal_Skor (%)"]) if "Reg_Sayısal_Skor (%)" in dec_row else 0.0,
                "jigsaw_mape": float(dec_row["Reg_KZ_Skor (%)"]) if "Reg_KZ_Skor (%)" in dec_row else 0.0,
                "actual": actual_reg_val
            },
            "classification_direction": {
                "prediction": pred_yon_val,
                "algorithm": cls_yon_alg,
                "version": cls_yon_ver,
                "jigsaw_score": float(dec_row["Cls_Yön_Skor (%)"]) if "Cls_Yön_Skor (%)" in dec_row else 0.0,
                "actual": actual_yon_val
            },
            "classification_profitability": {
                "prediction": pred_kz_val,
                "algorithm": cls_kz_alg,
                "version": cls_kz_ver,
                "jigsaw_score": float(dec_row["Cls_KZ_Skor (%)"]) if "Cls_KZ_Skor (%)" in dec_row else 0.0,
                "actual": actual_kz_val
            },
            "derived": {
                "regression_direction": reg_dir_val
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tahminleyici_bp.route('/api/predict_all', methods=['GET'])
def predict_all():
    """Predicts classification targets (K/Z and Yön) for all periods of a given company."""
    sector = request.args.get('sector')
    company = request.args.get('company')
    currency = request.args.get('currency', 'USD').upper()
    
    if not sector or not company:
        return jsonify({"error": "sector and company are required"}), 400
        
    try:
        # 1. Load Jigsaw Decision Matrix
        matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Main_Karar_Matrisi.xlsx")
        if not os.path.exists(matrix_path):
            matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
            
        if not os.path.exists(matrix_path):
            return jsonify({"error": f"Decision matrix not found locally for {currency}."}), 404
            
        df_dec = get_cached_df(matrix_path, "En_Iyi_Yapboz_Matrisi")
        dec_row = get_dec_row(df_dec, sector)
        if dec_row is None:
            return jsonify({"error": f"Sector {sector} not found in Decision Matrix"}), 404

        stored_sector = str(dec_row.get("Sektör") or dec_row.get("Sektor") or sector)
        cls_yon_ver = str(next((dec_row.get(k) for k in dec_row.index if "cls" in str(k).lower() and ("yn" in str(k).lower() or "yön" in str(k).lower()) and "ver" in str(k).lower()), "V1")).strip()
        cls_kz_ver  = str(next((dec_row.get(k) for k in dec_row.index if "cls" in str(k).lower() and "kz" in str(k).lower() and "ver" in str(k).lower()), "V1")).strip()
        
        # 2. Get list of all periods for the company
        v1_path = os.path.join(DATA_DIR, "datasets", "v1", f"2_BIST_{currency}_VIF.xlsx")
        df_v1 = get_cached_df(v1_path, sector)
        company_rows = df_v1[df_v1["Firma Adı"] == company]
        if company_rows.empty:
            return jsonify({"error": f"Company {company} not found in sector {sector}"}), 404
            
        periods = sorted(company_rows["Dönem"].unique().tolist())
        
        # 3. Load Models
        cls_yon_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{stored_sector}_Yon_Tahmini_{currency}.pkb")
        cls_yon_cache = get_cached_model(cls_yon_path)
        if not cls_yon_cache:
            cls_yon_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{sector}_Yon_Tahmini_{currency}.pkb")
            cls_yon_cache = get_cached_model(cls_yon_path)

        cls_kz_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{stored_sector}_Kar_Zarar_Tahmini_{currency}.pkb")
        cls_kz_cache = get_cached_model(cls_kz_path)
        if not cls_kz_cache:
            cls_kz_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{sector}_Kar_Zarar_Tahmini_{currency}.pkb")
            cls_kz_cache = get_cached_model(cls_kz_path)

        if not cls_yon_cache or not cls_kz_cache:
            return jsonify({"error": "Classification models not found"}), 404
            
        # Get expected features
        if cls_yon_ver == "V1":
            model_yon = cls_yon_cache["model"]
            scaler_yon = cls_yon_cache.get("scaler", None)
            threshold_yon = cls_yon_cache.get("threshold", 0.5)
            expected_feats_yon = cls_yon_cache.get("features", [])
            if not expected_feats_yon:
                if scaler_yon is not None and hasattr(scaler_yon, "feature_names_in_"):
                    expected_feats_yon = list(scaler_yon.feature_names_in_)
                elif hasattr(model_yon, "feature_names_in_"):
                    expected_feats_yon = list(model_yon.feature_names_in_)
            cls_yon_alg = f"{type(model_yon).__name__} (V1)"
        else:
            models_yon = cls_yon_cache["models"]
            best_name_yon = cls_yon_cache["best_model_name"]
            model_yon = models_yon[best_name_yon]
            cls_yon_alg = f"{best_name_yon} (V2)"
            
        if cls_kz_ver == "V1":
            model_kz = cls_kz_cache["model"]
            scaler_kz = cls_kz_cache.get("scaler", None)
            threshold_kz = cls_kz_cache.get("threshold", 0.5)
            expected_feats_kz = cls_kz_cache.get("features", [])
            if not expected_feats_kz:
                if scaler_kz is not None and hasattr(scaler_kz, "feature_names_in_"):
                    expected_feats_kz = list(scaler_kz.feature_names_in_)
                elif hasattr(model_kz, "feature_names_in_"):
                    expected_feats_kz = list(model_kz.feature_names_in_)
            cls_kz_alg = f"{type(model_kz).__name__} (V1)"
        else:
            models_kz = cls_kz_cache["models"]
            best_name_kz = cls_kz_cache["best_model_name"]
            model_kz = models_kz[best_name_kz]
            cls_kz_alg = f"{best_name_kz} (V2)"
            
        # V2 expected features
        expected_feats_v2 = []
        if cls_yon_ver == "V2" or cls_kz_ver == "V2":
            df_v2_cols = get_v2_columns(sector, currency)
            meta_cols_v2 = ["Dönem", "Firma Adı", "Anomali_Durumu"]
            target_cols_v2 = [col for col in df_v2_cols if "t+1" in col]
            target_col_v2 = target_cols_v2[0] if target_cols_v2 else None
            expected_feats_v2 = [col for col in df_v2_cols if col not in meta_cols_v2 and col != target_col_v2]

        # Load actuals to calculate metrics
        unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
        if not os.path.exists(unscaled_path):
            unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
            
        df_actual = pd.DataFrame()
        if os.path.exists(unscaled_path):
            df_actual = get_cached_df(unscaled_path, sector)

        results = []
        
        for period in periods:
            period_str = str(period)
            
            # Fetch default values for mevsimsellik and anomali
            row_v1 = company_rows[company_rows["Dönem"] == period].iloc[0].to_dict()
            mevsim = row_v1.get("Mevsimsellik", 1)
            anomali = row_v1.get("Anomali_Durumu", 0)
            
            # A. Predict Yön
            if cls_yon_ver == "V1":
                df_align_yon = align_features_for_model(sector, company, period_str, currency, "V1", expected_feats_yon, {}, model_yon, mevsim=mevsim, anomali=anomali)
                if scaler_yon is not None:
                    df_align_yon[df_align_yon.columns] = scaler_yon.transform(df_align_yon)
                probs_yon = model_yon.predict_proba(df_align_yon)[:, 1]
                pred_yon = int(probs_yon[0] >= threshold_yon)
            else:
                df_align_yon = align_features_for_model(sector, company, period_str, currency, "V2", expected_feats_v2, {}, model_yon, mevsim=mevsim, anomali=anomali)
                df_align_yon = scale_v2_features(df_align_yon, sector, currency)
                pred_yon = int(model_yon.predict(df_align_yon)[0])
                
            # B. Predict K/Z
            if cls_kz_ver == "V1":
                df_align_kz = align_features_for_model(sector, company, period_str, currency, "V1", expected_feats_kz, {}, model_kz, mevsim=mevsim, anomali=anomali)
                if scaler_kz is not None:
                    df_align_kz[df_align_kz.columns] = scaler_kz.transform(df_align_kz)
                probs_kz = model_kz.predict_proba(df_align_kz)[:, 1]
                pred_kz = int(probs_kz[0] >= threshold_kz)
            else:
                df_align_kz = align_features_for_model(sector, company, period_str, currency, "V2", expected_feats_v2, {}, model_kz, mevsim=mevsim, anomali=anomali)
                df_align_kz = scale_v2_features(df_align_kz, sector, currency)
                pred_kz = int(model_kz.predict(df_align_kz)[0])
                
            # C. Fetch Actuals
            actual_kz_val = None
            actual_yon_val = None
            if not df_actual.empty:
                row_act = df_actual[(df_actual["Firma Adı"] == company) & (df_actual["Dönem"] == period)]
                if not row_act.empty:
                    row_act_dict = row_act.iloc[0].to_dict()
                    t_cols = [col for col in df_actual.columns if "t+1" in col]
                    if t_cols:
                        t_col = t_cols[0]
                        act_reg = row_act_dict.get(t_col)
                        if pd.notna(act_reg):
                            # Sector median for K/Z comparison
                            df_p = df_actual[df_actual["Dönem"] == period]
                            median_t1 = df_p[t_col].median() if not df_p.empty and t_col in df_p.columns else 0.0
                            actual_kz_val = 1 if act_reg > median_t1 else 0
                            
                            # Company current profit for Yön comparison
                            curr_prof_col = None
                            for c in df_actual.columns:
                                cn = clean_and_normalize(c)
                                if "netdonemkar" in cn or "netdonemkari" in cn or "netdonemkarizarari" in cn:
                                    if "t+1" not in c:
                                        curr_prof_col = c
                                        break
                            if not curr_prof_col:
                                for c in df_actual.columns:
                                    cn = clean_and_normalize(c)
                                    if "kar" in cn and "t+1" not in c:
                                        curr_prof_col = c
                                        break
                                        
                            if curr_prof_col:
                                curr_prof_val = row_act_dict.get(curr_prof_col, 0.0)
                            else:
                                curr_prof_val = 0.0
                            actual_yon_val = 1 if act_reg > curr_prof_val else 0
                            
            results.append({
                "period": int(period),
                "pred_kz": pred_kz,
                "actual_kz": actual_kz_val,
                "pred_yon": pred_yon,
                "actual_yon": actual_yon_val,
                "mevsim": int(mevsim),
                "anomali": int(anomali)
            })
            
        # D. Narrative commentaries
        valid_kz = [r for r in results if r["actual_kz"] is not None]
        correct_kz = [r for r in valid_kz if r["pred_kz"] == r["actual_kz"]]
        accuracy_kz = (len(correct_kz) / len(valid_kz) * 100) if valid_kz else None
        
        valid_yon = [r for r in results if r["actual_yon"] is not None]
        correct_yon = [r for r in valid_yon if r["pred_yon"] == r["actual_yon"]]
        accuracy_yon = (len(correct_yon) / len(valid_yon) * 100) if valid_yon else None
        
        report_kz = ""
        if accuracy_kz is not None:
            report_kz = (
                f"<strong>{company}</strong> firmasının kârlılık sınıflandırma tahmini (Net Dönem Kârının sektör medyanını aşıp aşmayacağı), "
                f"şampiyon algoritma <strong>{cls_kz_alg}</strong> (Versiyon: {cls_kz_ver}) kullanılarak toplam <strong>{len(periods)} çeyreklik dönem</strong> için analiz edilmiştir.<br><br>"
                f"Modelimiz, gerçek verisi bulunan <strong>{len(valid_kz)} çeyrek</strong> arasından <strong>{len(correct_kz)} çeyrekte</strong> doğru tahminde bulunarak "
                f"<strong>%{accuracy_kz:.1f}</strong> başarı (accuracy) oranı elde etmiştir. Karar matrisinde bu modelin genel sektör başarımı <strong>%{float(dec_row.get('Cls_KZ_Skor (%)', 0)):.1f}</strong> olarak kaydedilmiştir."
            )
        else:
            report_kz = f"{company} firması için kârlılık sınıflandırma analizi tamamlanmıştır. Ancak kıyaslama yapılacak gerçekleşen kâr verisi bulunamamıştır."

        report_yon = ""
        if accuracy_yon is not None:
            report_yon = (
                f"<strong>{company}</strong> firmasının kâr değişim yönü tahmini (Net Dönem Kârının cari döneme göre artıp azalacağı), "
                f"şampiyon algoritma <strong>{cls_yon_alg}</strong> (Versiyon: {cls_yon_ver}) kullanılarak toplam <strong>{len(periods)} çeyreklik dönem</strong> için analiz edilmiştir.<br><br>"
                f"Modelimiz, gerçek verisi bulunan <strong>{len(valid_yon)} çeyrek</strong> arasından <strong>{len(correct_yon)} çeyrekte</strong> doğru yön tahmini yaparak "
                f"<strong>%{accuracy_yon:.1f}</strong> başarı (accuracy) oranı elde etmiştir. Karar matrisinde bu modelin genel sektör başarımı <strong>%{float(dec_row.get('Cls_Yön_Skor (%)', 0)):.1f}</strong> olarak kaydedilmiştir."
            )
        else:
            report_yon = f"{company} firması için kâr değişim yönü analizi tamamlanmıştır. Ancak kıyaslama yapılacak gerçekleşen kâr verisi bulunamamıştır."
            
        return jsonify({
            "sector": sector,
            "company": company,
            "currency": currency,
            "cls_kz_alg": cls_kz_alg,
            "cls_kz_ver": cls_kz_ver,
            "cls_yon_alg": cls_yon_alg,
            "cls_yon_ver": cls_yon_ver,
            "jigsaw_kz_score": float(dec_row.get("Cls_KZ_Skor (%)", 0.0)),
            "jigsaw_yon_score": float(dec_row.get("Cls_Yön_Skor (%)", 0.0)),
            "results": results,
            "accuracy_kz": accuracy_kz,
            "correct_kz_count": len(correct_kz),
            "total_kz_count": len(valid_kz),
            "accuracy_yon": accuracy_yon,
            "correct_yon_count": len(correct_yon),
            "total_yon_count": len(valid_yon),
            "report_kz": report_kz,
            "report_yon": report_yon
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
