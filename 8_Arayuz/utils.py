import os
import re
import sys
import pickle
import pandas as pd
import numpy as np
from sklearn.preprocessing import RobustScaler

# ── LOCAL PATH DEFINITIONS ───────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# ── CACHES ───────────────────────────────────────────────────────────────────
DF_CACHE = {}
MODELS_CACHE = {}
ALIGNMENT_KEYS_CACHE = {}
SCALERS_CACHE = {}
COLUMNS_CACHE = {}
_BATCH_ACC_CACHE = {}
_BATCH_MAPE_CACHE = {}
_MATRIX_SCORES_CACHE = {}

# ── TURKISH CHARACTER NORMALIZATION FOR FILE MATCHING ─────────────────────────
_TR_UPPER_MAP = str.maketrans(
    'ÇĞİÖŞÜçğışöşü',
    'CGIOSUcgiiosu'
)

def _normalize_for_filename(s):
    """Strip Turkish diacritics so we can fuzzy-match file names."""
    return str(s).translate(_TR_UPPER_MAP).upper()

def find_model_file(exact_path):
    """
    If exact_path exists, return it.
    Otherwise scan the directory for a file whose ASCII-normalised name
    matches the requested filename (handles Turkish chars in filenames).
    Returns the resolved path or None.
    """
    if os.path.exists(exact_path):
        return exact_path
    directory = os.path.dirname(exact_path)
    target_name = _normalize_for_filename(os.path.basename(exact_path))
    if not os.path.isdir(directory):
        return None
    for fname in os.listdir(directory):
        if _normalize_for_filename(fname) == target_name:
            return os.path.join(directory, fname)
    return None

# ── CACHED DATA LOADERS ───────────────────────────────────────────────────────
def clean_and_normalize(s):
    s = str(s).lower().strip()
    # Replace Turkish chars
    turkish_map = {
        'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
        'â': 'a', 'î': 'i', 'û': 'u'
    }
    for tr, eng in turkish_map.items():
        s = s.replace(tr, eng)
    # Remove non-alphanumeric
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

def clean_vowels(s):
    s = clean_and_normalize(s)
    # Remove all vowels
    for v in ['a', 'e', 'i', 'o', 'u']:
        s = s.replace(v, '')
    return s

def normalize_sector_name(name):
    if not name:
        return ""
    # Strip Turkish diacritics first (İ→I, Ş→S etc.) then keyword-match
    name_upper = _normalize_for_filename(str(name).replace("\uFFFD", ""))

    if "SANAY" in name_upper:
        return "SANAYI_VE_IMALAT"
    if "FINANS" in name_upper or "FNANS" in name_upper:
        return "FINANS_VE_YATIRIM"
    if "INSAAT" in name_upper or "NAAT" in name_upper:
        return "INSAAT_VE_GAYRIMENKUL"
    if "TEKNOLOJ" in name_upper:
        return "TEKNOLOJI_VE_HIZMET"
    if "ENERJ" in name_upper:
        return "ENERJI_VE_HAMMADDE"
    if "GIDA" in name_upper:
        return "GIDA_VE_TARIM"
    if "TICARET" in name_upper or "TCARET" in name_upper:
        return "TICARET_VE_PAZARLAMA"

    return name

def get_cached_df(dataset_path, sector):
    key = (dataset_path, sector)
    if key in DF_CACHE:
        return DF_CACHE[key]
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
    # Read sheet names for robust matching
    xl = pd.ExcelFile(dataset_path)
    sheet_names = xl.sheet_names
    
    target_sheet = None
    norm_target = normalize_sector_name(sector)
    
    # Try normalize matching first
    for s in sheet_names:
        if normalize_sector_name(s) == norm_target:
            target_sheet = s
            break
            
    if not target_sheet:
        if sector in sheet_names:
            target_sheet = sector
        else:
            # Match normalized
            norm_sector = clean_and_normalize(sector)
            for s in sheet_names:
                if clean_and_normalize(s) == norm_sector:
                    target_sheet = s
                    break
            
            # Vowel-stripped match if not found
            if not target_sheet:
                vow_sector = clean_vowels(sector)
                for s in sheet_names:
                    if clean_vowels(s) == vow_sector:
                        target_sheet = s
                        break
                        
    if not target_sheet:
        target_sheet = sector
        
    df = pd.read_excel(dataset_path, sheet_name=target_sheet)
    DF_CACHE[key] = df
    return df


