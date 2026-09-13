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
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, roc_curve
import xgboost as xgb
import lightgbm as lgb
import catboost as cb

# Check SMOTE availability
try:
    from imblearn.over_sampling import SMOTE
    has_smote = True
except ImportError:
    has_smote = False

# Add root folder to sys.path to import kullanici.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# Define paths dynamically using kb.klasor
ml_dir = os.path.join(kb.klasor, "5_Makine Öğrenmesi_v1")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "4_Siniflandirma_Analizi")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "4_Siniflandirma_Analizi")
modeller_dir = os.path.join(ml_dir, "4_modeller", "4_Siniflandirma_Analizi")

# Ensure target directories exist
os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)
os.makedirs(modeller_dir, exist_ok=True)

# Clear old outputs for Step 4
print("Clearing old outputs for Step 4...")
for file in os.listdir(output_dir):
    try:
        os.remove(os.path.join(output_dir, file))
    except Exception:
        pass
for file in os.listdir(gorseller_dir):
    try:
        os.remove(os.path.join(gorseller_dir, file))
    except Exception:
        pass

input_path = os.path.join(islenmis_dir, "2_BIST_USD_VIF.xlsx")
print(f"Loading {input_path}...")
xl = pd.ExcelFile(input_path)
sheet_names = xl.sheet_names

# Custom Panel Time Series Split CV by Period
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

# SMOTE class balance logic
def apply_smote_if_needed(X, y):
    class_counts = y.value_counts()
    if len(class_counts) < 2:
        return X, y
    min_class = class_counts.min()
    total = len(y)
    minority_ratio = min_class / total
    
    # Check if imbalanced (< 35% representation)
    if minority_ratio < 0.35:
        if has_smote:
            # SMOTE requires at least k_neighbors+1 samples of minority class
            k = min(5, min_class - 1)
            if k >= 1:
                try:
                    smote = SMOTE(k_neighbors=k, random_state=42)
                    X_res, y_res = smote.fit_resample(X, y)
                    return X_res, y_res
                except Exception as e:
                    print(f"SMOTE failed: {e}. Falling back to Random Over Sampling.")
                    
        # Fallback manual Random Over Sampler
        majority_class = class_counts.idxmax()
        minority_class = class_counts.idxmin()
        
        df_temp = pd.concat([X, y], axis=1)
        df_maj = df_temp[df_temp[y.name] == majority_class]
        df_min = df_temp[df_temp[y.name] == minority_class]
        
        df_min_over = df_min.sample(len(df_maj), replace=True, random_state=42)
        df_over = pd.concat([df_maj, df_min_over], axis=0).sample(frac=1.0, random_state=42)
        return df_over.drop(columns=[y.name]), df_over[y.name]
        
    return X, y

# ROC decision threshold tuning using Youden's J Index
def get_best_threshold(y_true, y_prob):
    fpr, tpr, thresholds = roc_curve(y_true, y_prob)
    j_scores = tpr - fpr
    best_idx = np.argmax(j_scores)
    best_threshold = thresholds[best_idx]
    # Cap threshold between 0.15 and 0.85
    return float(np.clip(best_threshold, 0.15, 0.85))

# Store results for summary sheet
summary_rows = []
writer_perf = pd.ExcelWriter(os.path.join(output_dir, "Model_Performansi_Siniflandirma_USD.xlsx"), engine="xlsxwriter")

