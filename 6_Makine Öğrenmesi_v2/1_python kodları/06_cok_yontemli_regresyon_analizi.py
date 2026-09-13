import sys
import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

from sklearn.preprocessing import RobustScaler
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
import xgboost as xgb
import lightgbm as lgb
import catboost as cb

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 6 (Çok Yöntemli Regresyon) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "6_Regresyon_Analizi")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "6_Regresyon_Analizi")
modeller_dir = os.path.join(ml_dir, "4_modeller", "6_Regresyon_Analizi")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)
os.makedirs(modeller_dir, exist_ok=True)

# Clear old outputs
for file in os.listdir(output_dir):
    try: os.remove(os.path.join(output_dir, file))
    except: pass
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

input_path = os.path.join(islenmis_dir, f"5_BIST_{currency}_Scaled.xlsx")
if not os.path.exists(input_path):
    print(f"Hata: {input_path} bulunamadı! Lütfen önce Adım 5'i çalıştırın.")
    sys.exit(1)

print(f"Loading {input_path}...")
xl = pd.ExcelFile(input_path)
sheet_names = xl.sheet_names

def calc_success_score(direction_acc, kz_acc, mape):
    return (direction_acc * 0.4) + (kz_acc * 0.4) + (max(0.0, 1.0 - mape) * 0.2)

def custom_panel_tscv(df, n_splits=5):
    periods = sorted(df['Dönem'].unique())
    n_periods = len(periods)
    min_train_periods = 12
    val_size = (n_periods - min_train_periods) // n_splits
    if val_size < 1:
        val_size = 1
        
    splits = []
    for i in range(n_splits):
        val_start_idx = min_train_periods + i * val_size
        if i == n_splits - 1:
            val_periods = periods[val_start_idx:]
        else:
            val_periods = periods[val_start_idx : val_start_idx + val_size]
            
        train_periods = [p for p in periods if p < min(val_periods)]
        
        train_idx = df[df['Dönem'].isin(train_periods)].index.tolist()
        val_idx = df[df['Dönem'].isin(val_periods)].index.tolist()
        splits.append((train_idx, val_idx))
    return splits

model_perf_summary_train = []
model_perf_summary_test = []
mape_dist_summary = []

writer_perf = pd.ExcelWriter(os.path.join(output_dir, f"Model_Performansi_{currency}.xlsx"), engine="xlsxwriter")
writer_mape = pd.ExcelWriter(os.path.join(output_dir, f"Firma_Bazli_MAPE_Analizi_{currency}.xlsx"), engine="xlsxwriter")
writer_yontem = pd.ExcelWriter(os.path.join(output_dir, f"Yontem_Bazli_Basari_Analizi_{currency}.xlsx"), engine="xlsxwriter")