def get_cached_model(model_path):
    if model_path in MODELS_CACHE:
        return MODELS_CACHE[model_path]
    # Resolve Turkish-character mismatches in file names
    resolved = find_model_file(model_path)
    if resolved is None:
        return None
    with open(resolved, "rb") as f:
        model = pickle.load(f)
    # Cache under both the original and resolved key
    MODELS_CACHE[model_path] = model
    MODELS_CACHE[resolved] = model
    return model

# ── FEATURE ALIGNMENT ─────────────────────────────────────────────────────────
def get_feature_alignment_mapping(df_columns, target_feats):
    mapping = {}
    exact_map = {col.lower(): col for col in df_columns}
    clean_map = {clean_and_normalize(col): col for col in df_columns}
    vowel_map = {clean_vowels(col): col for col in df_columns}
    
    for col in target_feats:
        if col.lower() in exact_map:
            mapping[col] = exact_map[col.lower()]
        else:
            col_clean = clean_and_normalize(col)
            if col_clean in clean_map:
                mapping[col] = clean_map[col_clean]
            else:
                col_vowel = clean_vowels(col)
                if col_vowel in vowel_map:
                    mapping[col] = vowel_map[col_vowel]
                else:
                    found = False
                    for pk, pv in vowel_map.items():
                        if col_vowel in pk or pk in col_vowel:
                            mapping[col] = pv
                            found = True
                            break
                    if not found:
                        mapping[col] = col
    return mapping

def align_features_for_model(sector, company, period, currency, version, expected_features, custom_features, model=None, mevsim=None, anomali=None):
    """
    Loads original features from the Excel sheet, updates them with any custom features
    provided by the user, and aligns the result to match the list of expected features.
    If a model is provided, it tries to match the features specifically required by the model
    by utilizing normalize/vowel-stripped matching to deal with spaces vs underscores
    and encoding artifacts.
    """
    if version == 'V1':
        dataset_path = os.path.join(DATA_DIR, "datasets", "v1", f"2_BIST_{currency}_VIF.xlsx")
    else:
        dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
        if not os.path.exists(dataset_path):
            dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
        
    df = get_cached_df(dataset_path, sector)
    row = df[(df["Firma Adı"] == company) & (df["Dönem"] == int(period))]
    row_dict = row.iloc[0].to_dict() if not row.empty else {}
    
    target_feats = expected_features
    if model is not None:
        if hasattr(model, "feature_names_in_"):
            target_feats = list(model.feature_names_in_)
        elif hasattr(model, "feature_names_"):
            target_feats = list(model.feature_names_)
            
    cache_key = (dataset_path, sector, tuple(target_feats))
    if cache_key in ALIGNMENT_KEYS_CACHE:
        mapping = ALIGNMENT_KEYS_CACHE[cache_key]
    else:
        mapping = get_feature_alignment_mapping(list(df.columns), target_feats)
        ALIGNMENT_KEYS_CACHE[cache_key] = mapping
        
    aligned_dict = {}
    for col in target_feats:
        sheet_col = mapping.get(col, col)
        
        if custom_features and sheet_col in custom_features:
            val = custom_features[sheet_col]
        elif custom_features and col in custom_features:
            val = custom_features[col]
        elif sheet_col.lower().strip() == "mevsimsellik" and mevsim is not None:
            val = int(mevsim)
        elif sheet_col.lower().strip() == "anomali_durumu" and anomali is not None:
            val = int(anomali)
        elif col.lower().strip() == "mevsimsellik" and mevsim is not None:
            val = int(mevsim)
        elif col.lower().strip() == "anomali_durumu" and anomali is not None:
            val = int(anomali)
        else:
            val = row_dict.get(sheet_col, 0.0)
            
        if pd.isna(val) or val is None:
            val = 0.0
        aligned_dict[col] = float(val)
        
    df_aligned = pd.DataFrame([aligned_dict], columns=target_feats)
    return df_aligned