for sheet in sheet_names:
    print(f"\n==================================================")
    print(f"Running Classification for Sector: {sheet}")
    print(f"==================================================")
    
    df = pd.read_excel(input_path, sheet_name=sheet)
    df = df.reset_index(drop=True)
    
    target_col = [col for col in df.columns if "t+1" in col][0]
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", target_col]
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    # Calculate Targets
    # Target A: Profit or Loss
    y_target_A = (df[target_col] > 0).astype(int)
    # Target B: Profit direction
    y_target_B = (df[target_col] > df["Net Dönem Karı/Zararı"]).astype(int)
    targets = {
        "Kar_Zarar_Tahmini": (y_target_A, "Net Dönem Kârı (t+1) > 0"),
        "Yon_Tahmini": (y_target_B, "Net Dönem Kârı (t+1) > Cari Net Kâr")
    }
    
    # Split indexes
    train_mask = df["Dönem"] <= 31
    test_mask = df["Dönem"] >= 32
    
    df_train = df[train_mask].copy().reset_index(drop=True)
    df_test = df[test_mask].copy().reset_index(drop=True)
    
    # Create sector output sheet base
    sector_predictions_df = df_test[["Firma Adı", "Dönem"]].copy()
    
    # Loop over targets
    for target_name, (y_full, target_desc) in targets.items():
        print(f"\nTraining for {target_name}: {target_desc}...")
        
        y_train = y_full[train_mask].copy().reset_index(drop=True)
        y_test = y_full[test_mask].copy().reset_index(drop=True)
        
        X_train = df_train[feature_cols].copy()
        X_test = df_test[feature_cols].copy()
        
        # Check cache
        cache_file = os.path.join(modeller_dir, f"champion_{sheet}_{target_name}_USD.pkb")
        cache_loaded = False
        
        if os.path.exists(cache_file):
            try:
                print(f"Found cached classifier for {sheet} - {target_name}. Loading...")
                with open(cache_file, "rb") as f:
                    cache_data = pickle.load(f)
                best_model = cache_data["model"]
                scaler = cache_data["scaler"]
                best_threshold = cache_data["threshold"]
                cache_loaded = True
            except Exception as e:
                print(f"Failed to load cache: {e}. Re-training...")
                
        if not cache_loaded:
            # Scale features
            scaler = RobustScaler()
            if len(numeric_features) > 0:
                X_train[numeric_features] = scaler.fit_transform(X_train[numeric_features])
                X_test[numeric_features] = scaler.transform(X_test[numeric_features])
                
            # Class balancing (SMOTE) on Train split only
            X_train_res, y_train_res = apply_smote_if_needed(X_train, y_train)
                
            splits = custom_panel_tscv(df_train, n_splits=5)
            
            # Tune and evaluate models
            # We tune 4 tree models using Optuna (10 trials)
            def tune_tree_clf(model_class, param_space_func, X, y, splits):
                def objective(trial):
                    params = param_space_func(trial)
                    scores = []
                    for train_idx, val_idx in splits:
                        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
                        X_va, y_va = X.iloc[val_idx], y.iloc[val_idx]
                        
                        # Apply SMOTE to training folds
                        X_tr_res, y_tr_res = apply_smote_if_needed(X_tr, y_tr)
                            
                        # If minority class has 0 samples after split, skip
                        if len(np.unique(y_tr_res)) < 2 or len(np.unique(y_va)) < 2:
                            continue
                            
                        mdl = model_class(**params)
                        mdl.fit(X_tr_res, y_tr_res)
                        probs = mdl.predict_proba(X_va)[:, 1]
                        auc = roc_auc_score(y_va, probs)
                        scores.append(auc)
                    return np.mean(scores) if len(scores) > 0 else 0.0
                    
                study = optuna.create_study(direction="maximize")
                study.optimize(objective, n_trials=3)
                return model_class(**study.best_params).fit(X, y)
                
            # 1. Logistic Regression
            clf_lr = LogisticRegression(max_iter=10000, random_state=42).fit(X_train_res, y_train_res)
            
            # 2. Random Forest
            print("Tuning RF Classifier...")
            clf_rf = tune_tree_clf(
                RandomForestClassifier,
                lambda t: {
                    "n_estimators": t.suggest_int("n_estimators", 50, 150),
                    "max_depth": t.suggest_int("max_depth", 3, 8),
                    "random_state": 42
                },
                X_train, y_train, splits
            )
            
            # 3. XGBoost
            print("Tuning XGBoost Classifier...")
            clf_xgb = tune_tree_clf(
                xgb.XGBClassifier,
                lambda t: {
                    "n_estimators": t.suggest_int("n_estimators", 50, 150),
                    "learning_rate": t.suggest_float("learning_rate", 0.01, 0.1),
                    "max_depth": t.suggest_int("max_depth", 2, 6),
                    "random_state": 42
                },
                X_train, y_train, splits
            )
            
            # 4. LightGBM
            print("Tuning LightGBM Classifier...")
            clf_lgb = tune_tree_clf(
                lgb.LGBMClassifier,
                lambda t: {
                    "n_estimators": t.suggest_int("n_estimators", 50, 150),
                    "learning_rate": t.suggest_float("learning_rate", 0.01, 0.1),
                    "max_depth": t.suggest_int("max_depth", 2, 6),
                    "verbosity": -1,
                    "random_state": 42
                },
                X_train, y_train, splits
            )
            
            # 5. CatBoost
            print("Tuning CatBoost Classifier...")
            clf_cb = tune_tree_clf(
                cb.CatBoostClassifier,
                lambda t: {
                    "iterations": t.suggest_int("iterations", 50, 150),
                    "learning_rate": t.suggest_float("learning_rate", 0.01, 0.1),
                    "depth": t.suggest_int("depth", 2, 6),
                    "verbose": 0,
                    "random_seed": 42
                },
                X_train, y_train, splits
            )
            
            # Select champion among the 5 models based on validation ROC-AUC or Train predictions
            candidates = {
                "LogisticRegression": clf_lr,
                "RandomForest": clf_rf,
                "XGBoost": clf_xgb,
                "LightGBM": clf_lgb,
                "CatBoost": clf_cb
            }
            
            best_val_auc = -1.0
            best_model_name = ""
            best_model = None
            
            for name, mdl in candidates.items():
                # Estimate AUC on out-of-fold validation splits
                scores = []
                for train_idx, val_idx in splits:
                    X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
                    X_va, y_va = X_train.iloc[val_idx], y_train.iloc[val_idx]
                    
                    if len(np.unique(y_tr)) < 2 or len(np.unique(y_va)) < 2:
                        continue
                    # Retrain on fold
                    X_tr_res, y_tr_res = apply_smote_if_needed(X_tr, y_tr)
                    m_temp = pickle.loads(pickle.dumps(mdl)) # duplicate object
                    m_temp.fit(X_tr_res, y_tr_res)
                    probs = m_temp.predict_proba(X_va)[:, 1]
                    scores.append(roc_auc_score(y_va, probs))
                avg_auc = np.mean(scores) if len(scores) > 0 else 0.0
                
                if avg_auc > best_val_auc:
                    best_val_auc = avg_auc
                    best_model_name = name
                    best_model = mdl
                    
            print(f"Selected Champion for {target_name}: {best_model_name} (Val AUC: {best_val_auc:.4f})")
            
            # ROC Threshold tuning on Train set prediction
            train_probs = best_model.predict_proba(X_train)[:, 1]
            best_threshold = get_best_threshold(y_train, train_probs)
            
            # Calibrate model if desired
            # We calibrate the probability using isotonic method prefitted
            # (Note: CalibratedClassifierCV on prefit models is simple)
            try:
                calibrated_model = CalibratedClassifierCV(estimator=best_model, method="isotonic", cv="prefit")
                calibrated_model.fit(X_train, y_train)
                best_model = calibrated_model
            except Exception as e:
                print(f"Warning: Calibration failed, using raw probabilities: {e}")
                
            # Save to cache
            cache_data = {
                "model": best_model,
                "scaler": scaler,
                "threshold": best_threshold,
                "model_name": best_model_name
            }
            with open(cache_file, "wb") as f:
                pickle.dump(cache_data, f)
                
        # Scale test features for loaded cache models
        if cache_loaded and len(numeric_features) > 0:
            X_test[numeric_features] = scaler.transform(X_test[numeric_features])
            X_train[numeric_features] = scaler.transform(X_train[numeric_features])
            
        # Predict on Test split
        test_probs = best_model.predict_proba(X_test)[:, 1]
        test_preds = (test_probs >= best_threshold).astype(int)
        
        # Predict on Train split for metrics
        train_probs = best_model.predict_proba(X_train)[:, 1]
        train_preds = (train_probs >= best_threshold).astype(int)
        
        # Calculate test metrics
        test_acc = accuracy_score(y_test, test_preds)
        test_prec = precision_score(y_test, test_preds, zero_division=0)
        test_rec = recall_score(y_test, test_preds, zero_division=0)
        test_f1 = f1_score(y_test, test_preds, zero_division=0)
        try:
            test_auc = roc_auc_score(y_test, test_probs)
        except Exception:
            test_auc = 0.5
            
        # Calculate train metrics
        train_acc = accuracy_score(y_train, train_preds)
        train_prec = precision_score(y_train, train_preds, zero_division=0)
        train_rec = recall_score(y_train, train_preds, zero_division=0)
        train_f1 = f1_score(y_train, train_preds, zero_division=0)
        try:
            train_auc = roc_auc_score(y_train, train_probs)
        except Exception:
            train_auc = 0.5
            
        model_type_name = getattr(best_model, "estimator", best_model).__class__.__name__
        
        summary_rows.append({
            "Sektör": sheet,
            "Hedef Değişken": target_name,
            "Tanım": target_desc,
            "Veri Adeti (Test)": len(y_test),
            "Train Accuracy (%)": round(train_acc * 100, 2),
            "Train Precision (%)": round(train_prec * 100, 2),
            "Train Recall (%)": round(train_rec * 100, 2),
            "Train F1-Score (%)": round(train_f1 * 100, 2),
            "Train ROC-AUC (%)": round(train_auc * 100, 2),
            "Test Accuracy (%)": round(test_acc * 100, 2),
            "Test Precision (%)": round(test_prec * 100, 2),
            "Test Recall (%)": round(test_rec * 100, 2),
            "Test F1-Score (%)": round(test_f1 * 100, 2),
            "Test ROC-AUC (%)": round(test_auc * 100, 2),
            "Optimal Eşik (Threshold)": round(best_threshold, 4),
            "En İyi Model": model_type_name
        })
        
        # Add predictions to sector sheet
        sector_predictions_df[f"{target_name} Gerçek"] = y_test.values
        sector_predictions_df[f"{target_name} Tahmin"] = test_preds
        sector_predictions_df[f"{target_name} Olasılık"] = np.round(test_probs, 4)
        
    # Write sector predictions to Excel
    sector_predictions_df.to_excel(writer_perf, sheet_name=sheet, index=False)
    