for sheet in sheet_names:
    print(f"\n==================================================")
    print(f"Running Regression for Sector: {sheet}")
    print(f"==================================================")
    
    df = pd.read_excel(input_path, sheet_name=sheet)
    df = df.reset_index(drop=True)
    
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    train_mask = df["Dönem"] <= 31
    test_mask = df["Dönem"] >= 32
    
    df_train = df[train_mask].copy().reset_index(drop=True)
    df_test = df[test_mask].copy().reset_index(drop=True)
    
    X_train = df_train[feature_cols].copy()
    y_train = df_train[target_col].copy()
    X_test = df_test[feature_cols].copy()
    y_test = df_test[target_col].copy()
    
    cache_file = os.path.join(modeller_dir, f"champion_{sheet}_{currency}.pkb")
    cache_loaded = False
    
    if os.path.exists(cache_file):
        try:
            print(f"Found cached models for {sheet}. Loading...")
            with open(cache_file, "rb") as f:
                cache_data = pickle.load(f)
            models = cache_data["models"]
            best_model_name = cache_data.get("best_model_name", "")
            best_val_r2 = cache_data.get("best_val_r2", 0.0)
            cache_loaded = True
        except Exception as e:
            print(f"Failed to load cache: {e}. Re-training...")
            
    if not cache_loaded:
        print("Training 11 models with CV and Optuna (10 trials for trees)...")
        models = {}
        splits = custom_panel_tscv(df_train, n_splits=5)
        
        models["Ridge"] = Ridge()
        models["Lasso"] = Lasso(alpha=0.1, max_iter=10000)
        models["ElasticNet"] = ElasticNet(alpha=0.1, l1_ratio=0.5, max_iter=10000)
        models["SVR"] = TransformedTargetRegressor(regressor=SVR(C=1.0, epsilon=0.1), transformer=RobustScaler())
        models["KNN"] = KNeighborsRegressor(n_neighbors=5)
        
        def tune_tree_model(model_class, param_space_func, fixed_params, X, y, splits):
            def objective(trial):
                params = {**param_space_func(trial), **fixed_params}
                scores = []
                for train_idx, val_idx in splits:
                    X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
                    X_va, y_va = X.iloc[val_idx], y.iloc[val_idx]
                    mdl = model_class(**params)
                    mdl.fit(X_tr, y_tr)
                    preds = mdl.predict(X_va)
                    rmse = np.sqrt(np.mean((y_va - preds) ** 2))
                    scores.append(rmse)
                return np.mean(scores)
            
            study = optuna.create_study(direction="minimize")
            study.optimize(objective, n_trials=10)
            return model_class(**{**study.best_params, **fixed_params})
            
        print("Tuning Random Forest...")
        models["RF"] = tune_tree_model(
            RandomForestRegressor,
            lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 150), "max_depth": t.suggest_int("max_depth", 3, 8)},
            {"random_state": 42}, X_train, y_train, splits
        )
        print("Tuning Extra Trees...")
        models["Extra_Trees"] = tune_tree_model(
            ExtraTreesRegressor,
            lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 150), "max_depth": t.suggest_int("max_depth", 3, 8)},
            {"random_state": 42}, X_train, y_train, splits
        )
        print("Tuning Gradient Boosting...")
        models["GBR"] = tune_tree_model(
            GradientBoostingRegressor,
            lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 150), "learning_rate": t.suggest_float("learning_rate", 0.01, 0.1), "max_depth": t.suggest_int("max_depth", 2, 6)},
            {"random_state": 42}, X_train, y_train, splits
        )
        print("Tuning XGBoost...")
        models["XGBoost"] = tune_tree_model(
            xgb.XGBRegressor,
            lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 150), "learning_rate": t.suggest_float("learning_rate", 0.01, 0.1), "max_depth": t.suggest_int("max_depth", 2, 6)},
            {"random_state": 42}, X_train, y_train, splits
        )
        print("Tuning LightGBM...")
        models["LightGBM"] = tune_tree_model(
            lgb.LGBMRegressor,
            lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 150), "learning_rate": t.suggest_float("learning_rate", 0.01, 0.1), "max_depth": t.suggest_int("max_depth", 2, 6)},
            {"verbosity": -1, "random_state": 42}, X_train, y_train, splits
        )
        print("Tuning CatBoost...")
        models["CatBoost"] = tune_tree_model(
            cb.CatBoostRegressor,
            lambda t: {"iterations": t.suggest_int("iterations", 50, 150), "learning_rate": t.suggest_float("learning_rate", 0.01, 0.1), "depth": t.suggest_int("depth", 2, 6)},
            {"verbose": 0, "random_seed": 42}, X_train, y_train, splits
        )
        
        val_r2_scores = {}
        from sklearn.base import clone
        for name, model in models.items():
            r2_scores = []
            for train_idx, val_idx in splits:
                X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
                X_va, y_va = X_train.iloc[val_idx], y_train.iloc[val_idx]
                mdl = clone(model)
                mdl.fit(X_tr, y_tr)
                preds = mdl.predict(X_va)
                mean_y_va = np.mean(y_va)
                if np.sum((y_va - mean_y_va)**2) == 0:
                    r2 = 0.0
                else:
                    r2 = 1.0 - (np.sum((y_va - preds)**2) / np.sum((y_va - mean_y_va)**2))
                r2_scores.append(r2)
            val_r2_scores[name] = np.mean(r2_scores)
            
        best_model_name = max(val_r2_scores, key=val_r2_scores.get)
        best_val_r2 = val_r2_scores[best_model_name]
        
        print("Fitting all models on the entire training set...")
        for name, model in models.items():
            model.fit(X_train, y_train)
            
        cache_data = {
            "models": models,
            "best_model_name": best_model_name,
            "best_val_r2": best_val_r2
        }
        with open(cache_file, "wb") as f:
            pickle.dump(cache_data, f)
            
    best_test_mape = 999.0
    model_predictions_test = {}
    model_predictions_train = {}
    
    for name, model in models.items():
        model_predictions_train[name] = model.predict(X_train)
        preds_test = model.predict(X_test)
        model_predictions_test[name] = preds_test
        non_zero_mask = y_test != 0
        mape_val = np.mean(np.abs((y_test[non_zero_mask] - preds_test[non_zero_mask]) / y_test[non_zero_mask]))
        if name == best_model_name:
            best_test_mape = mape_val
            
    print(f"Sector {sheet} Champion: {best_model_name} (Val R2: {best_val_r2:.4f}, Test MAPE: {best_test_mape * 100:.2f}%)")
    
    df_yontem = df_test[["Firma Adı", "Dönem", target_col]].copy()
    df_yontem.columns = ["Firma adı", "Dönem no (t)", "t+1 gerçek kar"]
    df_yontem["t gerçek kar"] = df_test["Net Dönem Karı/Zararı"].values
    
    for name in models.keys():
        df_yontem[f"{name} tahmini"] = model_predictions_test[name]
        
    champ_train_preds = model_predictions_train[best_model_name]
    champ_test_preds = model_predictions_test[best_model_name]
    
    train_direction_acc = np.mean((df_train[target_col] > df_train["Net Dönem Karı/Zararı"]) == (champ_train_preds > df_train["Net Dönem Karı/Zararı"]))
    train_kz_acc = np.mean((df_train[target_col] > 0) == (champ_train_preds > 0))
    train_non_zero = df_train[target_col] != 0
    train_mape = np.mean(np.abs((df_train.loc[train_non_zero, target_col] - champ_train_preds[train_non_zero]) / df_train.loc[train_non_zero, target_col]))
    train_success = calc_success_score(train_direction_acc, train_kz_acc, train_mape)
    
    test_direction_acc = np.mean((df_test[target_col] > df_test["Net Dönem Karı/Zararı"]) == (champ_test_preds > df_test["Net Dönem Karı/Zararı"]))
    test_kz_acc = np.mean((df_test[target_col] > 0) == (champ_test_preds > 0))
    test_non_zero = df_test[target_col] != 0
    test_mape = np.mean(np.abs((df_test.loc[test_non_zero, target_col] - champ_test_preds[test_non_zero]) / df_test.loc[test_non_zero, target_col]))
    test_success = calc_success_score(test_direction_acc, test_kz_acc, test_mape)
    
    model_perf_summary_train.append({
        "Sektör adı": sheet, "Veri adet": len(df_train),
        "Ortalama K/Z %": round(train_kz_acc * 100, 2), "Ortalama Yön %": round(train_direction_acc * 100, 2),
        "MAPE %": round(train_mape * 100, 2), "Başarı Skoru": round(train_success, 4), "En iyi yöntem": best_model_name
    })
    model_perf_summary_test.append({
        "Sektör adı": sheet, "Veri adet": len(df_test),
        "Ortalama K/Z %": round(test_kz_acc * 100, 2), "Ortalama Yön %": round(test_direction_acc * 100, 2),
        "MAPE %": round(test_mape * 100, 2), "Başarı Skoru": round(test_success, 4), "En iyi yöntem": best_model_name
    })
    
    mape_test = np.abs((df_test[target_col] - champ_test_preds) / np.where(df_test[target_col] == 0, 1.0, df_test[target_col]))
    c_0_10 = np.sum(mape_test <= 0.10); c_10_50 = np.sum((mape_test > 0.10) & (mape_test <= 0.50))
    c_50_100 = np.sum((mape_test > 0.50) & (mape_test <= 1.0)); c_100_500 = np.sum((mape_test > 1.0) & (mape_test <= 5.0))
    c_500_1000 = np.sum((mape_test > 5.0) & (mape_test <= 10.0)); c_above_1000 = np.sum(mape_test > 10.0)
    
    mape_dist_summary.append({
        "Sektör adı": sheet, "Toplam veri": len(df_test), "%0-10": c_0_10, "%10-50": c_10_50,
        "%50-100": c_50_100, "%100-500": c_100_500, "%500-1000": c_500_1000, "+%1000": c_above_1000
    })
    
    df_perf_sheet = df_test[["Net Dönem Karı/Zararı", target_col]].copy()
    df_perf_sheet.columns = ["t. dönemin gerçek net karı", "t+1. dönemin gerçek net karı"]
    df_perf_sheet["t+1. dönemin tahmini net karı"] = champ_test_preds
    df_perf_sheet["gerçekteki yönü"] = np.where(df_perf_sheet["t+1. dönemin gerçek net karı"] > df_perf_sheet["t. dönemin gerçek net karı"], 1, -1)
    df_perf_sheet["tahmindeki yönü"] = np.where(df_perf_sheet["t+1. dönemin tahmini net karı"] > df_perf_sheet["t. dönemin gerçek net karı"], 1, -1)
    df_perf_sheet["tahmin ve gerçek uyumlu yönde bildi mi"] = np.where(df_perf_sheet["gerçekteki yönü"] == df_perf_sheet["tahmindeki yönü"], 1, 0)
    df_perf_sheet["Kar Zarar tahminini bildi mi"] = np.where((df_perf_sheet["t+1. dönemin gerçek net karı"] > 0) == (df_perf_sheet["t+1. dönemin tahmini net karı"] > 0), 1, 0)
    df_perf_sheet["MAPE hatası"] = mape_test
    df_perf_sheet["Başarı Skoru"] = (df_perf_sheet["tahmin ve gerçek uyumlu yönde bildi mi"] * 0.4) + (df_perf_sheet["Kar Zarar tahminini bildi mi"] * 0.4) + ((1.0 - df_perf_sheet["MAPE hatası"]).clip(lower=0.0) * 0.2)
    df_perf_sheet["En başarılı yöntem"] = best_model_name
    df_perf_sheet.to_excel(writer_perf, sheet_name=sheet, index=False)
    
    df_mape_sheet = df_test[["Firma Adı", "Dönem"]].copy()
    df_mape_sheet["MAPE"] = mape_test
    df_mape_pivot = df_mape_sheet.pivot(index="Firma Adı", columns="Dönem", values="MAPE")
    df_mape_pivot["Ortalama Mape oranı"] = df_mape_pivot.mean(axis=1)
    df_mape_pivot = df_mape_pivot.sort_values(by="Ortalama Mape oranı", ascending=False)
    df_mape_pivot.columns = [f"Firmanın {col}. döneminin MAPE yüzdesi" if isinstance(col, int) else col for col in df_mape_pivot.columns]
    df_mape_final = df_mape_pivot.reset_index()
    df_mape_final.rename(columns={"Firma Adı": "Firma adı"}, inplace=True)
    df_mape_final.insert(0, "Firma dönem no", range(1, len(df_mape_final) + 1))
    df_mape_final.to_excel(writer_mape, sheet_name=sheet, index=False)
    
    df_yontem["En iyi sonucu hangi yöntem verdiyse"] = best_model_name
    df_yontem["gerçekteki yönü"] = df_perf_sheet["gerçekteki yönü"].values
    df_yontem["tahmindeki yönü"] = df_perf_sheet["tahmindeki yönü"].values
    df_yontem["tahmin ve gerçek uyumlu yönde bildi mi"] = df_perf_sheet["tahmin ve gerçek uyumlu yönde bildi mi"].values
    df_yontem["Kar Zarar tahminini bildi mi"] = df_perf_sheet["Kar Zarar tahminini bildi mi"].values
    df_yontem["MAPE hatası"] = df_perf_sheet["MAPE hatası"].values
    df_yontem["Başarı Skoru"] = df_perf_sheet["Başarı Skoru"].values
    df_yontem.to_excel(writer_yontem, sheet_name=sheet, index=False)
    
    plt.figure(figsize=(12, 6))
    plt.scatter(df_perf_sheet["t+1. dönemin gerçek net karı"], df_perf_sheet["t+1. dönemin tahmini net karı"], alpha=0.6, color="#1abc9c")
    max_val = max(df_perf_sheet["t+1. dönemin gerçek net karı"].max(), df_perf_sheet["t+1. dönemin tahmini net karı"].max())
    min_val = min(df_perf_sheet["t+1. dönemin gerçek net karı"].min(), df_perf_sheet["t+1. dönemin tahmini net karı"].min())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', label="Mükemmel Uyum")
    plt.title(f"{sheet} - Gerçek vs Tahmini Net Dönem Karı (t+1)")
    plt.xlabel("Gerçek Net Dönem Karı (t+1)")
    plt.ylabel("Tahmin Edilen Net Dönem Karı (t+1)")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.6)
    
    import matplotlib.ticker as ticker
    ax = plt.gca()
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(os.path.join(gorseller_dir, f"Scatter_Gercek_vs_Tahmin_{sheet}.png"), dpi=300)
    plt.close()
    