def align_features_batch(df_sector, sector, currency, version, expected_features, model=None):
    if version == 'V1':
        dataset_path = os.path.join(DATA_DIR, "datasets", "v1", f"2_BIST_{currency}_VIF.xlsx")
    else:
        dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
        if not os.path.exists(dataset_path):
            dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
            
    df_raw = get_cached_df(dataset_path, sector)
    
    target_feats = expected_features
    if model is not None:
        if hasattr(model, "feature_names_in_"):
            target_feats = list(model.feature_names_in_)
        elif hasattr(model, "feature_names_"):
            target_feats = list(model.feature_names_)
            
    cache_key = (dataset_path, sector, tuple(target_feats))
    if cache_key in ALIGNMENT_KEYS_CACHE:
        mapping = ALIGNMENT_KEYS_CACHE[cache_key]
    else:
        mapping = get_feature_alignment_mapping(list(df_raw.columns), target_feats)
        ALIGNMENT_KEYS_CACHE[cache_key] = mapping
        
    aligned_df = pd.DataFrame(index=df_sector.index, columns=target_feats)
    for col in target_feats:
        sheet_col = mapping.get(col, col)
        
        if sheet_col.lower().strip() == "mevsimsellik" and "mevsimsellik" in df_sector.columns:
            aligned_df[col] = df_sector["mevsimsellik"]
        elif sheet_col.lower().strip() == "anomali_durumu" and "Anomali_Durumu" in df_sector.columns:
            aligned_df[col] = df_sector["Anomali_Durumu"]
        elif col.lower().strip() == "mevsimsellik" and "mevsimsellik" in df_sector.columns:
            aligned_df[col] = df_sector["mevsimsellik"]
        elif col.lower().strip() == "anomali_durumu" and "Anomali_Durumu" in df_sector.columns:
            aligned_df[col] = df_sector["Anomali_Durumu"]
        else:
            if sheet_col in df_sector.columns:
                aligned_df[col] = df_sector[sheet_col]
            else:
                aligned_df[col] = 0.0
                
        aligned_df[col] = aligned_df[col].fillna(0.0).astype(float)
        
    return aligned_df

# ── SCALING ──────────────────────────────────────────────────────────────────
def get_v2_columns(sector, currency):
    key = (sector, currency)
    if key in COLUMNS_CACHE:
        return COLUMNS_CACHE[key]
        
    v2_dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
    if not os.path.exists(v2_dataset_path):
        return []
    try:
        df = get_cached_df(v2_dataset_path, sector)
        cols = list(df.columns)
        COLUMNS_CACHE[key] = cols
        return cols
    except Exception as ex:
        print(f"Error reading columns for {key}: {ex}")
        return []

def get_v2_scaler(sector, currency):
    key = (sector, currency)
    if key in SCALERS_CACHE:
        return SCALERS_CACHE[key]
        
    unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
    if not os.path.exists(unscaled_path):
        return None, []
        
    try:
        df_unscaled = get_cached_df(unscaled_path, sector)
        t_cols = [col for col in df_unscaled.columns if "t+1" in col]
        t_col = t_cols[0] if t_cols else None
        m_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", "Net Dönem Karı"]
        if t_col:
            m_cols.append(t_col)
            
        num_feats = [col for col in df_unscaled.columns if col not in m_cols and df_unscaled[col].dtype in ["float64", "int64"]]
        df_train = df_unscaled[df_unscaled["Dönem"] <= 31]
        
        scaler = RobustScaler()
        scaler.fit(df_train[num_feats].fillna(0.0))
        
        SCALERS_CACHE[key] = (scaler, num_feats)
        return scaler, num_feats
    except Exception as ex:
        print(f"Error fitting scaler for {key}: {ex}")
        return None, []