# Save consolidated summary
summary_df = pd.DataFrame(summary_rows)
summary_df.to_excel(writer_perf, sheet_name="Genel_Ozet", index=False)
writer_perf.close()
print("Classification performance Excel sheet saved.")

# Generate performance comparison plots
for target in ["Kar_Zarar_Tahmini", "Yon_Tahmini"]:
    tgt_df = summary_df[summary_df["Hedef Değişken"] == target]
    
    plt.figure(figsize=(12, 6))
    x = np.arange(len(tgt_df["Sektör"]))
    width = 0.35
    
    # Plot Accuracy vs F1-Score
    fig, ax = plt.subplots(figsize=(12, 6))
    rects1 = ax.bar(x - width/2, tgt_df["Test Accuracy (%)"], width, label='Test Accuracy (%)', color='#2980b9')
    rects2 = ax.bar(x + width/2, tgt_df["Test F1-Score (%)"], width, label='Test F1-Score (%)', color='#e74c3c')
    
    # Add data labels
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='bold')
                        
    autolabel(rects1)
    autolabel(rects2)
    
    plt.xlabel('Sektör')
    plt.ylabel('Yüzde (%)')
    plt.title(f'Sınıflandırma Başarısı - {target} Karşılaştırması (Accuracy vs F1-Score)')
    plt.xticks(x, tgt_df["Sektör"], rotation=45, ha="right")
    plt.ylim(0, 110)
    plt.legend()
    plt.tight_layout()
    
    gorsel_path = os.path.join(gorseller_dir, f"Performans_Karsilastirma_{target}.png")
    plt.savefig(gorsel_path, dpi=300)
    plt.close()
    print(f"Plot saved to {gorsel_path}")
    
print("Step 4 Classification completed successfully!")
