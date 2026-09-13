import sys
import os
import traceback
import pandas as pd

sys.path.insert(0, '8_Arayuz')

from main import app, get_v2_scaler, get_company_features, align_features_for_model, scale_v2_features, get_cached_model

sector = 'FİNANS_VE_YATIRIM'
company = 'A1CAP'
period = '39'
currency = 'USD'

with app.test_client() as client:
    res_feats = client.get(f'/api/company_features?sector={sector}&company={company}&period={period}&currency={currency}&version=V2')
    feats_data = res_feats.get_json()
    custom_features = feats_data["features"]
    mevsim = feats_data.get("current_mevsim", 1)
    anomali = feats_data.get("current_anomali", 0)
    
    print("Features:", list(custom_features.keys()))
    
    # Let's inspect the models and scaler
    cls_kz_path = os.path.join("8_Arayuz", "models", "4_Siniflandirma_Analizi", f"champion_{sector}_Kar_Zarar_Tahmini_{currency}.pkb")
    cls_kz_cache = get_cached_model(cls_kz_path)
    models_kz = cls_kz_cache["models"]
    best_name_kz = cls_kz_cache["best_model_name"]
    model_kz = models_kz[best_name_kz]
    
    print("Best KZ model name:", best_name_kz)
    if hasattr(model_kz, "feature_names_in_"):
        print("Model feature_names_in_:", list(model_kz.feature_names_in_))
    else:
        print("Model has no feature_names_in_")
        
    scaler, num_feats = get_v2_scaler(sector, currency)
    print("Scaler:", scaler)
    print("Scaler num_feats:", num_feats)
    
    # Now let's run align and scale and print traceback
    try:
        from main import get_v2_columns
        df_v2_cols = get_v2_columns(sector, currency)
        meta_cols_v2 = ["Dönem", "Firma Adı", "Anomali_Durumu"]
        target_cols_v2 = [col for col in df_v2_cols if "t+1" in col]
        target_col_v2 = target_cols_v2[0] if target_cols_v2 else None
        expected_feats_v2 = [col for col in df_v2_cols if col not in meta_cols_v2 and col != target_col_v2]
        
        df_aligned_kz = align_features_for_model(sector, company, period, currency, "V2", expected_feats_v2, custom_features, model_kz, mevsim=mevsim, anomali=anomali)
        print("df_aligned_kz columns:", list(df_aligned_kz.columns))
        print("df_aligned_kz shape:", df_aligned_kz.shape)
        
        df_scaled = scale_v2_features(df_aligned_kz, sector, currency)
        print("Success scale! df_scaled shape:", df_scaled.shape)
    except Exception as e:
        print("CRASHED during align/scale:")
        traceback.print_exc()