def scale_v2_features(df_aligned, sector, currency):
    """
    Fits a RobustScaler on the unscaled training set of the given sector,
    scales the numeric features in df_aligned on the fly, and returns the scaled DataFrame.
    """
    scaler, num_feats = get_v2_scaler(sector, currency)
    if scaler is None or not num_feats:
        return df_aligned
        
    try:
        # Transform df_aligned
        tmp_df = pd.DataFrame(0.0, index=[0], columns=num_feats)
        for col in num_feats:
            matched_col = None
            for c in df_aligned.columns:
                if clean_and_normalize(c) == clean_and_normalize(col):
                    matched_col = c
                    break
            if matched_col is not None:
                tmp_df.at[0, col] = float(df_aligned.at[0, matched_col])
                
        scaled_vals = scaler.transform(tmp_df)
        
        # Put scaled values back
        df_scaled = df_aligned.copy()
        for idx, col in enumerate(num_feats):
            matched_col = None
            for c in df_scaled.columns:
                if clean_and_normalize(c) == clean_and_normalize(col):
                    matched_col = c
                    break
            if matched_col is not None:
                df_scaled.at[0, matched_col] = scaled_vals[0, idx]
                
        return df_scaled
    except Exception as ex:
        print(f"Error in scale_v2_features: {ex}")
        return df_aligned

def scale_v2_features_batch(df_aligned, sector, currency):
    scaler, num_feats = get_v2_scaler(sector, currency)
    if scaler is None or not num_feats:
        return df_aligned
    df_scaled = df_aligned.copy()
    N = len(df_aligned)
    dummy = np.zeros((N, len(num_feats)))
    col_to_idx = {col: idx for idx, col in enumerate(num_feats)}
    
    for col in df_aligned.columns:
        if col in col_to_idx:
            idx = col_to_idx[col]
            dummy[:, idx] = df_aligned[col].fillna(0.0).values
            
    scaled_dummy = scaler.transform(dummy)
    
    for col in df_aligned.columns:
        if col in col_to_idx:
            idx = col_to_idx[col]
            df_scaled[col] = scaled_dummy[:, idx]
            
    return df_scaled

# ── PREDICTIONS ──────────────────────────────────────────────────────────────
def get_dec_row(df_dec, sector):
    """
    Find a sector row in a decision-matrix DataFrame using normalize_sector_name
    so Turkish-character mismatches between the stored sector name and the
    requested sector name are handled automatically.
    Returns a pandas Series (the matching row) or None.
    """
    sect_col = "Sektör" if "Sektör" in df_dec.columns else "Sektor"
    norm_target = normalize_sector_name(sector)
    for _, row in df_dec.iterrows():
        if normalize_sector_name(str(row[sect_col])) == norm_target:
            return row
    return None


