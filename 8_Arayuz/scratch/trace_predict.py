import sys
import os
import traceback
import pandas as pd

sys.path.insert(0, '8_Arayuz')

from main import app, predict_regression_value, get_v2_scaler, get_company_features, align_features_for_model, scale_v2_features, get_cached_model, get_v2_columns

sector = 'İNŞAAT_VE_GAYRİMENKUL'
company = 'ADESE'
period = '39'
currency = 'USD'

with app.test_client() as client:
    res_feats = client.get(f'/api/company_features?sector={sector}&company={company}&period={period}&currency={currency}&version=V2')
    feats_data = res_feats.get_json()
    custom_features = feats_data["features"]
    mevsim = feats_data.get("current_mevsim", 1)
    anomali = feats_data.get("current_anomali", 0)
    current_profit = feats_data.get("current_profit", 0.0)

    # 1. Test Regression
    print("\n--- Testing Regression ---")
    try:
        pred_val, reg_alg = predict_regression_value(sector, company, period, currency, custom_features, mevsim, anomali)
        print("Regression Success:", pred_val)
    except Exception as e:
        print("Regression CRASHED:")
        traceback.print_exc()

    # 2. Test Direction (Yön)
    print("\n--- Testing Direction (Yön) ---")
    try:
        from main import MODELS_DIR, get_v2_columns
        df_dec = pd.read_excel('8_Arayuz/data/metrics/2_BIST_USD_Hibrit_Karar_Matrisi.xlsx', sheet_name='En_Iyi_Yapboz_Matrisi')
        dec_row = df_dec[df_dec["Sektör"] == sector].iloc[0]
        cls_yon_ver = dec_row["Cls_Yön_Versiyon"]
        print("Direction version:", cls_yon_ver)
        
        cls_yon_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{sector}_Yon_Tahmini_{currency}.pkb")
        cls_yon_cache = get_cached_model(cls_yon_path)
        
        if cls_yon_ver == "V1":
            model_yon = cls_yon_cache["model"]
            scaler_yon = cls_yon_cache.get("scaler", None)
            expected_feats_yon = cls_yon_cache.get("features", [])
            df_aligned_yon = align_features_for_model(sector, company, period, currency, "V1", expected_feats_yon, custom_features, model_yon, mevsim=mevsim, anomali=anomali)
            if scaler_yon is not None:
                df_aligned_yon[df_aligned_yon.columns] = scaler_yon.transform(df_aligned_yon)
            print("V1 Direction Success")
        else:
            models_yon = cls_yon_cache["models"]
            best_name_yon = cls_yon_cache["best_model_name"]
            model_yon = models_yon[best_name_yon]
            df_v2_cols = get_v2_columns(sector, currency)
            meta_cols_v2 = ["Dönem", "Firma Adı", "Anomali_Durumu"]
            target_cols_v2 = [col for col in df_v2_cols if "t+1" in col]
            target_col_v2 = target_cols_v2[0] if target_cols_v2 else None
            expected_feats_v2 = [col for col in df_v2_cols if col not in meta_cols_v2 and col != target_col_v2]
            df_aligned_yon = align_features_for_model(sector, company, period, currency, "V2", expected_feats_v2, custom_features, model_yon, mevsim=mevsim, anomali=anomali)
            df_aligned_yon = scale_v2_features(df_aligned_yon, sector, currency)
            print("V2 Direction Success")
    except Exception as e:
        print("Direction CRASHED:")
        traceback.print_exc()

    # 3. Test Profitability (K/Z)
    print("\n--- Testing Profitability (K/Z) ---")
    try:
        cls_kz_ver = dec_row["Cls_KZ_Versiyon"]
        print("KZ version:", cls_kz_ver)
        cls_kz_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{sector}_Kar_Zarar_Tahmini_{currency}.pkb")
        cls_kz_cache = get_cached_model(cls_kz_path)
        
        if cls_kz_ver == "V1":
            model_kz = cls_kz_cache["model"]
            scaler_kz = cls_kz_cache.get("scaler", None)
            expected_feats_kz = cls_kz_cache.get("features", [])
            df_aligned_kz = align_features_for_model(sector, company, period, currency, "V1", expected_feats_kz, custom_features, model_kz, mevsim=mevsim, anomali=anomali)
            if scaler_kz is not None:
                print("Scaling with scaler_kz type:", type(scaler_kz))
                df_aligned_kz[df_aligned_kz.columns] = scaler_kz.transform(df_aligned_kz)
            print("V1 KZ Success")
        else:
            models_kz = cls_kz_cache["models"]
            best_name_kz = cls_kz_cache["best_model_name"]
            model_kz = models_kz[best_name_kz]
            df_v2_cols = get_v2_columns(sector, currency)
            meta_cols_v2 = ["Dönem", "Firma Adı", "Anomali_Durumu"]
            target_cols_v2 = [col for col in df_v2_cols if "t+1" in col]
            target_col_v2 = target_cols_v2[0] if target_cols_v2 else None
            expected_feats_v2 = [col for col in df_v2_cols if col not in meta_cols_v2 and col != target_col_v2]
            df_aligned_kz = align_features_for_model(sector, company, period, currency, "V2", expected_feats_v2, custom_features, model_kz, mevsim=mevsim, anomali=anomali)
            df_aligned_kz = scale_v2_features(df_aligned_kz, sector, currency)
            print("V2 KZ Success")
    except Exception as e:
        print("Profitability (K/Z) CRASHED:")
        traceback.print_exc()
