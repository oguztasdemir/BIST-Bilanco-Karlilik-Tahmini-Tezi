import os
import pandas as pd
import numpy as np
from flask import Blueprint, jsonify, request, render_template
from utils import DATA_DIR, clean_and_normalize, predict_regression_batch, normalize_sector_name

rakip_analizi_bp = Blueprint('rakip_analizi', __name__)

@rakip_analizi_bp.route('/rakip-analizi', methods=['GET'])
def render_page():
    return render_template(
        'rakip_analizi.html',
        active_page='rakip_analizi',
        tab_title='Rakip Analizi',
        tab_desc='BIST şirketlerinin sektörel kârlılık sıralamaları ve rakip kıyaslamaları.'
    )

@rakip_analizi_bp.route('/api/competitor_analysis', methods=['GET'])
def get_competitor_analysis():
    """Generates competitor ranking and comparative metrics for a company within its sector across all periods."""
    sector = request.args.get('sector')
    company = request.args.get('company')
    competitor = request.args.get('competitor')
    currency = request.args.get('currency', 'USD').upper()
    
    if not sector or not company:
        return jsonify({"error": "sector and company parameters are required"}), 400
        
    # Standardize competitor parameter
    if competitor == company or competitor == "":
        competitor = None
        
    try:
        unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
        if not os.path.exists(unscaled_path):
            unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
            
        if not os.path.exists(unscaled_path):
            return jsonify({"error": f"Dataset for currency {currency} not found."}), 404
            
        # Find matched sheet name
        xls = pd.ExcelFile(unscaled_path)
        matched_sheet = None
        for sheet in xls.sheet_names:
            if normalize_sector_name(sheet) == normalize_sector_name(sector):
                matched_sheet = sheet
                break

                
        if not matched_sheet:
            return jsonify({"error": f"Sector {sector} not found in dataset."}), 404
            
        df = pd.read_excel(unscaled_path, sheet_name=matched_sheet)
        
        # Calculate regression predictions in batch
        df_preds = pd.Series(0.0, index=df.index)
        try:
            df_preds = predict_regression_batch(matched_sheet, currency, df)
        except Exception as ex:
            print(f"Error predicting regression batch in competitor analysis: {ex}")
        
        # Get target column (Actual Net Profit)
        actual_profit_cols = [col for col in df.columns if ("net" in col.lower() and ("kar" in col.lower() or "kâr" in col.lower()) and "t+1" not in col.lower())]
        if not actual_profit_cols:
            actual_profit_cols = [col for col in df.columns if "net" in col.lower() and ("kar" in col.lower() or "kâr" in col.lower())]
        if not actual_profit_cols:
            return jsonify({"error": "Net Dönem Karı column not found in dataset."}), 404
        target_col = actual_profit_cols[0]
        
        # Find all unique periods in dataset
        all_periods = sorted(df["Dönem"].unique().tolist())
        periods_data = []
        
        for p in all_periods:
            df_period = df[df["Dönem"] == p]
            if df_period.empty:
                continue
                
            # Extract companies and their target values for this period
            comp_data = []
            for idx, row in df_period.iterrows():
                c_name = row["Firma Adı"]
                val = row[target_col]
                if pd.notna(val):
                    comp_data.append({
                        "company": c_name,
                        "value": float(val)
                    })
                    
            if not comp_data:
                continue
                
            # Sort descending by value
            comp_data.sort(key=lambda x: x["value"], reverse=True)
            
            # Find selected company's details in this period
            company_val = None
            company_rank = None
            company_pred_val = 0.0
            
            for i, item in enumerate(comp_data):
                if item["company"] == company:
                    company_val = item["value"]
                    company_rank = i + 1
                    break
                    
            if company_rank is None:
                continue  # Company doesn't have data in this period
                
            # Fetch company's predicted value for this period
            df_comp_p = df_period[df_period["Firma Adı"] == company]
            if not df_comp_p.empty:
                idx = df_comp_p.index[0]
                if idx in df_preds.index:
                    company_pred_val = float(df_preds.loc[idx])
            
            # Competitor check
            competitor_val = None
            competitor_rank = None
            competitor_pred_val = 0.0
            
            if competitor:
                for i, item in enumerate(comp_data):
                    if item["company"] == competitor:
                        competitor_val = item["value"]
                        competitor_rank = i + 1
                        break
                
                df_competitor_p = df_period[df_period["Firma Adı"] == competitor]
                if not df_competitor_p.empty:
                    idx_comp = df_competitor_p.index[0]
                    if idx_comp in df_preds.index:
                        competitor_pred_val = float(df_preds.loc[idx_comp])
                
            total_cos = len(comp_data)
            values = [x["value"] for x in comp_data]
            
            sector_avg = float(np.mean(values))
            sector_median = float(np.median(values))
            sector_min = float(np.min(values))
            sector_max = float(np.max(values))
            
            percentile = (1 - (company_rank - 1) / total_cos) * 100
            ratio_to_avg = (company_val / sector_avg * 100) if sector_avg != 0 else 0.0
            ratio_to_median = (company_val / sector_median * 100) if sector_median != 0 else 0.0
            
            position_desc = ""
            if percentile >= 90:
                position_desc = "Sektörün En Yüksek Kârlılığa Sahip Lider Grubunda"
            elif percentile >= 75:
                position_desc = "Sektör Ortalamasının Üzerinde"
            elif percentile >= 50:
                position_desc = "Sektör Medyanı Üzerinde Dengeli Seviyede"
            elif percentile >= 25:
                position_desc = "Sektör Medyanının Altında, Orta Seviyede"
            else:
                position_desc = "Sektörün En Düşük Kârlılık Grubunda"
                
            # Competitor position details
            competitor_percentile = None
            competitor_position_desc = ""
            if competitor_rank is not None:
                competitor_percentile = (1 - (competitor_rank - 1) / total_cos) * 100
                if competitor_percentile >= 90:
                    competitor_position_desc = "Sektörün En Yüksek Kârlılığa Sahip Lider Grubunda"
                elif competitor_percentile >= 75:
                    competitor_position_desc = "Sektör Ortalamasının Üzerinde"
                elif competitor_percentile >= 50:
                    competitor_position_desc = "Sektör Medyanı Üzerinde Dengeli Seviyede"
                elif competitor_percentile >= 25:
                    competitor_position_desc = "Sektör Medyanının Altında, Orta Seviyede"
                else:
                    competitor_position_desc = "Sektörün En Düşük Kârlılık Grubunda"
                
            periods_data.append({
                "period": int(p),
                "company_value": company_val,
                "company_pred_value": company_pred_val,
                "company_rank": company_rank,
                "total_companies": total_cos,
                "sector_avg": sector_avg,
                "sector_median": sector_median,
                "sector_min": sector_min,
                "sector_max": sector_max,
                "percentile": percentile,
                "ratio_to_avg": ratio_to_avg,
                "ratio_to_median": ratio_to_median,
                "position_desc": position_desc,
                
                # Competitor details
                "competitor_value": competitor_val,
                "competitor_pred_value": competitor_pred_val,
                "competitor_rank": competitor_rank,
                "competitor_percentile": competitor_percentile,
                "competitor_position_desc": competitor_position_desc
            })
            
        if not periods_data:
            return jsonify({"error": f"Company {company} has no valid data in any period of sector {sector}."}), 404
            
        # Calculate overall sector size rank for the company
        try:
            mean_profits = df.groupby("Firma Adı")[target_col].mean()
            ranks_overall = mean_profits.rank(ascending=False, method='min')
            company_overall_rank = int(ranks_overall.get(company, 999))
        except Exception:
            company_overall_rank = 1
            
        ranks = [x["company_rank"] for x in periods_data]
        percentiles = [x["percentile"] for x in periods_data]
        
        avg_rank = company_overall_rank # Use overall integer size rank
        best_idx = int(np.argmin(ranks))
        worst_idx = int(np.argmax(ranks))
        
        best_rank = periods_data[best_idx]["company_rank"]
        best_rank_period = periods_data[best_idx]["period"]
        best_rank_total = periods_data[best_idx]["total_companies"]
        
        worst_rank = periods_data[worst_idx]["company_rank"]
        worst_rank_period = periods_data[worst_idx]["period"]
        worst_rank_total = periods_data[worst_idx]["total_companies"]
        
        avg_percentile = float(np.mean(percentiles))
        
        overall_pos = ""
        if avg_percentile >= 75:
            overall_pos = "güçlü bir sektörel liderlik sergilemekte ve kârlılıkta ön sıralarda yer almaktadır"
        elif avg_percentile >= 50:
            overall_pos = "sektör ortalamasının üstünde stabil ve dengeli bir performans sürdürmektedir"
        elif avg_percentile >= 25:
            overall_pos = "sektör medyanının gerisinde kalarak kârlılık açısından orta-düşük grupta yer almaktadır"
        else:
            overall_pos = "sektör genelinin oldukça gerisinde kalarak düşük kârlılık grubunda konumlanmaktadır"
            
        # Let's generate a narrative commentary
        trend_direction = ""
        if len(periods_data) > 1:
            first_rank = periods_data[0]["company_rank"]
            last_rank = periods_data[-1]["company_rank"]
            if last_rank < first_rank:
                trend_direction = "analiz edilen dönemler boyunca sektör içi sıralamasını iyileştirerek yükselen bir trend sergilemiştir"
            elif last_rank > first_rank:
                trend_direction = "analiz edilen dönemler boyunca sektör içi sıralamasında gerileme yaşamış ve kârlılık payını kaybetmiştir"
            else:
                trend_direction = "dönemler genelinde sektör içi rekabet pozisyonunu korumuş ve stabil kalmıştır"
        else:
            trend_direction = "tek dönemlik veriyle analiz edilmiş olup rekabet performansı stabil gözükmektedir"
            
        narrative = (
            f"<strong>{company}</strong> firması, <strong>{matched_sheet}</strong> sektöründe "
            f"analiz edilen tüm çeyrekler genelinde <strong>{overall_pos}</strong>.<br><br>"
            f"Şirket, tüm çeyrekler genelinde ortalama <strong>{avg_rank:.1f}.</strong> sırada yer almaktadır. "
            f"En başarılı performansını <strong>{best_rank_period}. Çeyrekte</strong> "
            f"<strong>{best_rank_total}</strong> firma arasından <strong>{best_rank}.</strong> olarak elde etmiş; "
            f"en düşük sıralamasını ise <strong>{worst_rank_period}. Çeyrekte</strong> "
            f"<strong>{worst_rank_total}</strong> firma arasından <strong>{worst_rank}.</strong> olarak kaydetmiştir.<br><br>"
            f"Şirket, {trend_direction}."
        )
        
        # Calculate positive/negative profit and sector win stats for company
        co_valid_data = [x for x in periods_data if x["company_value"] is not None]
        company_stats = {
            "total_periods": len(co_valid_data),
            "positive_periods": sum(1 for x in co_valid_data if x["company_value"] > 0),
            "negative_periods": sum(1 for x in co_valid_data if x["company_value"] <= 0),
            "above_avg_periods": sum(1 for x in co_valid_data if x["company_value"] > x["sector_avg"]),
            "above_median_periods": sum(1 for x in co_valid_data if x["company_value"] > x["sector_median"])
        }
        
        pos_pct = (company_stats["positive_periods"] / company_stats["total_periods"] * 100) if company_stats["total_periods"] > 0 else 0.0
        narrative += (
            f"<br><br><strong>Kârlılık Özeti:</strong> Şirket analiz edilen <strong>{company_stats['total_periods']}</strong> dönemin "
            f"<strong>{company_stats['positive_periods']}</strong> tanesinde pozitif kâr, "
            f"<strong>{company_stats['negative_periods']}</strong> tanesinde ise zarar açıklamıştır. "
            f"Kâr açıklama sıklığı <strong>%{pos_pct:.1f}</strong> seviyesindedir. "
            f"Dönemlerin <strong>{company_stats['above_avg_periods']}</strong> tanesinde sektör ortalamasının, "
            f"<strong>{company_stats['above_median_periods']}</strong> tanesinde ise sektör medyanının üzerinde kâr elde etmeyi başarmıştır."
        )
        
        # Competitor stats
        competitor_avg_rank = None
        competitor_best_rank = None
        competitor_best_rank_period = None
        competitor_best_rank_total = None
        competitor_worst_rank = None
        competitor_worst_rank_period = None
        competitor_worst_rank_total = None
        competitor_stats = None
        
        if competitor:
            try:
                mean_profits_comp = df.groupby("Firma Adı")[target_col].mean()
                competitor_overall_rank = int(mean_profits_comp.rank(ascending=False, method='min').get(competitor, 999))
            except Exception:
                competitor_overall_rank = 1
                
            comp_periods = [x for x in periods_data if x["competitor_rank"] is not None]
            if comp_periods:
                competitor_avg_rank = competitor_overall_rank
                comp_ranks = [x["competitor_rank"] for x in comp_periods]
                best_comp_idx = int(np.argmin(comp_ranks))
                worst_comp_idx = int(np.argmax(comp_ranks))
                
                competitor_best_rank = comp_periods[best_comp_idx]["competitor_rank"]
                competitor_best_rank_period = comp_periods[best_comp_idx]["period"]
                competitor_best_rank_total = comp_periods[best_comp_idx]["total_companies"]
                
                competitor_worst_rank = comp_periods[worst_comp_idx]["competitor_rank"]
                competitor_worst_rank_period = comp_periods[worst_comp_idx]["period"]
                competitor_worst_rank_total = comp_periods[worst_comp_idx]["total_companies"]
                
                # Calculate positive/negative profit and sector win stats for competitor
                comp_valid_data = [x for x in periods_data if x["competitor_value"] is not None]
                competitor_stats = {
                    "total_periods": len(comp_valid_data),
                    "positive_periods": sum(1 for x in comp_valid_data if x["competitor_value"] > 0),
                    "negative_periods": sum(1 for x in comp_valid_data if x["competitor_value"] <= 0),
                    "above_avg_periods": sum(1 for x in comp_valid_data if x["competitor_value"] > x["sector_avg"]),
                    "above_median_periods": sum(1 for x in comp_valid_data if x["competitor_value"] > x["sector_median"])
                }
                
                comp_pos_pct = (competitor_stats["positive_periods"] / competitor_stats["total_periods"] * 100) if competitor_stats["total_periods"] > 0 else 0.0
                
                narrative += (
                    f"<br><br><strong>Rakip Firma Kıyaslaması:</strong> Karşılaştırılan <strong>{competitor}</strong> firması, "
                    f"sektör büyüklük sıralamasında <strong>{competitor_avg_rank}.</strong> sırada yer almaktadır. "
                    f"En iyi sıralamasını <strong>{competitor_best_rank_period}. Çeyrekte</strong> "
                    f"<strong>{competitor_best_rank_total}</strong> firma arasından <strong>{competitor_best_rank}.</strong> olarak; "
                    f"en düşük sıralamasını ise <strong>{competitor_worst_rank_period}. Çeyrekte</strong> "
                    f"<strong>{competitor_worst_rank_total}</strong> firma arasından <strong>{competitor_worst_rank}.</strong> olarak kaydetmiştir. "
                    f"<br>Rakip firma, analiz edilen <strong>{competitor_stats['total_periods']}</strong> dönemin "
                    f"<strong>{competitor_stats['positive_periods']}</strong> tanesinde pozitif kâr, "
                    f"<strong>{competitor_stats['negative_periods']}</strong> tanesinde ise zarar açıklamıştır (kârlılık sıklığı: %{comp_pos_pct:.1f}). "
                    f"Dönemlerin <strong>{competitor_stats['above_avg_periods']}</strong> tanesinde sektör ortalamasını, "
                    f"<strong>{competitor_stats['above_median_periods']}</strong> tanesinde ise sektör medyanını geçmiştir."
                )
        
        narrative += f"<br><br>Kârlılık seviyesinin sektör ortalaması ve medyanı ile çeyreklik değişimi grafiklerde gösterilmektedir."
        
        return jsonify({
            "company": company,
            "competitor": competitor,
            "sector": matched_sheet,
            "currency": currency,
            "periods_data": periods_data,
            "avg_rank": avg_rank,
            "best_rank": best_rank,
            "best_rank_period": best_rank_period,
            "best_rank_total": best_rank_total,
            "worst_rank": worst_rank,
            "worst_rank_period": worst_rank_period,
            "worst_rank_total": worst_rank_total,
            "avg_percentile": avg_percentile,
            "narrative": narrative,
            "company_stats": company_stats,
            "competitor_stats": competitor_stats,
            
            # Competitor stats
            "competitor_avg_rank": competitor_avg_rank,
            "competitor_best_rank": competitor_best_rank,
            "competitor_best_rank_period": competitor_best_rank_period,
            "competitor_best_rank_total": competitor_best_rank_total,
            "competitor_worst_rank": competitor_worst_rank,
            "competitor_worst_rank_period": competitor_worst_rank_period,
            "competitor_worst_rank_total": competitor_worst_rank_total
        })
    except Exception as ex:
        print(f"Error in competitor_analysis: {ex}")
        return jsonify({"error": str(ex)}), 500