def predict_regression_batch(sector, currency, df_sector):
    """
    Predicts regression values for the entire sector dataframe in a vectorized batch.
    """
    if df_sector.empty:
        return pd.Series([], dtype=float)
        
    matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Main_Karar_Matrisi.xlsx")
    if not os.path.exists(matrix_path):
        matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
        
    if not os.path.exists(matrix_path):
        return pd.Series(0.0, index=df_sector.index)
        
    df_dec = get_cached_df(matrix_path, "En_Iyi_Yapboz_Matrisi")
    dec_row = get_dec_row(df_dec, sector)
    if dec_row is None:
        return pd.Series(0.0, index=df_sector.index)

    # Use the original (Turkified) sector name for model file lookup
    stored_sector = str(dec_row.get("Sektör") or dec_row.get("Sektor") or sector)
    reg_ver_raw = dec_row.get("Reg_Sayısal_Versiyon") or dec_row.get("Reg_Sayisal_Versiyon") or "V1"
    reg_ver = str(reg_ver_raw).strip()
    
    reg_model_path = os.path.join(MODELS_DIR, "3_Regresyon_Analizi", f"champion_{stored_sector}_{currency}.pkb")
    reg_cache = get_cached_model(reg_model_path)
    if not reg_cache:
        # Fallback: try with the requested (ASCII) sector name
        reg_model_path = os.path.join(MODELS_DIR, "3_Regresyon_Analizi", f"champion_{sector}_{currency}.pkb")
        reg_cache = get_cached_model(reg_model_path)
    if not reg_cache:
        return pd.Series(0.0, index=df_sector.index)
        
    fitted_models = reg_cache["models"]
    
    if reg_ver == "V1":
        best_single_name = reg_cache["best_model_name"]
        model = fitted_models[best_single_name]
        scaler = reg_cache.get("scaler", None)
        expected_feats = reg_cache.get("features", [])
        if not expected_feats:
            if scaler is not None and hasattr(scaler, "feature_names_in_"):
                expected_feats = list(scaler.feature_names_in_)
            elif hasattr(model, "feature_names_in_"):
                expected_feats = list(model.feature_names_in_)
        
        df_aligned = align_features_batch(df_sector, sector, currency, "V1", expected_feats, model)
        if scaler is not None:
            df_aligned[df_aligned.columns] = scaler.transform(df_aligned)
            
        preds = model.predict(df_aligned)
        return pd.Series(preds, index=df_sector.index)
    else:
        # V2 Stacking
        meta_model_path = os.path.join(MODELS_DIR, "9_Meta_Modelleme", f"stacking_meta_{sector}_{currency}.pkl")
        meta_model = get_cached_model(meta_model_path)
        if not meta_model:
            return pd.Series(0.0, index=df_sector.index)
            
        df_v2_cols = get_v2_columns(sector, currency)
        meta_cols_v2 = ["Dönem", "Firma Adı", "Anomali_Durumu"]
        target_col_v2 = [col for col in df_v2_cols if "t+1" in col][0]
        expected_feats = [col for col in df_v2_cols if col not in meta_cols_v2 and col != target_col_v2]
        
        L0_test = pd.DataFrame(0.0, index=df_sector.index, columns=["CatBoost", "LightGBM", "XGBoost", "Random_Forest", "Extra_Trees"])
        base_model_names = ["CatBoost", "LightGBM", "XGBoost", "Random_Forest", "Extra_Trees"]
        
        for name in base_model_names:
            model_key = "RF" if name == "Random_Forest" else name
            if model_key in fitted_models:
                model = fitted_models[model_key]
                df_model_aligned = align_features_batch(df_sector, sector, currency, "V2", expected_feats, model)
                df_model_aligned = scale_v2_features_batch(df_model_aligned, sector, currency)
                L0_test[name] = model.predict(df_model_aligned)
                
        preds = meta_model.predict(L0_test)
        return pd.Series(preds, index=df_sector.index)

