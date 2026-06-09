import pandas as pd
import numpy as np
import os
import traceback
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from ai_manager import get_kpi_analysis, design_semantic_charts

def analyze_dataset(dataset_paths, filters=None, focus_metric=None):
    if isinstance(dataset_paths, str):
        dataset_paths = [dataset_paths]
        
    dataframes = []
    
    try:
        for path in dataset_paths:
            ext = os.path.splitext(path)[1].lower()
            df_temp = None
            if ext == '.csv':
                df_temp = pd.read_csv(path, low_memory=False)
            elif ext in ['.xlsx', '.xlsm']:
                df_temp = pd.read_excel(path, engine='openpyxl')
            elif ext == '.xls':
                df_temp = pd.read_excel(path, engine='xlrd')
            elif ext == '.xlsb':
                df_temp = pd.read_excel(path, engine='pyxlsb')
            else:
                return {"error": f"Format '{ext}' not supported."}
            
            if df_temp is not None and not df_temp.empty:
                dataframes.append(df_temp)

        if not dataframes:
            return {"error": "The uploaded files are empty or unreadable."}

        # Auto-Join Logic
        df = dataframes[0]
        for i in range(1, len(dataframes)):
            next_df = dataframes[i]
            # Find common columns
            common_cols = list(set(df.columns).intersection(set(next_df.columns)))
            if not common_cols:
                return {"error": f"Cannot join datasets. No common columns found between files."}
            
            try:
                # Merge on all common columns
                df = pd.merge(df, next_df, on=common_cols, how='inner')
            except Exception as e:
                return {"error": f"Failed to join datasets on {common_cols}: {str(e)}"}
                
        if df.empty:
            return {"error": "The merged dataset is empty. The joined files have no matching records."}

        # 2. Cleanup & Processing
        df = df.dropna(axis=1, how='all').head(10000) 
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        df[numeric_cols] = df[numeric_cols].fillna(0)

        # 2b. Apply Drill-Down Filters (if any)
        active_filters = {}
        if filters and isinstance(filters, dict):
            for col, val in filters.items():
                if col in df.columns and val:
                    df = df[df[col].astype(str) == str(val)]
                    active_filters[col] = val
            if df.empty:
                return {"error": f"No data found for the selected filter(s): {active_filters}"}

        # 3. Semantic Feature Mapping
        datetime_cols = []
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                datetime_cols.append(col)
                continue
            if df[col].dtype == 'object':
                sample = df[col].dropna().head(10)
                if len(sample) > 0:
                    try:
                        converted = pd.to_datetime(sample, errors='coerce')
                        if converted.notna().sum() > len(sample) * 0.7:
                            datetime_cols.append(col)
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                    except: pass

        categorical_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
        categorical_cols = [c for c in categorical_cols if c not in datetime_cols]
        all_cats = list(dict.fromkeys(categorical_cols))

        # Filter categories for high-signal textual data (skip JSON-like blobs)
        sig_cats = []
        for c in all_cats:
             sample = df[c].dropna().head(20).astype(str)
             if any(x in "".join(sample) for x in ['{', '[', '}', ']']): continue
             sig_cats.append(c)

        # Build filter options for the frontend (limit to top 6 columns with <=50 unique values)
        filter_options = {}
        searchable_columns = [] # For high-cardinality items (SKU, Product ID, etc.)
        
        item_keywords = ['item', 'sku', 'product', 'name', 'desc', 'id', 'article', 'code']

        for c in sig_cats:
            uniques = df[c].dropna().unique().tolist()
            count = len(uniques)
            if 2 <= count <= 50:
                # Only show in basic dropdown if within limits and not explicitly an ID-type field
                if len(filter_options) < 6:
                    filter_options[c] = sorted([str(v) for v in uniques])
            
            # High Cardinality logic for the advanced Search field
            if count > 1:
                col_lower = str(c).lower()
                if any(k in col_lower for k in item_keywords):
                    searchable_columns.append({"name": c, "count": count})

        # Pick top high-cardinality match as primary search context
        searchable_columns = sorted(searchable_columns, key=lambda x: x['count'], reverse=True)

        # FALLBACK: If no keywords match but we have category columns with significant unique counts, pick the biggest one so search bar is active
        if not searchable_columns and sig_cats:
            fallback_col = None
            max_count = 0
            for c in sig_cats:
                cnt = len(df[c].dropna().unique())
                if cnt > max_count and cnt > 1:
                    max_count = cnt
                    fallback_col = c
            if fallback_col:
                 searchable_columns.append({"name": fallback_col, "count": max_count})

        # Filter out coordinates, months, years, or obvious date numbers from KPIs
        exclude_keys = ['id', 'zip', 'code', 'index', 'month', 'year', 'day', 'latitude', 'longitude', 'lat', 'lon', 'coord', 'date', 'time', 'hour', 'minute', 'sec', 'storage', 'ram', 'capacity', 'size', 'weight', 'height', 'width', 'version', 'model_num', 'rating', 'score', 'ml_month_num']
        
        finance_keys = ['revenue', 'sales', 'price', 'profit', 'cost', 'spend', 'amount', 'total', 'demand', 'visitors', 'returns', 'count', 'volume', 'quantity', 'rate']
        metric_cols = [c for c in numeric_cols if any(k in str(c).lower() for k in finance_keys) and not any(x in str(c).lower() for x in exclude_keys)]
        
        # If we still have few metrics, just take all numeric cols that aren't obvious IDs or dates
        other_metrics = [c for c in numeric_cols if c not in metric_cols and not any(x in str(c).lower() for x in exclude_keys)]
        metric_cols.extend(other_metrics)
        metric_cols = list(dict.fromkeys(metric_cols)) # Deduplicate

        # Dynamic dashboard-wide focus pivot
        if focus_metric and focus_metric in metric_cols:
            metric_cols.remove(focus_metric)
            metric_cols.insert(0, focus_metric)

        # 4. Semantic Engine Core (SUPER-INTELLIGENCE OVERHAUL)
        kpis = []
        charts = []
        insights = []
        
        # --- NEW: Automated Ratio Engineering ---
        # If we have Returns and Sales, create a Return Rate
        if any(x in str(metric_cols).lower() for x in ['return']) and any(x in str(metric_cols).lower() for x in ['sale', 'revenue']):
            r_col = next((c for c in metric_cols if 'return' in str(c).lower()), None)
            s_col = next((c for c in metric_cols if 'sale' in str(c).lower() or 'revenue' in str(c).lower()), None)
            if r_col and s_col and df[s_col].sum() > 0:
                df['Strategic_Return_Rate'] = (df[r_col] / df[s_col]) * 100
                metric_cols.insert(0, 'Strategic_Return_Rate')
                insights.append("Ratio Engineering: Automatically synthesized 'Strategic Return Rate' for efficiency audit.")

        # --- TOP KPI SUMMARY (AI ENHANCED) ---
        candidate_metrics = []
        for m in metric_cols:
            val = float(df[m].sum())
            candidate_metrics.append({"name": str(m), "value": val})
            
        # Build schema metadata for the Mega-Prompt
        columns_metadata = []
        for col in df.columns:
            col_type = "numeric"
            unique_sample = []
            if col in datetime_cols:
                col_type = "datetime"
            elif col in categorical_cols:
                col_type = "categorical"
                unique_sample = df[col].astype(str).dropna().unique()[:5].tolist()
            columns_metadata.append({"name": col, "type": col_type, "sample_values": unique_sample})

        from ai_manager import generate_master_intelligence
        master_data = generate_master_intelligence(candidate_metrics[:25], columns_metadata, df.head(10).fillna("").to_dict(orient='records'))
        
        ai_kpis = master_data.get("kpis", [])
        ai_designed_charts = master_data.get("charts", [])
        action_plans = master_data.get("actions", [])
        
        if ai_kpis:
            for item in ai_kpis:
                orig_name = item.get('original_name')
                matched_col = next((m for m in metric_cols if str(m) == orig_name), None)
                if not matched_col: continue
                val = df[matched_col].sum()
                impact_label = item.get('impact_label', matched_col)
                is_pct = 'rate' in str(matched_col).lower() or 'Strategic' in str(matched_col)
                is_currency = any(x in str(matched_col).lower() for x in ['revenue', 'sales', 'profit', 'cost', 'price', 'amount', 'spend'])
                prefix = "$" if is_currency else ""
                suffix = "%" if is_pct else ""
                
                if val >= 1e12: fmt = f"{prefix}{val/1e12:.2f}T{suffix}"
                elif val >= 1e9: fmt = f"{prefix}{val/1e9:.2f}B{suffix}"
                elif val >= 1e6: fmt = f"{prefix}{val/1e6:.1f}M{suffix}"
                elif val >= 1e3: fmt = f"{prefix}{val/1e3:.1f}k{suffix}"
                else: fmt = f"{prefix}{val:,.1f}{suffix}"
                kpis.append({"label": impact_label, "value": fmt, "is_ai": True, "insight": item.get('insight', '')})
        else:
            for m in metric_cols[:4]:
                val = df[m].sum()
                name = str(m).replace('_', ' ').title()
                is_currency = any(x in name.lower() for x in ['revenue', 'sales', 'profit', 'cost', 'price', 'amount', 'spend'])
                prefix = "$" if is_currency else ""
                if val >= 1e12: fmt = f"{prefix}{val/1e12:.2f}T"
                elif val >= 1e9: fmt = f"{prefix}{val/1e9:.2f}B"
                elif val >= 1e6: fmt = f"{prefix}{val/1e6:.1f}M"
                elif val >= 1e3: fmt = f"{prefix}{val/1e3:.1f}k"
                else: fmt = f"{prefix}{val:,.1f}"
                kpis.append({"label": name, "value": fmt})

        # --- REVOLUTIONARY CHART GENERATION (ADVANCED ANALYST MODE) ---
        max_charts = 60
        
        # 1. SEGMENTED TIME SERIES (Trends by Category)
        if datetime_cols and metric_cols and sig_cats:
            d_col, m_col, c_col = datetime_cols[0], metric_cols[0], sig_cats[0]
            top_cats = df[c_col].value_counts().head(3).index.tolist()
            if len(top_cats) >= 2:
                charts.append({
                    "type": "line", "style": "spline",
                    "title": f"Segmented Trajectory: {m_col} by {c_col}",
                    "labels": [], # Will be filled below
                    "datasets": []
                })
                # Aggregate for these top cats
                agg_all = []
                labels_set = False
                for cat_val in top_cats:
                    sub = df[df[c_col] == cat_val].set_index(d_col).resample('W')[m_col].sum().reset_index()
                    if not labels_set:
                        charts[-1]["labels"] = [str(x.strftime('%b %d')) for x in sub[d_col]]
                        labels_set = True
                    charts[-1]["datasets"].append({
                        "label": f"{cat_val}",
                        "data": [round(float(v), 2) for v in sub[m_col]]
                    })

        # 2. TIME SERIES DISCOVERY (Adaptive Frequency)
        if datetime_cols and metric_cols:
            d_col = datetime_cols[0]
            m_col = metric_cols[0]
            for freq, freq_label in [('ME', 'Monthly'), ('W', 'Weekly'), ('D', 'Daily')]:
                agg = df.set_index(d_col).resample(freq)[m_col].sum().reset_index()
                if len(agg) >= 3:
                    charts.append({
                        "type": "line", "style": "area",
                        "title": f"{freq_label} Momentum: {m_col}",
                        "labels": [str(x.strftime('%b %d' if freq != 'ME' else '%b %y')) for x in agg[d_col]],
                        "datasets": [{"label": f"{m_col} Index", "data": [round(float(v), 2) for v in agg[m_col]]}]
                    })
                    
                    # --- NEW: MACHINE LEARNING FORECAST ---
                    if len(agg) >= 5:
                        try:
                            # Train Forecast Model
                            ts_data = agg[m_col].astype(float).values
                            model = ExponentialSmoothing(ts_data, trend='add', seasonal=None, initialization_method="estimated")
                            fit_model = model.fit()
                            
                            # Predict next 3 periods
                            forecast_periods = 3
                            forecast = fit_model.forecast(forecast_periods)
                            
                            # Generate future labels
                            last_date = agg[d_col].iloc[-1]
                            if freq == 'ME':
                                future_dates = [last_date + pd.DateOffset(months=i) for i in range(1, forecast_periods + 1)]
                                label_fmt = '%b %y'
                            elif freq == 'W':
                                future_dates = [last_date + pd.Timedelta(weeks=i) for i in range(1, forecast_periods + 1)]
                                label_fmt = '%b %d'
                            else:
                                future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, forecast_periods + 1)]
                                label_fmt = '%b %d'
                                
                            future_labels = [f"Fwd {x.strftime(label_fmt)}" for x in future_dates]
                            all_labels = [str(x.strftime(label_fmt)) for x in agg[d_col]] + future_labels
                            
                            # Data arrays
                            historical_data = [round(float(v), 2) for v in agg[m_col]] + [None] * forecast_periods
                            forecast_data = [None] * (len(agg) - 1) + [round(float(agg[m_col].iloc[-1]), 2)] + [round(float(v), 2) for v in forecast]
                            
                            charts.append({
                                "type": "line", "style": "spline",
                                "title": f"Predictive AI Forecast: {m_col} ({freq_label})",
                                "labels": all_labels,
                                "datasets": [
                                    {"label": "Historical", "data": historical_data},
                                    {"label": "AI Forecast", "data": forecast_data} # We style it in frontend
                                ]
                            })
                            insights.append(f"Predictive Analytics: Generated {forecast_periods}-period AI forecast for {m_col} using Holt-Winters Exponential Smoothing.")
                        except Exception as e:
                            print(f"FORECAST ERROR: {e}")
                    break

        # 3. CONCENTRATION RISK AUDIT (Pareto Logic)
        for cat in sig_cats[:3]:
            for m in metric_cols[:2]:
                agg = df.groupby(cat)[m].sum().reset_index().sort_values(by=m, ascending=False)
                if len(agg) < 3: continue
                total = agg[m].sum()
                agg['pct'] = (agg[m] / total) * 100
                top_3_pct = agg['pct'].head(3).sum()
                if top_3_pct > 70:
                    insights.append(f"Concentration Risk: Top 3 segments in '{cat}' control {top_3_pct:.1f}% of {m}.")
                
                charts.append({
                    "type": "doughnut", "style": "standard",
                    "title": f"Concentration Audit: {m} Distribution ({cat})",
                    "labels": [str(v)[:15] for v in agg[cat].head(6)],
                    "datasets": [{"label": "Contribution %", "data": [round(float(v), 1) for v in agg['pct'].head(6)]}]
                })

        # 4. CROSS-METRIC CORRELATIONS (Strategic Pairings)
        if len(metric_cols) >= 2 and len(df) >= 2:
            for i in range(min(len(metric_cols)-1, 4)):
                m1, m2 = metric_cols[i], metric_cols[i+1]
                sample_df = df.head(20)
                if len(sample_df) < 2: continue
                charts.append({
                    "type": "line", "style": "spline",
                    "title": f"Correlation Dynamics: {m1} vs {m2}",
                    "labels": [f"Seg {k+1}" for k in range(len(sample_df))],
                    "datasets": [
                        {"label": str(m1), "data": [round(float(v), 2) for v in sample_df[m1]]},
                        {"label": str(m2), "data": [round(float(v), 2) for v in sample_df[m2]], "yAxisID": "y1"}
                    ]
                })

        anomalies = []
        # Identify a descriptive column for individual record labeling
        label_col = next((c for c in sig_cats if any(x in str(c).lower() for x in ['name', 'title', 'product', 'item', 'desc', 'label'])), None)
        if not label_col and sig_cats: label_col = sig_cats[0]

        # 5. DATA DISTRIBUTION AUDIT (Volatility Check)
        for m in metric_cols[:3]: # Focus on key 3 metrics for distribution
            if len(df) < 4 or df[m].nunique() < 2: continue
            try:
                # Basic Outlier Detection (Heuristic)
                q1 = df[m].quantile(0.25)
                q3 = df[m].quantile(0.75)
                iqr = q3 - q1
                outliers = df[(df[m] < (q1 - 1.5 * iqr)) | (df[m] > (q3 + 1.5 * iqr))]
                if len(outliers) > 0:
                    insights.append(f"Anomalies Detected: Found {len(outliers)} significant outliers in {m} (Statistical variance check).")
                    
                    extreme_outliers = outliers.copy()
                    extreme_outliers['abs_dev'] = abs(extreme_outliers[m] - df[m].median())
                    top_outliers = extreme_outliers.nlargest(3, 'abs_dev')
                    
                    for _, row in top_outliers.iterrows():
                        # Build a rich, unique label combining available identifiers to avoid duplicate summaries
                        label_parts = []
                        key_cats = [c for c in sig_cats if not any(x in str(c).lower() for x in ['date', 'time', 'year', 'month'])]
                        for col in key_cats[:3]:
                            if col in row and pd.notna(row[col]) and str(row[col]).strip():
                                label_parts.append(f"{col.replace('_', ' ').title()}: {row[col]}")
                        
                        if datetime_cols:
                            d_col = datetime_cols[0]
                            if d_col in row and pd.notna(row[d_col]):
                                val_str = str(row[d_col])
                                try:
                                    val_str = pd.to_datetime(row[d_col]).strftime('%d-%m-%Y')
                                except: pass
                                label_parts.append(f"Date: {val_str}")
                        
                        if not label_parts:
                            lbl = row[label_col] if (label_col and label_col in row) else f"Record {row.name}"
                        else:
                            lbl = " | ".join(label_parts)

                        dev_direction = "exceeds normal distribution" if row[m] > q3 else "falls below normal baseline"
                        clean_m = str(m).replace('_', ' ').title()
                        anomalies.append({
                            "metric": clean_m,
                            "value": round(float(row[m]), 2),
                            "label": str(lbl),
                            "type": "High Spike" if row[m] > q3 else "Deep Drop",
                            "reason": f"Flagged as statistical outlier that {dev_direction} in {clean_m}."
                        })

                bins = pd.cut(df[m], bins=8).value_counts().sort_index()
                charts.append({
                    "type": "bar", "style": "vertical",
                    "title": f"Data Distribution Audit: {m} (Volatility Check)",
                    "labels": [str(b) for b in bins.index],
                    "datasets": [{"label": "Record Density", "data": [int(v) for v in bins.values]}]
                })
            except: pass

        # 6. ELITE LEADERBOARD (Top Record Audit)
        for m in metric_cols[:2]: # Focus on top 2 metrics to avoid clutter
            if len(df) > 0: # Ensure at least one chart renders even on single-row drill-downs
                top_n = df.nlargest(12, m)
                labels = [str(v)[:20] for v in top_n[label_col]] if label_col else [f"Record {idx}" for idx in top_n.index]
                charts.append({
                    "type": "bar", "style": "horizontal",
                    "title": f"Elite Leaderboard: Top Performers ({m})",
                    "labels": labels,
                    "datasets": [{"label": str(m), "data": [round(float(v), 2) for v in top_n[m]]}]
                })

        # --- 1. NEW CHART: Seasonal Demand Profile ---
        if datetime_cols and metric_cols:
            d_col = datetime_cols[0]
            m_col = metric_cols[0]
            try:
                # Calculate mean of target grouped by month
                df['ml_month_num'] = df[d_col].dt.month
                month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
                monthly_avg = df.groupby('ml_month_num')[m_col].mean().reset_index()
                
                if len(monthly_avg) >= 2:
                    monthly_avg['month_lbl'] = monthly_avg['ml_month_num'].map(month_names)
                    monthly_avg = monthly_avg.sort_values(by='ml_month_num')
                    charts.append({
                        "type": "bar", "style": "vertical",
                        "title": f"Seasonal Demand Profile: Average {m_col} by Month",
                        "labels": monthly_avg['month_lbl'].tolist(),
                        "datasets": [{"label": f"Average {m_col}", "data": [round(float(v), 2) for v in monthly_avg[m_col]]}]
                    })
            except Exception as e:
                print(f"Seasonality calculation skipped: {e}")

        # --- 2. NEW CHART: 80/20 Pareto Cumulative Share ---
        if sig_cats and metric_cols:
            cat = sig_cats[0]
            m_col = metric_cols[0]
            try:
                agg = df.groupby(cat)[m_col].sum().reset_index().sort_values(by=m_col, ascending=False)
                if len(agg) >= 3:
                    total = agg[m_col].sum()
                    agg['pct'] = (agg[m_col] / total) * 100
                    agg['cum_pct'] = agg['pct'].cumsum()
                    
                    top_n = agg.head(10)
                    charts.append({
                        "type": "bar", "style": "stacked", # Dynamic composite on front-end
                        "title": f"80/20 Pareto Operations Share: {m_col} by {cat}",
                        "labels": [str(v)[:15] for v in top_n[cat]],
                        "datasets": [
                            {"label": "Contribution % (Bar)", "data": [round(float(v), 1) for v in top_n['pct']]},
                            {"label": "Cumulative Share % (Line)", "data": [round(float(v), 1) for v in top_n['cum_pct']], "type": "line", "tension": 0.3}
                        ]
                    })
            except Exception as e:
                print(f"Pareto analysis skipped: {e}")

        # --- 3. NEW CHART: Month-over-Month Growth Rates ---
        if datetime_cols and metric_cols:
            d_col = datetime_cols[0]
            m_col = metric_cols[0]
            try:
                monthly_agg = df.set_index(d_col).resample('ME')[m_col].sum().reset_index()
                if len(monthly_agg) >= 2:
                    monthly_agg['pct_change'] = monthly_agg[m_col].pct_change() * 100
                    monthly_agg = monthly_agg.dropna(subset=['pct_change'])
                    charts.append({
                        "type": "bar", "style": "vertical",
                        "title": f"Month-over-Month Growth Rates (%): {m_col}",
                        "labels": [str(x.strftime('%b %y')) for x in monthly_agg[d_col]],
                        "datasets": [{"label": "Growth Rate %", "data": [round(float(v), 1) for v in monthly_agg['pct_change']]}]
                    })
            except Exception as e:
                print(f"MoM Growth skipped: {e}")

        # === NEW: AI-Driven Semantic Chart Architect (from Mega-Prompt) ===
        try:
            ai_charts = []
            if ai_designed_charts:
                for chart_spec in ai_designed_charts:
                    try:
                        x_col = chart_spec.get('x_column')
                        y_col = chart_spec.get('y_column')
                        title = chart_spec.get('title', 'AI Ingestion Insights')
                        ctype = chart_spec.get('type', 'bar')
                        agg_method = chart_spec.get('aggregation', 'sum')

                        if not x_col or x_col not in df.columns: continue
                        if not y_col or y_col not in df.columns: continue

                        # Convert target column to numeric for aggregation, unless we are just counting occurrences
                        df_agg_temp = df.copy()
                        if agg_method in ['sum', 'mean'] or ctype in ['scatter', 'boxplot']:
                            # Only coerce to numeric if they are different columns, to avoid destroying x_col if x_col == y_col
                            if x_col != y_col:
                                df_agg_temp[y_col] = pd.to_numeric(df_agg_temp[y_col], errors='coerce').fillna(0)
                            else:
                                df_agg_temp['__temp_y'] = pd.to_numeric(df_agg_temp[y_col], errors='coerce').fillna(0)
                                y_col = '__temp_y'

                        if ctype == 'matrix':
                            # Heatmap Support
                            z_col = chart_spec.get('z_column')
                            if not z_col or z_col not in df.columns: continue
                            df_agg_temp[z_col] = pd.to_numeric(df_agg_temp[z_col], errors='coerce').fillna(0)
                            
                            # Group by X and Y
                            matrix_grouped = df_agg_temp.groupby([x_col, y_col])[z_col].sum().reset_index()
                            
                            # Limit to top 10 x 10 to avoid browser crash
                            top_x = matrix_grouped.groupby(x_col)[z_col].sum().nlargest(10).index
                            top_y = matrix_grouped.groupby(y_col)[z_col].sum().nlargest(10).index
                            matrix_filtered = matrix_grouped[matrix_grouped[x_col].isin(top_x) & matrix_grouped[y_col].isin(top_y)]
                            
                            matrix_data = []
                            for _, row in matrix_filtered.iterrows():
                                matrix_data.append({
                                    "x": str(row[x_col])[:15],
                                    "y": str(row[y_col])[:15],
                                    "v": float(row[z_col])
                                })
                            
                            if len(matrix_data) > 0:
                                ai_charts.append({
                                    "type": ctype,
                                    "style": "standard",
                                    "title": title,
                                    "labels": [],
                                    "datasets": [{"label": f"{z_col} by {x_col} & {y_col}", "data": matrix_data}],
                                    "strategic_description": "\n".join([f"• {x}" for x in chart_spec.get("strategic_description", [])])
                                })

                        elif ctype == 'grouped_bar':
                            group_col = chart_spec.get('group_column')
                            if not group_col or group_col not in df.columns: continue
                            
                            grp = df_agg_temp.groupby([x_col, group_col])[y_col].sum().reset_index()
                            # Pivot
                            pivot = grp.pivot(index=x_col, columns=group_col, values=y_col).fillna(0)
                            # Top 10 X labels
                            pivot['Total'] = pivot.sum(axis=1)
                            pivot = pivot.sort_values(by='Total', ascending=False).head(10).drop(columns=['Total'])
                            
                            labels = [str(x)[:15] for x in pivot.index]
                            datasets = []
                            # Limit to top 5 groups to avoid crowding
                            top_groups = pivot.sum().nlargest(5).index
                            for g in top_groups:
                                datasets.append({
                                    "label": str(g)[:15],
                                    "data": [round(float(v), 2) for v in pivot[g]]
                                })
                            
                            if len(labels) > 0 and len(datasets) > 0:
                                ai_charts.append({
                                    "type": "bar",
                                    "style": "grouped",
                                    "title": title,
                                    "labels": labels,
                                    "datasets": datasets,
                                    "strategic_description": "\n".join([f"• {x}" for x in chart_spec.get("strategic_description", [])])
                                })

                        elif ctype == 'dual_axis':
                            y1_col = chart_spec.get('y1_column')
                            y2_col = chart_spec.get('y2_column')
                            if not y1_col or y1_col not in df.columns: continue
                            if not y2_col or y2_col not in df.columns: continue
                            
                            df_agg_temp[y1_col] = pd.to_numeric(df_agg_temp[y1_col], errors='coerce').fillna(0)
                            df_agg_temp[y2_col] = pd.to_numeric(df_agg_temp[y2_col], errors='coerce').fillna(0)
                            
                            dual_grp = df_agg_temp.groupby(x_col)[[y1_col, y2_col]].sum().reset_index()
                            dual_grp = dual_grp.sort_values(by=y1_col, ascending=False).head(10)
                            
                            labels = [str(x)[:15] for x in dual_grp[x_col]]
                            
                            if len(labels) > 0:
                                ai_charts.append({
                                    "type": "bar", # Base type
                                    "style": "dual_axis",
                                    "title": title,
                                    "labels": labels,
                                    "datasets": [
                                        {"label": str(y1_col), "data": [round(float(v), 2) for v in dual_grp[y1_col]], "type": "bar", "yAxisID": "y"},
                                        {"label": str(y2_col), "data": [round(float(v), 2) for v in dual_grp[y2_col]], "type": "line", "yAxisID": "y1"}
                                    ],
                                    "strategic_description": "\n".join([f"• {x}" for x in chart_spec.get("strategic_description", [])])
                                })

                        elif ctype == 'scatter':
                            # For scatter plots, use raw data pairs instead of aggregated groups
                            scatter_data = []
                            # Limit to 100 points to prevent chart performance issues
                            for idx, row in df_agg_temp.dropna(subset=[x_col, y_col]).head(100).iterrows():
                                try:
                                    x_val = float(row[x_col])
                                    y_val = float(row[y_col])
                                    scatter_data.append({"x": x_val, "y": y_val})
                                except:
                                    pass
                            if len(scatter_data) > 0:
                                ai_charts.append({
                                    "type": ctype,
                                    "style": "standard",
                                    "title": title,
                                    "labels": [],
                                    "datasets": [{"label": str(y_col).replace('_', ' ').title(), "data": scatter_data}],
                                    "strategic_description": "\n".join([f"• {x}" for x in chart_spec.get("strategic_description", [])])
                                })
                        elif ctype == 'boxplot':
                            # Group by x_col and collect all y_col values as a list
                            boxplot_data = []
                            labels = []
                            grouped = df_agg_temp.groupby(x_col)[y_col].apply(list).reset_index()
                            for _, row in grouped.head(10).iterrows():
                                labels.append(str(row[x_col])[:15])
                                boxplot_data.append([float(v) for v in row[y_col] if pd.notna(v)])
                            if len(labels) > 0:
                                ai_charts.append({
                                    "type": ctype,
                                    "style": "standard",
                                    "title": title,
                                    "labels": labels,
                                    "datasets": [{"label": str(y_col).replace('_', ' ').title(), "data": boxplot_data}],
                                    "strategic_description": "\n".join([f"• {x}" for x in chart_spec.get("strategic_description", [])])
                                })
                        else:
                            if x_col == y_col and agg_method == 'count':
                                grouped = df_agg_temp[x_col].value_counts().reset_index()
                                grouped.columns = [x_col, y_col]
                            else:
                                if agg_method == 'mean':
                                    grouped = df_agg_temp.groupby(x_col)[y_col].mean().reset_index()
                                elif agg_method == 'count':
                                    grouped = df_agg_temp.groupby(x_col)[y_col].count().reset_index()
                                else:
                                    grouped = df_agg_temp.groupby(x_col)[y_col].sum().reset_index()

                            grouped = grouped.sort_values(by=y_col, ascending=False).head(10)

                            if pd.api.types.is_datetime64_any_dtype(df_agg_temp[x_col]):
                                labels = [str(x.strftime('%b %d' if len(grouped) > 5 else '%b %y')) for x in grouped[x_col]]
                            else:
                                labels = [str(v)[:15] for v in grouped[x_col]]

                            data_vals = [round(float(v), 2) for v in grouped[y_col]]

                            if len(labels) > 0:
                                ai_charts.append({
                                    "type": ctype,
                                    "style": "spline" if ctype == 'line' else "vertical",
                                    "title": title,
                                    "labels": labels,
                                    "datasets": [{"label": str(y_col).replace('_', ' ').title(), "data": data_vals}],
                                    "strategic_description": "\n".join([f"• {x}" for x in chart_spec.get("strategic_description", [])])
                                })
                    except Exception as inner_e:
                        print(f"FAILED TO EXECUTE AI CHART SPEC '{chart_spec}': {inner_e}")

            if len(ai_charts) >= 3:
                # MANDATORY: Preserve the predictive time series forecast at index 0 for ML consistency
                forecast_chart = next((c for c in charts if "Predictive" in c['title']), None)
                if forecast_chart and forecast_chart not in ai_charts:
                    ai_charts.insert(0, forecast_chart)
                
                # Combine standard advanced visual layout with AI tailored visual layout for MAXIMUM charts
                for ai_c in ai_charts:
                    if ai_c not in charts:
                        charts.append(ai_c)
                print(f"AutoML successfully combined {len(ai_charts)} custom AI-designed charts with base analytics!")
        except Exception as outer_e:
            print(f"AI Chart generation failed, reverting to standard analytical suite: {outer_e}")

        insights.append(f"Strategic Intelligence synthesized {len(charts)} executive visualizations.")
        # --- NEW: Dynamic Category Performance Scorecard Matrix ---
        category_scorecard = []
        if sig_cats and metric_cols:
            cat_col = sig_cats[0]
            met_col = metric_cols[0]
            try:
                # Calculate total sales for share proportion
                total_sales = float(df[met_col].sum())
                
                # Dynamic Grouping
                grp = df.groupby(cat_col).agg({
                    met_col: ['sum', 'count', 'mean']
                }).reset_index()
                grp.columns = [cat_col, 'sales_sum', 'volume_count', 'sales_mean']
                
                # Rank top 15 categories for visual card matrix
                grp = grp.sort_values(by='sales_sum', ascending=False).head(15)
                
                for _, row in grp.iterrows():
                    sales = float(row['sales_sum'])
                    volume = int(row['volume_count'])
                    avg_price = float(row['sales_mean'])
                    share = (sales / total_sales * 100) if total_sales > 0 else 0
                    
                    # Outlined corporate health categorization
                    if share > 25:
                        status = "High-Volume Engine"
                        review = f"Core B2B revenue pipeline contributing {share:.1f}% share. Secure logistical buffers."
                    elif avg_price > df[met_col].median() * 1.4:
                        status = "Margin Anchor"
                        review = f"Premium segment driver (Avg: ${avg_price:,.1f}). Invest in premium SLA loyalty perks."
                    elif share < 4:
                        status = "Efficiency Alert"
                        review = f"Underperforming tail segment ({share:.1f}% share). Review channel profitability metrics."
                    else:
                        status = "Performance Core"
                        review = f"Stable operational performer with {volume} records. Maintain baseline marketing indexes."
                        
                    category_scorecard.append({
                        "category": str(row[cat_col]),
                        "sales": round(sales, 2),
                        "volume": volume,
                        "avg_price": round(avg_price, 2),
                        "share": round(share, 1),
                        "status": status,
                        "review": review
                    })
            except Exception as grp_e:
                print(f"B2B Category grouping metrics skipped: {grp_e}")

        # --- Strategic Action Cards from Gemini (Mega-Prompt) ---
        # Already extracted `action_plans` at the top!

        # Ensure all charts have a strategic description (either from AI or dynamic fallback)
        from ai_manager import _generate_dynamic_fallback
        for c in charts:
            if not c.get('strategic_description'):
                c['strategic_description'] = _generate_dynamic_fallback(c)

        return {
            "kpis": kpis, "charts": charts, "insights": insights, "anomalies": anomalies,
            "metadata": {
                "rows": len(df), 
                "columns": len(df.columns), 
                "filename": ", ".join([os.path.basename(p) for p in dataset_paths]),
                "metric_cols": metric_cols # Pass detected metrics to populate dynamic frontend dropdown selectors
            },
            "raw_data": df.head(500).fillna("").to_dict(orient='records'),
            "themes": ["Executive Intelligence Briefing", "Strategic Action Planner", "Category Diagnostics Scorecard"],
            "filter_options": filter_options,
            "searchable_columns": searchable_columns,
            "active_filters": active_filters,
            "category_scorecard": category_scorecard,
            "action_plans": action_plans
        }

    except Exception as e:
        print(f"ANALYZE ERROR: {traceback.format_exc()}")
        return {"error": f"Semantic Analysis Failure: {str(e)}"}
