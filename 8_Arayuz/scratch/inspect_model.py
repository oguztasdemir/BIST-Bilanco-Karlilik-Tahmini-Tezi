import os
import pickle

models_dir = r"c:\Users\User\Desktop\Tez Feature Selection\8_Arayuz\models\4_Siniflandirma_Analizi"
files = os.listdir(models_dir)

for file in sorted(files):
    if not file.endswith(".pkb"):
        continue
    path = os.path.join(models_dir, file)
    with open(path, "rb") as f:
        data = pickle.load(f)
    
    print(f"File: {file}")
    print(f"  Keys: {list(data.keys())}")
    if "features" in data:
        print(f"  features (V1): {len(data['features'])}")
    else:
        print(f"  NO 'features' key")
    if "models" in data:
        print(f"  models (V2): {list(data['models'].keys())}")
        # Try to find expected features for V2
        best_name = data.get("best_model_name")
        best_m = data["models"].get(best_name)
        if hasattr(best_m, "feature_names_in_"):
            print(f"    best model features count: {len(best_m.feature_names_in_)}")
        elif hasattr(best_m, "feature_names_"):
            print(f"    best model features count: {len(best_m.feature_names_)}")
        else:
            print(f"    best model has no feature names")