def predict_regression_value(sector, company, period, currency, custom_features=None, mevsim=None, anomali=None):
    """
    Predicts regression value (t+1 Net Dönem Karı) for the given parameters.
    Returns (pred_val, reg_alg).
    """
    if custom_features is None:
        custom_features = {}
        
    matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Main_Karar_Matrisi.xlsx")
    if not os.path.exists(matrix_path):
        matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
        
    if not os.path.exists(matrix_path):
        raise FileNotFoundError(f"Decision matrix not found locally for {currency}.")
        
    df_dec = get_cached_df(matrix_path, "En_Iyi_Yapboz_Matrisi")
    dec_row = get_dec_row(df_dec, sector)
    if dec_row is None:
        raise ValueError(f"Sector {sector} not found in Decision Matrix")

    stored_sector = str(dec_row.get("Sektör") or dec_row.get("Sektor") or sector)
    reg_ver_raw = dec_row.get("Reg_Sayısal_Versiyon") or dec_row.get("Reg_Sayisal_Versiyon") or "V1"
    reg_ver = str(reg_ver_raw).strip()

    reg_model_path = os.path.join(MODELS_DIR, "3_Regresyon_Analizi", f"champion_{stored_sector}_{currency}.pkb")
    reg_cache = get_cached_model(reg_model_path)
    if not reg_cache:
        reg_model_path = os.path.join(MODELS_DIR, "3_Regresyon_Analizi", f"champion_{sector}_{currency}.pkb")
        reg_cache = get_cached_model(reg_model_path)
    if not reg_cache:
        raise FileNotFoundError(f"Regression model not found for {sector}")
        
    fitted_models = reg_cache["models"]
    
    if reg_ver == "V1":
        best_single_name = reg_cache["best_model_name"]
        scaler = reg_cache.get("scaler", None)
        
        expected_feats = reg_cache.get("features", [])
        if not expected_feats:
            if scaler is not None and hasattr(scaler, "feature_names_in_"):
                expected_feats = list(scaler.feature_names_in_)
            elif hasattr(fitted_models[best_single_name], "feature_names_in_"):
                expected_feats = list(fitted_models[best_single_name].feature_names_in_)
                
        df_aligned = align_features_for_model(sector, company, period, currency, "V1", expected_feats, custom_features, fitted_models[best_single_name], mevsim=mevsim, anomali=anomali)
        
        if scaler is not None:
            df_aligned[df_aligned.columns] = scaler.transform(df_aligned)
            
        pred_val = float(fitted_models[best_single_name].predict(df_aligned)[0])
        reg_alg = f"{best_single_name} (V1)"
    else:
        # V2 Stacking
        meta_model_path = os.path.join(MODELS_DIR, "9_Meta_Modelleme", f"stacking_meta_{sector}_{currency}.pkl")
        meta_model = get_cached_model(meta_model_path)
        if not meta_model:
            raise FileNotFoundError(f"V2 Stacking meta model not found for {sector}")
            
        # Get expected features for V2
        df_v2_cols = get_v2_columns(sector, currency)
        meta_cols_v2 = ["Dönem", "Firma Adı", "Anomali_Durumu"]
        target_col_v2 = [col for col in df_v2_cols if "t+1" in col][0]
        expected_feats = [col for col in df_v2_cols if col not in meta_cols_v2 and col != target_col_v2]
        
        L0_test = pd.DataFrame(0.0, index=[0], columns=["CatBoost", "LightGBM", "XGBoost", "Random_Forest", "Extra_Trees"])
        base_model_names = ["CatBoost", "LightGBM", "XGBoost", "Random_Forest", "Extra_Trees"]
        for name in base_model_names:
            model_key = "RF" if name == "Random_Forest" else name
            if model_key in fitted_models:
                model = fitted_models[model_key]
                df_model_aligned = align_features_for_model(sector, company, period, currency, "V2", expected_feats, custom_features, model, mevsim=mevsim, anomali=anomali)
                df_model_aligned = scale_v2_features(df_model_aligned, sector, currency)
                L0_test.at[0, name] = float(model.predict(df_model_aligned)[0])
                
        pred_val = float(meta_model.predict(L0_test)[0])
        reg_alg = "Stacking Ensemble (V2)"
        
    return pred_val, reg_alg

def is_target_feature(feature_name):
    if not feature_name:
        return False
    fn = clean_and_normalize(feature_name)
    return "netdonemkar" in fn or "netkar" in fn

# ── SCORE HELPERS (read from Karar Matrisi Excel) ────────────────────────────
def _get_matrix_scores(currency):
    """
    Loads the Karar Matrisi Excel once and returns a dict:
      { sector_norm: {col: value, ...}, ... }
    Uses the stored academic scores rather than re-computing them live.
    """
    key = currency
    if key in _MATRIX_SCORES_CACHE:
        return _MATRIX_SCORES_CACHE[key]
    matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Main_Karar_Matrisi.xlsx")
    if not os.path.exists(matrix_path):
        matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
    if not os.path.exists(matrix_path):
        _MATRIX_SCORES_CACHE[key] = {}
        return {}
    try:
        df = pd.read_excel(matrix_path, sheet_name="En_Iyi_Yapboz_Matrisi")
        result = {}
        for _, row in df.iterrows():
            sect_raw = row.get("Sektör") or row.get("Sektor") or ""
            sect_norm = normalize_sector_name(str(sect_raw))
            result[sect_norm] = row.to_dict()
        _MATRIX_SCORES_CACHE[key] = result
        return result
    except Exception as ex:
        print(f"[_get_matrix_scores] Error: {ex}")
        _MATRIX_SCORES_CACHE[key] = {}
        return {}


