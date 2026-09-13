import os
import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, request, render_template
from utils import DATA_DIR, get_cached_df, predict_regression_batch, is_target_feature

kar_tahmini_bp = Blueprint('kar_tahmini', __name__)

@kar_tahmini_bp.route('/kar-tahmini', methods=['GET'])
def render_page():
    return render_template(
        'kar_tahmini.html',
        active_page='kar_tahmini',
        tab_title='Kâr Tahmini (Regresyon)',
        tab_desc='Yapay zekâ modellerimiz ile çeyreklik kâr tahminleri ve MAPE analizleri.'
    )

@kar_tahmini_bp.route('/api/regression_trend_data', methods=['GET'])
def get_regression_trend_data():
    """
    Returns actual and predicted values for a selected company and feature over all quarters,
    including sector averages, aligning datasets and generating period-by-period comments.
    """
    sector = request.args.get('sector')
    company = request.args.get('company')
    currency = request.args.get('currency', 'USD').upper()
    feature = request.args.get('feature')
    
    if not sector or not company or not feature:
        return jsonify({"error": "sector, company, and feature parameters are required"}), 400
        
    try:
        # Load the raw/unscaled dataset for this currency and sector
        dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
        if not os.path.exists(dataset_path):
            dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
            
        if not os.path.exists(dataset_path):
            return jsonify({"error": f"Dataset not found for currency {currency}."}), 404
            
        df = get_cached_df(dataset_path, sector)
        
        # Calculate batch predictions for all rows in the sector sheet
        df_sector_preds = predict_regression_batch(sector, currency, df)
        df = df.copy()
        df["pred_target"] = df_sector_preds
        
        # Sort periods
        df_comp = df[df["Firma Adı"] == company].sort_values("Dönem")
        periods = df_comp["Dönem"].dropna().astype(int).tolist()
        
        # Target column: find column containing t+1
        target_cols = [c for c in df.columns if "t+1" in c]
        target_col = target_cols[0] if target_cols else None
        
        # We need actual values for the selected feature
        actual_feat_vals = []
        actual_target_vals = []
        pred_target_vals = []
        
        # Sector averages
        sector_avg_feat = []
        sector_avg_pred_target = []
        sector_avg_actual_target = []
        
        # Populate period values
        for p in periods:
            # 1. Company Actual selected feature value
            row = df_comp[df_comp["Dönem"] == p]
            if not row.empty:
                val = row.iloc[0].get(feature, 0.0)
                actual_feat_vals.append(float(val) if pd.notna(val) else 0.0)
                
                # Actual target (t Net Dönem Karı/Zararı)
                t_val = row.iloc[0].get(target_col, 0.0) if target_col else 0.0
                actual_target_vals.append(float(t_val) if pd.notna(t_val) else 0.0)
                
                # Predicted target (t)
                p_val = row.iloc[0].get("pred_target", 0.0)
                pred_target_vals.append(float(p_val) if pd.notna(p_val) else 0.0)
            else:
                actual_feat_vals.append(0.0)
                actual_target_vals.append(0.0)
                pred_target_vals.append(0.0)
                
            # 2. Sector averages
            df_p = df[df["Dönem"] == p]
            if not df_p.empty:
                if feature in df_p.columns:
                    avg_feat = df_p[feature].mean()
                    sector_avg_feat.append(float(avg_feat) if pd.notna(avg_feat) else 0.0)
                else:
                    sector_avg_feat.append(0.0)
                    
                if target_col and target_col in df_p.columns:
                    avg_t = df_p[target_col].mean()
                    sector_avg_actual_target.append(float(avg_t) if pd.notna(avg_t) else 0.0)
                else:
                    sector_avg_actual_target.append(0.0)
                    
                avg_pred = df_p["pred_target"].mean()
                sector_avg_pred_target.append(float(avg_pred) if pd.notna(avg_pred) else 0.0)
            else:
                sector_avg_feat.append(0.0)
                sector_avg_actual_target.append(0.0)
                sector_avg_pred_target.append(0.0)
        
        # Align actual vs predicted based on target vs custom features
        is_target = is_target_feature(feature) or (target_col and feature.lower() in target_col.lower())
        
        final_actual = []
        final_pred = []
        final_sector_actual = []
        final_sector_pred = []
        
        # Find the actual profit column (without t+1)
        actual_profit_cols = [col for col in df.columns if ("net" in col.lower() and ("kar" in col.lower() or "kâr" in col.lower()) and "t+1" not in col.lower())]
        if not actual_profit_cols:
            actual_profit_cols = [col for col in df.columns if "net" in col.lower() and ("kar" in col.lower() or "kâr" in col.lower())]
        actual_profit_col = actual_profit_cols[0] if actual_profit_cols else None

        if is_target and actual_profit_col:
            for i, p in enumerate(periods):
                # Actual profit at period p
                row_curr = df_comp[df_comp["Dönem"] == p]
                val_act = row_curr.iloc[0].get(actual_profit_col, 0.0) if not row_curr.empty else 0.0
                final_actual.append(float(val_act) if pd.notna(val_act) else 0.0)
                
                # Prediction for period p (predicted at p-1)
                row_prev = df_comp[df_comp["Dönem"] == p - 1]
                val_pred = row_prev.iloc[0].get("pred_target", None) if not row_prev.empty else None
                if val_pred is None or pd.isna(val_pred):
                    final_pred.append(None)
                else:
                    final_pred.append(float(val_pred))
                
                # Sector averages actual at period p
                df_p = df[df["Dönem"] == p]
                avg_act = df_p[actual_profit_col].mean() if not df_p.empty and actual_profit_col in df_p.columns else 0.0
                final_sector_actual.append(float(avg_act) if pd.notna(avg_act) else 0.0)
                
                # Sector averages prediction for period p (predicted at p-1)
                df_p_prev = df[df["Dönem"] == p - 1]
                avg_pred = df_p_prev["pred_target"].mean() if not df_p_prev.empty else None
                if avg_pred is None or pd.isna(avg_pred):
                    final_sector_pred.append(None)
                else:
                    final_sector_pred.append(float(avg_pred))
        elif is_target:
            final_actual = actual_target_vals
            final_pred = pred_target_vals
            final_sector_actual = sector_avg_actual_target
            final_sector_pred = sector_avg_pred_target
        else:
            final_actual = actual_feat_vals
            # Compute rolling trend prediction for custom feature
            for i in range(len(periods)):
                if i == 0:
                    final_pred.append(actual_feat_vals[0])
                else:
                    prev_vals = actual_feat_vals[max(0, i-3):i]
                    final_pred.append(float(np.mean(prev_vals)))
            
            final_sector_actual = sector_avg_feat
            for i in range(len(periods)):
                if i == 0:
                    final_sector_pred.append(sector_avg_feat[0])
                else:
                    prev_vals = sector_avg_feat[max(0, i-3):i]
                    final_sector_pred.append(float(np.mean(prev_vals)))
                    
        # Generate detailed period-by-period comment narrative
        errors = []
        for a, p in zip(final_actual, final_pred):
            if p is not None and a != 0:
                errors.append(abs(a - p) / abs(a))
            else:
                errors.append(0.0)
        avg_mape = np.mean(errors) * 100 if errors else 0.0
        
        narrative_parts = []
        narrative_parts.append(f"<p style='margin-bottom: 12px; font-weight: 500;'><strong>{company} &mdash; {feature}</strong> kalemi üzerinde gerçekleştirilen zaman serisi karşılaştırma analizi sonuçları aşağıdadır. Yapay zekâ modelimizin bu kalemde elde ettiği ortalama mutlak yüzde hata (MAPE) oranı: <strong style='color: var(--color-gold);'>%{avg_mape:.2f}</strong>'dir.</p>")
        
        narrative_parts.append("<div class='period-narrative-list' style='display: flex; flex-direction: column; gap: 8px;'>")
        
        for i, p in enumerate(periods):
            act = final_actual[i]
            prd = final_pred[i]
            
            if prd is None:
                narrative_parts.append(
                    f"<div style='border-left: 3px solid #94a3b8; padding: 4px 10px; background: rgba(255,255,255,0.01); border-radius: 0 6px 6px 0;'>"
                    f"<strong>Çeyrek {p}:</strong> Gerçekleşen: <span style='font-family: monospace;'>{act:,.2f}</span> | "
                    f"Öngörülen: <span style='font-family: monospace;'>Veri yok</span>"
                    f"</div>"
                )
                continue
                
            diff = act - prd
            err_pct = (abs(diff) / abs(act) * 100) if act != 0 else 0.0
            
            act_str = f"{act:,.2f}"
            prd_str = f"{prd:,.2f}"
            
            period_label = f"Çeyrek {p}"
            
            if act == 0 and prd == 0:
                status = "Veri bulunamadı"
                color = "#94a3b8"
            elif err_pct <= 10.0:
                status = f"<span style='color:#00f27c; font-weight:600;'>Yüksek Kararlılık (%{err_pct:.1f} hata)</span>"
                color = "#00f27c"
            elif err_pct <= 25.0:
                status = f"<span style='color:var(--color-gold); font-weight:600;'>Kabul Edilebilir Sapma (%{err_pct:.1f} hata)</span>"
                color = "var(--color-gold)"
            else:
                status = f"<span style='color:#ae52ff; font-weight:600;'>Yüksek Sapma (%{err_pct:.1f} hata)</span>"
                color = "#ae52ff"
                
            trend_comment = ""
            if i > 0:
                prev_act = final_actual[i-1]
                if prev_act != 0:
                    change = (act - prev_act) / abs(prev_act) * 100
                    if change > 30:
                        trend_comment = f" &mdash; Bir önceki çeyreğe göre <strong style='color:#00f27c;'>%{change:.1f} büyüme</strong> kaydedilmiştir."
                    elif change < -30:
                        trend_comment = f" &mdash; Bir önceki çeyreğe göre <strong style='color:#ff5252;'>%{change:.1f} daralma</strong> kaydedilmiştir."
            
            narrative_parts.append(
                f"<div style='border-left: 3px solid {color}; padding: 4px 10px; background: rgba(255,255,255,0.01); border-radius: 0 6px 6px 0;'>"
                f"<strong>{period_label}:</strong> Gerçekleşen: <span style='font-family: monospace;'>{act_str}</span> | "
                f"Öngörülen: <span style='font-family: monospace;'>{prd_str}</span> &mdash; {status}{trend_comment}"
                f"</div>"
            )
            
        narrative_parts.append("</div>")
        analysis_comment = "\n".join(narrative_parts)
            
        result = {
            "periods": [str(p) for p in periods],
            "target_col": target_col,
            "feature": feature,
            "is_target": is_target,
            "company_actual": final_actual,
            "company_pred": final_pred,
            "sector_avg_actual": final_sector_actual,
            "sector_avg_pred": final_sector_pred,
            "analysis_comment": analysis_comment
        }
        return jsonify(result)
    except Exception as ex:
        print(f"Error in get_regression_trend_data: {ex}")
        return jsonify({"error": str(ex)}), 500
