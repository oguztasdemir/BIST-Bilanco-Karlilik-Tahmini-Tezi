import os
import pandas as pd
from flask import Blueprint, jsonify, request, render_template
from utils import DATA_DIR, get_cached_df, _BATCH_ACC_CACHE, _get_batch_cls_accuracy, _BATCH_MAPE_CACHE, _get_batch_reg_mape

trend_analizi_bp = Blueprint('trend_analizi', __name__)

@trend_analizi_bp.route('/trend-analizi', methods=['GET'])
def render_page():
    return render_template(
        'trend_analizi.html',
        active_page='trend_analizi',
        tab_title='Sektörel Trend Analizi',
        tab_desc='Seçilen şirketlerin finansal verilerinin zaman serisi grafik analizleri.'
    )

@trend_analizi_bp.route('/api/companies', methods=['GET'])
def get_companies():
    """Lists unique company names in a sector, optionally formatted with ranking or accuracy based on task."""
    sector = request.args.get('sector')
    task = request.args.get('task')
    currency = request.args.get('currency', 'USD').upper()
    
    if not sector:
        return jsonify({"error": "sector parameter is required"}), 400
    try:
        # Load dataset
        unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"4_BIST_{currency}_RFE_Secilmis.xlsx")
        if not os.path.exists(unscaled_path):
            unscaled_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
            
        if not os.path.exists(unscaled_path):
            return jsonify({"error": "Local dataset not found."}), 404
            
        df = get_cached_df(unscaled_path, sector)
        companies_list = sorted(df["Firma Adı"].unique().tolist())
        
        result_companies = []
        
        if task == 'ranking':
            t_cols = [c for c in df.columns if "t+1" in c]
            if t_cols:
                t_col = t_cols[0]
                mean_profits = df.groupby("Firma Adı")[t_col].mean()
                ranks = mean_profits.rank(ascending=False, method='min')
                ranked_companies = sorted(companies_list, key=lambda c: ranks.get(c, 999))
                for c in ranked_companies:
                    rank_val = int(ranks.get(c, 999))
                    result_companies.append({
                        "name": c,
                        "label": f"({rank_val}.) {c}"
                    })
                return jsonify({"companies": result_companies})
        
        elif task in ('classification_kz', 'classification_yon'):
            model_type = "kz" if task == "classification_kz" else "yon"
            cache_key = (sector, currency, task)
            if cache_key in _BATCH_ACC_CACHE:
                acc_map = _BATCH_ACC_CACHE[cache_key]
            else:
                acc_map = _get_batch_cls_accuracy(sector, currency, model_type)
                _BATCH_ACC_CACHE[cache_key] = acc_map

            for c in companies_list:
                acc = acc_map.get(c)
                if acc is not None:
                    label = f"{c}  (%{acc:.0f} Başarı)"
                else:
                    label = c
                result_companies.append({"name": c, "label": label})
            return jsonify({"companies": result_companies})
        
        elif task == 'regression_mape':
            cache_key = (sector, currency)
            if cache_key in _BATCH_MAPE_CACHE:
                mape_map = _BATCH_MAPE_CACHE[cache_key]
            else:
                mape_map = _get_batch_reg_mape(sector, currency)
                _BATCH_MAPE_CACHE[cache_key] = mape_map

            for c in companies_list:
                mape = mape_map.get(c)
                if mape is not None:
                    label = f"{c}  (%{mape:.1f} MAPE Hatası)"
                else:
                    label = c
                result_companies.append({"name": c, "label": label})
            return jsonify({"companies": result_companies})
        
        # Default/Fallback behavior
        actual_profit_cols = [col for col in df.columns if ("net" in col.lower() and ("kar" in col.lower() or "kâr" in col.lower()) and "t+1" not in col.lower())]
        if not actual_profit_cols:
            actual_profit_cols = [col for col in df.columns if "net" in col.lower() and ("kar" in col.lower() or "kâr" in col.lower())]
            
        if actual_profit_cols:
            profit_col = actual_profit_cols[0]
            profit_sums = df.groupby("Firma Adı")[profit_col].sum().fillna(0)
            sorted_companies = profit_sums.sort_values(ascending=False).index.tolist()
            remaining = [c for c in companies_list if c not in sorted_companies]
            final_companies = sorted_companies + remaining
        else:
            final_companies = companies_list
            
        for idx, c in enumerate(final_companies, 1):
            result_companies.append({
                "name": c,
                "label": f"{idx}- {c}"
            })
            
        return jsonify({"companies": result_companies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@trend_analizi_bp.route('/api/periods', methods=['GET'])
def get_periods():
    """Lists unique periods for a company in a sector."""
    sector = request.args.get('sector')
    company = request.args.get('company')
    version = request.args.get('version', 'V1').upper()
    currency = request.args.get('currency', 'USD').upper()
    if not sector or not company:
        return jsonify({"error": "sector and company parameters are required"}), 400
    try:
        if version == 'ZEKI_ELEME':
            dataset_path = os.path.join(DATA_DIR, "zeki_eleme", f"3_Final_Filtreli_Veri_{currency}.xlsx")
        elif version == 'V2':
            dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{currency}_Scaled.xlsx")
        else:
            dataset_path = os.path.join(DATA_DIR, "datasets", "v1", f"2_BIST_{currency}_VIF.xlsx")
            
        if not os.path.exists(dataset_path):
            return jsonify({"error": f"Local dataset not found: {dataset_path}"}), 404
        
        df = get_cached_df(dataset_path, sector)
        df_comp = df[df["Firma Adı"] == company]
        periods = sorted(df_comp["Dönem"].unique().tolist())
        return jsonify({"periods": periods})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@trend_analizi_bp.route('/api/trend_data', methods=['GET'])
def get_trend_data():
    """Gets historical financial features for plotting time-series line charts across multiple companies and currencies."""
    sector = request.args.get('sector')
    companies = request.args.getlist('company')
    features = request.args.getlist('features') # list of features
    version = request.args.get('version', 'V2').upper()
    currencies = request.args.getlist('currency')
    show_avg = request.args.get('show_avg', 'false').lower() == 'true'
    
    # Backward compatibility for companies
    if not companies:
        single_company = request.args.get('company')
        if single_company:
            companies = [single_company]
            
    # Backward compatibility for currency
    if not currencies:
        single_curr = request.args.get('currency', 'USD').upper()
        currencies = [single_curr]
    else:
        currencies = [c.upper() for c in currencies]
            
    if not sector or not companies or not features:
        return jsonify({"error": "sector, company, and features are required"}), 400
        
    try:
        all_periods = set()
        dfs = {}
        
        # Load sheets for each currency
        for curr in currencies:
            if version == 'ZEKI_ELEME':
                dataset_path = os.path.join(DATA_DIR, "zeki_eleme", f"3_Final_Filtreli_Veri_{curr}.xlsx")
            elif version == 'V1':
                dataset_path = os.path.join(DATA_DIR, "datasets", "v1", f"2_BIST_{curr}_VIF.xlsx")
            else:
                dataset_path = os.path.join(DATA_DIR, "datasets", "v2", f"5_BIST_{curr}_Scaled.xlsx")
                
            if not os.path.exists(dataset_path):
                return jsonify({"error": f"Dataset not found for currency {curr} and version {version}."}), 404
                
            df = get_cached_df(dataset_path, sector)
            dfs[curr] = df
            
            df_comp_all = df[df["Firma Adı"].isin(companies)]
            for p in df_comp_all["Dönem"].dropna().tolist():
                all_periods.add(int(p))
                
        periods = sorted(list(all_periods))
        result = {"periods": [str(p) for p in periods], "data": {}}
        
        # Populate values for each currency, company, and feature combination
        for curr in currencies:
            df = dfs.get(curr)
            if df is None:
                continue
                
            for comp in companies:
                df_c = df[df["Firma Adı"] == comp]
                period_val_map = {}
                for _, r in df_c.iterrows():
                    try:
                        p_key = int(r["Dönem"])
                        period_val_map[p_key] = r
                    except (ValueError, TypeError):
                        continue
                        
                for feat in features:
                    # Line label varies depending on count of currencies
                    if len(currencies) > 1:
                        line_name = f"{comp} ({curr}) - {feat}"
                    else:
                        line_name = f"{comp} - {feat}"
                        
                    vals = []
                    for p in periods:
                        row_data = period_val_map.get(p)
                        if row_data is not None and feat in row_data:
                            val = row_data[feat]
                            vals.append(float(val) if pd.notna(val) else 0.0)
                        else:
                            vals.append(0.0)
                    result["data"][line_name] = vals
                    
            # Compute sector averages per currency if enabled
            if show_avg:
                for feat in features:
                    if len(currencies) > 1:
                        line_name = f"Sektör Ortalaması ({curr}) - {feat}"
                    else:
                        line_name = f"Sektör Ortalaması - {feat}"
                    vals = []
                    for p in periods:
                        df_p = df[df["Dönem"] == p]
                        if not df_p.empty and feat in df_p.columns:
                            mean_val = df_p[feat].mean()
                            vals.append(float(mean_val) if pd.notna(mean_val) else 0.0)
                        else:
                            vals.append(0.0)
                    result["data"][line_name] = vals
                    
        # Compute company general stats & ranking
        summary_stats = {}
        report_curr = currencies[0] if currencies else "USD"
        df_report = dfs.get(report_curr)
        
        # Identify the sector net profit column for ranks
        ranks_map = {}
        if df_report is not None:
            actual_profit_cols = [col for col in df_report.columns if ("net" in col.lower() and ("kar" in col.lower() or "kâr" in col.lower()) and "t+1" not in col.lower())]
            if not actual_profit_cols:
                actual_profit_cols = [col for col in df_report.columns if "net" in col.lower() and ("kar" in col.lower() or "kâr" in col.lower())]
            
            if actual_profit_cols:
                profit_col = actual_profit_cols[0]
                sector_sums = df_report.groupby("Firma Adı")[profit_col].sum().fillna(0)
                sector_ranks = sector_sums.rank(ascending=False, method='min')
                for c_name, r_val in sector_ranks.items():
                    ranks_map[c_name] = int(r_val)

            for comp in companies:
                df_c = df_report[df_report["Firma Adı"] == comp]
                comp_stats = {}
                for feat in features:
                    if feat in df_c.columns:
                        vals = df_c[feat].dropna().tolist()
                        vals = [float(v) for v in vals]
                    else:
                        vals = []
                    if vals:
                        comp_stats[feat] = {
                            "sum": sum(vals),
                            "mean": sum(vals) / len(vals),
                            "max": max(vals),
                            "min": min(vals),
                            "last": vals[-1] if len(vals) > 0 else 0.0,
                            "count": len(vals)
                        }
                    else:
                        comp_stats[feat] = {
                            "sum": 0.0,
                            "mean": 0.0,
                            "max": 0.0,
                            "min": 0.0,
                            "last": 0.0,
                            "count": 0
                        }
                summary_stats[comp] = {
                    "stats": comp_stats,
                    "rank": ranks_map.get(comp, 999)
                }
                
        # Generate narrative commentary
        narratives = []
        if len(companies) > 0 and df_report is not None and features:
            main_feat = features[0]
            comp_sums = []
            for comp in companies:
                feat_sum = summary_stats.get(comp, {}).get("stats", {}).get(main_feat, {}).get("sum", 0.0)
                comp_sums.append((comp, feat_sum))
            comp_sums.sort(key=lambda x: x[1], reverse=True)
            
            narratives.append(f"<h4 style='color: var(--color-blue); margin-bottom: 12px;'><i class='fa-solid fa-chart-line'></i> {main_feat} Odaklı Sektörel Karşılaştırma Raporu</h4>")
            narratives.append(f"Seçilen firmalar arasında, <strong>{main_feat}</strong> kalemi baz alındığında ")
            
            if len(comp_sums) > 1:
                leader = comp_sums[0][0]
                runner_up = comp_sums[1][0]
                leader_val = comp_sums[0][1]
                runner_up_val = comp_sums[1][1]
                diff = leader_val - runner_up_val
                
                narratives.append(
                    f"toplamda <strong>{leader_val:,.0f} {report_curr}</strong> kümülatif değer ile <strong>{leader}</strong> lider konumdadır. "
                    f"Onu <strong>{runner_up_val:,.0f} {report_curr}</strong> kümülatif değer ile <strong>{runner_up}</strong> takip etmektedir. "
                    f"Lider ile takipçisi arasındaki fark <strong>{diff:,.0f} {report_curr}</strong> seviyesindedir.<br><br>"
                )
                
                narratives.append("<strong>Dönemsel Performans Karşılaştırmaları:</strong><ul style='margin-left: 20px; margin-top: 10px; display: flex; flex-direction: column; gap: 8px;'>")
                for comp, _ in comp_sums:
                    c_stats = summary_stats[comp]["stats"][main_feat]
                    narratives.append(
                        f"<li><strong>{comp}</strong>: Sektördeki genel kümülatif kâr sıralamasında <strong>{ranks_map.get(comp, 999)}.</strong> sırada yer almaktadır. Çeyreklik bazda ortalama <strong>{c_stats['mean']:,.0f} {report_curr}</strong> değer üretirken, tek bir çeyrekte ulaştığı en yüksek değer <strong>{c_stats['max']:,.0f} {report_curr}</strong> olmuştur. Son çeyrekte ise <strong>{c_stats['last']:,.0f} {report_curr}</strong> açıklamıştır.</li>"
                    )
                narratives.append("</ul>")
                
                narratives.append("<br><strong>Yapay Zekâ Analiz Notu:</strong> ")
                if leader_val > 2 * runner_up_val:
                    narratives.append(f"<strong>{leader}</strong> firması kümülatif bazda en yakın rakibi <strong>{runner_up}</strong>'a kıyasla 2 katından fazla büyüklüğe sahip olup, sektörde baskın bir pazar payı ve mali üstünlük sergilemektedir.")
                else:
                    narratives.append(f"Sektörde <strong>{leader}</strong> ve <strong>{runner_up}</strong> arasında dengeli bir rekabet mevcuttur; pazar liderliği dönemsel finansal dalgalanmalara karşı hassastır.")
            else:
                comp = comp_sums[0][0]
                c_val = comp_sums[0][1]
                c_stats = summary_stats[comp]["stats"][main_feat]
                narratives.append(
                    f"kümülatif <strong>{c_val:,.0f} {report_curr}</strong> değer ile <strong>{comp}</strong> tek başına incelenmiştir. "
                    f"Şirket çeyreklik bazda ortalama <strong>{c_stats['mean']:,.0f} {report_curr}</strong> değer üretirken, "
                    f"en yüksek çeyreklik değeri <strong>{c_stats['max']:,.0f} {report_curr}</strong> ve son açıklanan çeyreklik değeri <strong>{c_stats['last']:,.0f} {report_curr}</strong> olarak kaydedilmiştir. "
                    f"Şirketin sektör genelindeki toplam kâr büyüklüğü sıralaması ise <strong>{ranks_map.get(comp, 999)}.</strong> sıradadır."
                )
        
        result["summary_stats"] = summary_stats
        result["report_text"] = "".join(narratives) if narratives else "Rapor oluşturulacak yeterli veri bulunamadı."
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