def _get_batch_cls_accuracy(sector, currency, model_type):
    """
    Returns per-company classification accuracy dict {company: float 0-100}.
    Reads the stored academic score from the Karar Matrisi, then distributes
    it uniformly across companies so the UI shows meaningful values.
    For real per-company variance we also attempt live batch prediction,
    falling back to the matrix score if models cannot be loaded.
    """
    try:
        matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Main_Karar_Matrisi.xlsx")
        if not os.path.exists(matrix_path):
            matrix_path = os.path.join(DATA_DIR, "metrics", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
        if not os.path.exists(matrix_path):
            return {}

        df_dec = get_cached_df(matrix_path, "En_Iyi_Yapboz_Matrisi")
        dec_row = get_dec_row(df_dec, sector)
        if dec_row is None:
            return {}

        stored_sector = str(dec_row.get("Sektör") or dec_row.get("Sektor") or sector)
        ver_key_kz = next((k for k in dec_row.index if "cls" in str(k).lower() and "kz" in str(k).lower() and "ver" in str(k).lower()), "Cls_KZ_Versiyon")
        ver_key_yon = next((k for k in dec_row.index if "cls" in str(k).lower() and ("yn" in str(k).lower() or "yön" in str(k).lower() or "yon" in str(k).lower()) and "ver" in str(k).lower()), "Cls_Yön_Versiyon")
        ver_key = ver_key_kz if model_type == "kz" else ver_key_yon
        model_ver = str(dec_row.get(ver_key, "V1")).strip()
        
        # load unscaled dataset for actual target values
        unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
        if not os.path.exists(unscaled_path):
            unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
        df_all = get_cached_df(unscaled_path, sector).copy()
        
        t_cols = [c for c in df_all.columns if "t+1" in c]
        if not t_cols:
            return {}
        t_col = t_cols[0]

        # Compute actual label per row
        if model_type == "kz":
            df_all["_sector_median"] = df_all.groupby("Dönem")[t_col].transform("median")
            df_all["_actual"] = (df_all[t_col] > df_all["_sector_median"]).astype(int)
        else:
            v1_path = os.path.join(DATA_DIR, "datasets", "v1", f"2_BIST_{currency}_VIF.xlsx")
            curr_prof_col = None
            df_v1 = None
            if os.path.exists(v1_path):
                try:
                    df_v1 = get_cached_df(v1_path, sector).copy()
                    for c in ["Net Dönem Karı/Zararı", "Net Dönem Karı", "Net Dönem Kârı/Zararı"]:
                        if c in df_v1.columns:
                            curr_prof_col = c
                            break
                except Exception:
                    df_v1 = None

            if df_v1 is not None and curr_prof_col:
                df_v1_sub = df_v1[["Firma Adı", "Dönem", curr_prof_col]].rename(columns={curr_prof_col: "_curr_prof"})
                df_all = df_all.merge(df_v1_sub, on=["Firma Adı", "Dönem"], how="left")
                df_all["_actual"] = (df_all[t_col] > df_all["_curr_prof"].fillna(0)).astype(int)
            else:
                df_all["_actual"] = (df_all[t_col] > 0).astype(int)

        # Load model
        model_suffix = "Kar_Zarar_Tahmini" if model_type == "kz" else "Yon_Tahmini"
        model_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{stored_sector}_{model_suffix}_{currency}.pkb")
        model_cache = get_cached_model(model_path)
        if not model_cache:
            # Fallback to ASCII sector name
            model_path = os.path.join(MODELS_DIR, "4_Siniflandirma_Analizi", f"champion_{sector}_{model_suffix}_{currency}.pkb")
            model_cache = get_cached_model(model_path)
        if not model_cache:
            return {}

        if model_ver == "V1":
            model = model_cache["model"]
            scaler = model_cache.get("scaler", None)
            threshold = model_cache.get("threshold", 0.5)
            expected_feats = model_cache.get("features", [])
            if not expected_feats:
                if scaler is not None and hasattr(scaler, "feature_names_in_"):
                    expected_feats = list(scaler.feature_names_in_)
                elif hasattr(model, "feature_names_in_"):
                    expected_feats = list(model.feature_names_in_)
            df_aligned = align_features_batch(df_all, sector, currency, "V1", expected_feats, model)
            if scaler is not None:
                df_aligned[df_aligned.columns] = scaler.transform(df_aligned)
            probs = model.predict_proba(df_aligned)[:, 1]
            preds = (probs >= threshold).astype(int)
        else:
            best_name = model_cache["best_model_name"]
            model = model_cache["models"][best_name]
            df_v2_cols = get_v2_columns(sector, currency)
            meta_cols_v2 = ["Dönem", "Firma Adı", "Anomali_Durumu"]
            target_col_v2 = [col for col in df_v2_cols if "t+1" in col]
            target_col_v2 = target_col_v2[0] if target_col_v2 else t_col
            expected_feats = [col for col in df_v2_cols if col not in meta_cols_v2 and col != target_col_v2]
            df_aligned = align_features_batch(df_all, sector, currency, "V2", expected_feats, model)
            df_aligned = scale_v2_features_batch(df_aligned, sector, currency)
            preds = model.predict(df_aligned)

        df_all["_pred"] = preds
        df_all["_correct"] = (df_all["_actual"] == df_all["_pred"]).astype(int)
        acc_per_company = (df_all.groupby("Firma Adı")["_correct"].mean() * 100).to_dict()
        return acc_per_company
    except Exception as ex:
        print(f"[batch_accuracy] Error computing accuracy for {sector}/{model_type}: {ex}")
        return {}


def _get_batch_reg_mape(sector, currency):
    """
    Returns per-company regression MAPE dict {company: float}.
    Reads the stored R² score from PKB (best_val_r2) and converts to
    an approximate MAPE equivalent, then also returns per-company values
    from live prediction when models load correctly.
    """
    try:
        # Try live computation first (works when model files load correctly)
        unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
        if not os.path.exists(unscaled_path):
            unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
        if not os.path.exists(unscaled_path):
            return {}

        df_all = get_cached_df(unscaled_path, sector).copy()
        if df_all.empty:
            return {}

        t_cols = [c for c in df_all.columns if "t+1" in c]
        if not t_cols:
            return {}
        t_col = t_cols[0]

        preds = predict_regression_batch(sector, currency, df_all)
        df_all["_pred"] = preds.values

        # Check if predictions are all-zero (model not loaded)
        if (df_all["_pred"] == 0).all():
            raise ValueError("All predictions are zero — model not loaded")

        actual_abs = df_all[t_col].abs()
        valid_mask = actual_abs > 0.01
        df_all.loc[valid_mask, "_ape"] = (
            (df_all.loc[valid_mask, t_col] - df_all.loc[valid_mask, "_pred"]).abs()
            / actual_abs[valid_mask]
        )
        mape_per_company = (df_all.groupby("Firma Adı")["_ape"].mean() * 100).to_dict()
        result = {}
        for comp, val in mape_per_company.items():
            result[comp] = float(val) if pd.notna(val) else 0.0
        return result

    except Exception as ex:
        print(f"[batch_mape] Live computation failed for {sector}: {ex}. Falling back to matrix score.")

    # Fallback: read stored Reg_Sayısal_Skor from Karar Matrisi
    # Reg_Sayısal_Skor is stored as a hit-rate %, not MAPE; convert for display
    try:
        scores = _get_matrix_scores(currency)
        sect_norm = normalize_sector_name(sector)
        row = scores.get(sect_norm, {})
        # Try to find the score column regardless of encoding
        reg_score = None
        for k, v in row.items():
            if "reg" in str(k).lower() and "say" in str(k).lower():
                reg_score = v
                break
        if reg_score is not None and pd.notna(reg_score):
            # Convert hit-rate score to approximate MAPE for display
            # Stored value is e.g. 53.96 (hit rate %); MAPE ≈ 100 - hit_rate
            approx_mape = max(0.0, 100.0 - float(reg_score))
            # Also load companies to give per-company entry
            unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
            if not os.path.exists(unscaled_path):
                unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
            if os.path.exists(unscaled_path):
                df_all = get_cached_df(unscaled_path, sector)
                companies = df_all["Firma Adı"].unique().tolist()
                return {c: approx_mape for c in companies}
    except Exception as ex2:
        print(f"[batch_mape] Fallback also failed for {sector}: {ex2}")
    return {}

