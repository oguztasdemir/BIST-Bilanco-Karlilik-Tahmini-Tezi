import sys
import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
from imblearn.over_sampling import SMOTE

currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 7 (Sınıflandırma ve Veri Dengesizliği) for currency: {currency}")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "7_Siniflandirma_Analizi")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "7_Siniflandirma_Analizi")
modeller_dir = os.path.join(ml_dir, "4_modeller", "7_Siniflandirma_Analizi")

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

summary_data = []
writer_perf = pd.ExcelWriter(os.path.join(output_dir, f"Model_Performansi_Siniflandirma_{currency}.xlsx"), engine="xlsxwriter")

def custom_panel_tscv_cls(df, n_splits=5):
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

for sheet in sheet_names:
    print(f"\n==================================================")
    print(f"Running Classification for Sector: {sheet}")
    print(f"==================================================")
    
    df = pd.read_excel(input_path, sheet_name=sheet)
    df = df.reset_index(drop=True)
    
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    # Classification Targets
    y_target_kz = (df[target_col] > 0).astype(int)
    y_target_yon = (df[target_col] > df["Net Dönem Karı/Zararı"]).astype(int)
    
    targets = {
        "Kar_Zarar_Tahmini": (y_target_kz, "Net Dönem Kârı (t+1) > 0"),
        "Yon_Tahmini": (y_target_yon, "Net Dönem Kârı (t+1) > Cari Net Kâr")
    }
    
    train_mask = df["Dönem"] <= 31
    test_mask = df["Dönem"] >= 32
    
    df_train = df[train_mask].copy().reset_index(drop=True)
    df_test = df[test_mask].copy().reset_index(drop=True)
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    X_train = df_train[feature_cols].copy()
    X_test = df_test[feature_cols].copy()
    
    # Train modeller for each target
    for target_name, (y_full, target_desc) in targets.items():
        print(f"\n--- Target: {target_name} ({target_desc}) ---")
        
        y_train = y_full[train_mask].reset_index(drop=True)
        y_test = y_full[test_mask].reset_index(drop=True)
        
        # Apply SMOTE to Training set ONLY if minority class < 40%
        minority_ratio = y_train.value_counts(normalize=True).min()
        X_train_res, y_train_res = X_train, y_train
        if minority_ratio < 0.40 and len(y_train) > 50:
            print(f"  Minority class ratio is {minority_ratio:.2f}. Applying SMOTE...")
            smote = SMOTE(random_state=42)
            try:
                X_train_res, y_train_res = smote.fit_resample(X_train[numeric_features], y_train)
                # Ensure correct structure
                X_train_res = pd.DataFrame(X_train_res, columns=numeric_features)
                # Keep Dönem as proxy for splits if needed (or we don't do TSCV on resampled data directly because it mixes time)
            except Exception as e:
                print(f"  SMOTE failed ({e}). Proceeding without SMOTE.")
                
        # Since SMOTE destroys time index, we use standard Stratified CV or just rely on Optuna with the original splits 
        # But wait, we can just apply SMOTE inside the CV loop to prevent data leakage perfectly!
        
        cache_file = os.path.join(modeller_dir, f"champion_{sheet}_{target_name}_{currency}.pkb")
        if os.path.exists(cache_file):
            print(f"Found cached classification models for {target_name}. Loading...")
            with open(cache_file, "rb") as f:
                cache_data = pickle.load(f)
            models = cache_data["models"]
            best_model_name = cache_data.get("best_model_name", "")
        else:
            models = {}
            splits = custom_panel_tscv_cls(df_train, n_splits=3)
            
            # Simple SVM
            models["SVM"] = SVC(probability=True, random_state=42)
            
            def tune_tree_clf(model_class, param_space_func, fixed_params, X, y, splits):
                def objective(trial):
                    params = {**param_space_func(trial), **fixed_params}
                    scores = []
                    for train_idx, val_idx in splits:
                        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
                        X_va, y_va = X.iloc[val_idx], y.iloc[val_idx]
                        
                        # Apply SMOTE strictly to train split
                        if y_tr.value_counts(normalize=True).min() < 0.40:
                            try:
                                sm = SMOTE(random_state=42)
                                X_tr, y_tr = sm.fit_resample(X_tr[numeric_features], y_tr)
                                X_tr = pd.DataFrame(X_tr, columns=numeric_features)
                            except: pass
                            
                        mdl = model_class(**params)
                        # Ensure X_tr only has numeric features
                        mdl.fit(X_tr[numeric_features], y_tr)
                        preds = mdl.predict(X_va[numeric_features])
                        scores.append(f1_score(y_va, preds, average='macro'))
                    return np.mean(scores)
                
                study = optuna.create_study(direction="maximize")
                study.optimize(objective, n_trials=5) # 5 trials for speed
                return model_class(**{**study.best_params, **fixed_params})
            
            print("Tuning Random Forest Classifier...")
            models["RF"] = tune_tree_clf(RandomForestClassifier, lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 100)}, {"random_state": 42}, X_train, y_train, splits)
            print("Tuning XGBoost Classifier...")
            models["XGBoost"] = tune_tree_clf(xgb.XGBClassifier, lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 100)}, {"random_state": 42, "eval_metric": "logloss"}, X_train, y_train, splits)
            print("Tuning LightGBM Classifier...")
            models["LightGBM"] = tune_tree_clf(lgb.LGBMClassifier, lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 100)}, {"random_state": 42, "verbosity": -1}, X_train, y_train, splits)
            print("Tuning CatBoost Classifier...")
            models["CatBoost"] = tune_tree_clf(cb.CatBoostClassifier, lambda t: {"iterations": t.suggest_int("iterations", 50, 100)}, {"random_seed": 42, "verbose": 0}, X_train, y_train, splits)
            
            # Evaluate to find champion
            val_scores = {}
            from sklearn.base import clone
            for name, model in models.items():
                scores = []
                for train_idx, val_idx in splits:
                    X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
                    X_va, y_va = X_train.iloc[val_idx], y_train.iloc[val_idx]
                    if y_tr.value_counts(normalize=True).min() < 0.40:
                        try:
                            sm = SMOTE(random_state=42)
                            X_tr, y_tr = sm.fit_resample(X_tr[numeric_features], y_tr)
                            X_tr = pd.DataFrame(X_tr, columns=numeric_features)
                        except: pass
                    mdl = clone(model)
                    mdl.fit(X_tr[numeric_features], y_tr)
                    preds = mdl.predict(X_va[numeric_features])
                    scores.append(f1_score(y_va, preds, average='macro'))
                val_scores[name] = np.mean(scores)
                
            best_model_name = max(val_scores, key=val_scores.get)
            
            # Final fit on whole resampled train
            for name, model in models.items():
                model.fit(X_train_res[numeric_features], y_train_res)
                
            cache_data = {"models": models, "best_model_name": best_model_name}
            with open(cache_file, "wb") as f:
                pickle.dump(cache_data, f)
                
        # Generate Test Metrics
        champ_model = models[best_model_name]
        preds_test = champ_model.predict(X_test[numeric_features])
        acc = accuracy_score(y_test, preds_test)
        f1 = f1_score(y_test, preds_test, average='macro')
        
        summary_data.append({
            "Sektör": sheet,
            "Hedef Değişken": target_name,
            "En İyi Model": best_model_name,
            "Train Gözlem": len(y_train),
            "Test Gözlem": len(y_test),
            "Test Accuracy (%)": round(acc * 100, 2),
            "Test F1-Score (%)": round(f1 * 100, 2)
        })
        
        # Save details sheet
        df_out = df_test[["Firma Adı", "Dönem"]].copy()
        df_out["Gerçek"] = y_test
        df_out["Tahmin"] = preds_test
        sheet_n = f"{sheet[:20]}_{target_name[:5]}"
        df_out.to_excel(writer_perf, sheet_name=sheet_n, index=False)
        
        # Plot Confusion Matrix
        cm = confusion_matrix(y_test, preds_test)
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title(f"{sheet} - {target_name}\nEn İyi Model: {best_model_name} (Acc: {acc:.2f})")
        plt.ylabel('Gerçek Sınıf')
        plt.xlabel('Tahmin Edilen Sınıf')
        plt.tight_layout()
        plt.savefig(os.path.join(gorseller_dir, f"CM_{sheet}_{target_name}_{currency}.png"), dpi=300)
        plt.close()

summary_df = pd.DataFrame(summary_data)
worksheet = writer_perf.book.add_worksheet("Genel_Ozet")
writer_perf.sheets["Genel_Ozet"] = worksheet
summary_df.to_excel(writer_perf, sheet_name="Genel_Ozet", index=False)
writer_perf.close()

for target in ["Kar_Zarar_Tahmini", "Yon_Tahmini"]:
    tgt_df = summary_df[summary_df["Hedef Değişken"] == target]
    plt.figure(figsize=(12, 6))
    ax = sns.barplot(data=tgt_df, x="Sektör", y="Test Accuracy (%)", palette="Set2")
    for p in ax.patches:
        ax.annotate(f"{p.get_height():.2f}%", (p.get_x() + p.get_width() / 2., p.get_height()), ha='center', va='center', xytext=(0, 9), textcoords='offset points', fontweight='bold')
    plt.title(f"{target} Sınıflandırma Başarısı ({currency})")
    plt.xticks(rotation=45, ha='right')
    plt.ylim(0, 110)
    plt.tight_layout()
    plt.savefig(os.path.join(gorseller_dir, f"Performans_Karsilastirma_{target}.png"), dpi=300)
    plt.close()

print("Step 7 Classification completed successfully!")