summary_train_df = pd.DataFrame(model_perf_summary_train)
summary_test_df = pd.DataFrame(model_perf_summary_test)
summary_mape_dist = pd.DataFrame(mape_dist_summary)

summary_train_df.columns = ["sektör adı", "Kaç adet veri kullanıldığı", "Ortalama Kar Zarar yüzdesi", "Ortalama Yön Bilme Yüzdesi", "MAPE yüzdesi", "Başarı Skoru", "en başarılı yöntem hangisi"]
summary_test_df.columns = ["sektör adı", "Kaç adet veri kullanıldığı", "Ortalama Kar Zarar yüzdesi", "Ortalama Yön Bilme yüzdesi", "MAPE yüzdesi", "Başarı Skoru", "en başarılı yöntem hangisi"]
summary_mape_dist.columns = ["Sektör adı", "Toplam veri", "%0-10 MAPE", "%10 - 50 MAPE", "%50-100 MAPE", "%100-500 MAPE", "%500-1000 MAPE", "+%1000 MAPE"]

worksheet = writer_perf.book.add_worksheet("Genel Özet")
writer_perf.sheets["Genel Özet"] = worksheet

worksheet.write_string(0, 0, "A) Train Tablosu")
summary_train_df.to_excel(writer_perf, sheet_name="Genel Özet", startrow=1, index=False)

