import sys
import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shap

# Add root folder to sys.path to import kullanici.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# Define paths dynamically using kb.klasor
ml_dir = os.path.join(kb.klasor, "5_Makine Öğrenmesi_v1")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "5_XAI")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "5_XAI")
modeller_reg_dir = os.path.join(ml_dir, "4_modeller", "3_Regresyon_Analizi")

# Ensure target directories exist
os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# Clear old outputs for Step 5
print("Clearing old outputs for Step 5...")
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

writer_shap = pd.ExcelWriter(os.path.join(output_dir, "SHAP_Feature_Importance_USD.xlsx"), engine="xlsxwriter")

for sheet in sheet_names:
    print(f"\n==================================================")
    print(f"Running SHAP Analysis for Sector: {sheet}")
    print(f"==================================================")
    
    df = pd.read_excel(input_path, sheet_name=sheet)
    df = df.reset_index(drop=True)
    
    target_col = [col for col in df.columns if "t+1" in col][0]
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", target_col]
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    # Load champion regression model and its scaler
    cache_file = os.path.join(modeller_reg_dir, f"champion_{sheet}_USD.pkb")
    if not os.path.exists(cache_file):
        print(f"Warning: No champion model found for {sheet}. Skipping...")
        continue
        
    with open(cache_file, "rb") as f:
        cache_data = pickle.load(f)
        
    # In Step 3, we stored the model dictionary under 'models' and the champion's name in the excel report.
    # Let's inspect the keys to find the champion model.
    # Wait, the regression script saved:
    # cache_data = {"models": models, "scaler": scaler}
    # Let's find the best model name by evaluating which model is in models.
    # Wait, in the regression script:
    # best_model_name was written to the test summary, and we saved all models in the dict.
    # Let's find the champion model from the output summary sheet or let's select the best one by scoring them here!
    # Wait! Scoring them here on Test set is extremely easy and guarantees we get the exact same champion!
    
    # Split train/test
    train_mask = df["Dönem"] <= 31
    test_mask = df["Dönem"] >= 32
    
    df_train = df[train_mask].copy().reset_index(drop=True)
    df_test = df[test_mask].copy().reset_index(drop=True)
    
    X_train = df_train[feature_cols].copy()
    y_train = df_train[target_col].copy()
    X_test = df_test[feature_cols].copy()
    y_test = df_test[target_col].copy()
    
    scaler = cache_data["scaler"]
    models = cache_data["models"]
    
    # Scale features
    if len(numeric_features) > 0 and scaler is not None:
        X_train[numeric_features] = scaler.transform(X_train[numeric_features])
        X_test[numeric_features] = scaler.transform(X_test[numeric_features])
        
    # Retrieve champion model from cache
    best_model_name = cache_data.get("best_model_name", "")
    if not best_model_name or best_model_name not in models:
        # Fallback to evaluating models on test split to find the best model name if not cached
        best_test_mape = 999.0
        best_model_name = ""
        best_model = None
        for name, model in models.items():
            preds = model.predict(X_test)
            non_zero_mask = y_test != 0
            mape_val = np.mean(np.abs((y_test[non_zero_mask] - preds[non_zero_mask]) / y_test[non_zero_mask]))
            if mape_val < best_test_mape:
                best_test_mape = mape_val
                best_model_name = name
                best_model = model
    else:
        best_model = models[best_model_name]
        
    print(f"Sector {sheet} Champion Model: {best_model_name}")
    
    # Calculate SHAP values
    # Try using TreeExplainer for tree models
    is_tree = best_model_name in ["RF", "Extra_Trees", "GBR", "XGBoost", "LightGBM", "CatBoost"]
    
    # We will use X_test_plot and shap_values for plots
    X_test_plot = X_test.copy()
    
    try:
        if is_tree:
            # TreeExplainer is extremely fast
            explainer = shap.TreeExplainer(best_model)
            shap_values = explainer.shap_values(X_test)
        else:
            # KernelExplainer for Ridge, Lasso, ElasticNet, SVR, KNN
            # Use small background sample AND small test sample to keep it fast
            background = shap.sample(X_train, 5)
            X_test_plot = shap.sample(X_test, min(20, len(X_test)), random_state=42)
            explainer = shap.KernelExplainer(best_model.predict, background)
            shap_values = explainer.shap_values(X_test_plot)
    except Exception as e:
        print(f"Standard explainer failed for {best_model_name}: {e}. Falling back to general Explainer.")
        try:
            background = shap.sample(X_train, 5)
            X_test_plot = shap.sample(X_test, min(20, len(X_test)), random_state=42)
            explainer = shap.Explainer(best_model.predict, background)
            shap_values = explainer(X_test_plot).values
        except Exception as ex:
            print(f"Fallback explainer failed: {ex}. Skipping SHAP for this sector.")
            continue
            
    # Normalize shape of SHAP values if needed
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    elif len(shap_values.shape) == 3:
        shap_values = shap_values[:, :, 0]
        
    # Calculate mean absolute SHAP value for feature importance
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    
    # Compute correlation between SHAP values and feature values to determine direction
    directions = []
    for i, col in enumerate(feature_cols):
        feat_vals = X_test_plot[col].values
        s_vals = shap_values[:, i]
        # Correlation
        if np.std(feat_vals) > 0 and np.std(s_vals) > 0:
            corr = np.corrcoef(feat_vals, s_vals)[0, 1]
            directions.append("Pozitif (+)" if corr > 0 else "Negatif (-)")
        else:
            directions.append("Nötr (0)")
            
    # Create Feature Importance DataFrame
    importance_df = pd.DataFrame({
        "Öznitelik adı": feature_cols,
        "Ortalama Mutlak SHAP Değeri": mean_abs_shap,
        "Katkı Yönü (Pozitif/Negatif)": directions
    })
    
    # Sort descending
    importance_df = importance_df.sort_values(by="Ortalama Mutlak SHAP Değeri", ascending=False).reset_index(drop=True)
    # Add shortened name for plotting
    importance_df["Öznitelik adı (Kısa)"] = importance_df["Öznitelik adı"].apply(lambda x: x[:30] + "..." if len(x) > 30 else x)
    importance_df.to_excel(writer_shap, sheet_name=sheet, index=False)
    
    import matplotlib.ticker as ticker
    

    
    # Plot 2: Top 10 Feature Importance Bar Plot with exact numerical values labels
    top_10 = importance_df.head(10).copy()
    plt.figure(figsize=(12, 7))
    ax = sns.barplot(
        data=top_10, 
        x="Ortalama Mutlak SHAP Değeri", 
        y="Öznitelik adı (Kısa)", 
        palette="viridis"
    )
    # Add exact numerical value labels on top of the bars (x-axis ends)
    for p in ax.patches:
        width = p.get_width()
        ax.annotate(f"{int(width):,}", 
                    (width, p.get_y() + p.get_height() / 2.), 
                    ha='left', va='center', 
                    xytext=(5, 0), 
                    textcoords='offset points',
                    fontsize=9, fontweight='bold')
                    
    plt.title(f"{sheet} - En Önemli 10 Öznitelik (SHAP)", fontsize=12, fontweight='bold', pad=15)
    plt.xlabel("Ortalama Mutlak SHAP Etkisi")
    plt.ylabel("Öznitelik Adı")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    plt.xticks(rotation=15)
    
    plt.xlim(0, top_10["Ortalama Mutlak SHAP Değeri"].max() * 1.25)
    plt.gcf().subplots_adjust(left=0.40, right=0.9, top=0.9, bottom=0.18)
    bar_plot_path = os.path.join(gorseller_dir, f"SHAP_Feature_Importance_Bar_{sheet}.png")
    plt.savefig(bar_plot_path, dpi=300)
    plt.close()
    print(f"Saved SHAP summary and importance plots for {sheet}.")

writer_shap.close()
print("Step 5 XAI completed successfully!")