start_test = len(summary_train_df) + 4
worksheet.write_string(start_test - 1, 0, "B) Test Tablosu")
summary_test_df.to_excel(writer_perf, sheet_name="Genel Özet", startrow=start_test, index=False)

start_mape = start_test + len(summary_test_df) + 4
worksheet.write_string(start_mape - 1, 0, "C) MAPE Tablosu")
summary_mape_dist.to_excel(writer_perf, sheet_name="Genel Özet", startrow=start_mape, index=False)

writer_perf.close()
writer_mape.close()
writer_yontem.close()

plt.figure(figsize=(12, 6))
ax = sns.barplot(data=summary_test_df, x="sektör adı", y="Başarı Skoru", palette="coolwarm")
for p in ax.patches:
    ax.annotate(f"{p.get_height():.4f}", 
                (p.get_x() + p.get_width() / 2., p.get_height()), 
                ha='center', va='center', xytext=(0, 9), textcoords='offset points', fontsize=10, fontweight='bold')
plt.title("Sektörler Arası Regresyon Şampiyon Modellerinin Test Başarı Skorları")
plt.xticks(rotation=45, ha="right")
plt.ylabel("Başarı Skoru")
plt.ylim(0, 1.1)
plt.tight_layout()
plt.savefig(os.path.join(gorseller_dir, "Sektorel_Basari_Skorlari_Ozet.png"), dpi=300)
plt.close()

print("Step 6 Regression completed successfully!")
