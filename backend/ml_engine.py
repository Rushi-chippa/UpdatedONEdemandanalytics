import pandas as pd
import numpy as np
import os
import pickle
import traceback
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder

def train_predictive_model(filepath, target_col, feature_cols, filters=None):
    """
    Trains a robust RandomForestRegressor on any dataset.
    Automatically handles numerical imputation, categorical encoding, and date parsing.
    Saves the entire trained pipeline to a pickle file for dynamic real-time predictions.
    """
    try:
        # 1. Load Dataset
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.csv':
            df = pd.read_csv(filepath, low_memory=False)
        elif ext in ['.xlsx', '.xlsm']:
            df = pd.read_excel(filepath, engine='openpyxl')
        elif ext == '.xls':
            df = pd.read_excel(filepath, engine='xlrd')
        else:
            return {"error": f"Dataset format '{ext}' is not supported."}

        if df is None or df.empty:
            return {"error": "Dataset is empty or unreadable."}

        # 2. Apply Active Filters (Ensures model is trained on current visual scope)
        if filters and isinstance(filters, dict):
            for col, val in filters.items():
                if col in df.columns and val:
                    df = df[df[col].astype(str) == str(val)]
            if df.empty:
                return {"error": "The active filters left no records for training."}

        # 3. Clean Target & Features list
        if target_col not in df.columns:
            return {"error": f"Target column '{target_col}' not found."}
        
        # Ensure target is numeric
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
        df = df.dropna(subset=[target_col])
        if len(df) < 5:
            return {"error": "Not enough data points after cleaning target (minimum 5 required)."}

        # Filter out features that do not exist or match the target
        valid_features = [f for f in feature_cols if f in df.columns and f != target_col]
        if not valid_features:
            return {"error": "No valid predictive features selected."}

        # Keep a snapshot of original column categories before processing for slider layouts
        features_info = []
        df_ml = df[[target_col] + valid_features].copy()

        # 4. Feature Engineering & Preprocessing
        numerical_imputers = {}
        categorical_encoders = {}
        date_features = []
        final_numeric_cols = []
        final_categorical_cols = []

        for col in valid_features:
            col_type = "numeric"
            
            # Check if Date column
            if pd.api.types.is_datetime64_any_dtype(df_ml[col]):
                col_type = "date"
            else:
                # Try parsing string date
                if df_ml[col].dtype == 'object':
                    sample = df_ml[col].dropna().head(10).astype(str)
                    if len(sample) > 0:
                        try:
                            converted = pd.to_datetime(sample, errors='coerce')
                            if converted.notna().sum() > len(sample) * 0.7:
                                df_ml[col] = pd.to_datetime(df_ml[col], errors='coerce')
                                col_type = "date"
                        except: pass

            if col_type == "date":
                # Convert date to features
                df_ml[col] = pd.to_datetime(df_ml[col], errors='coerce')
                # Fill missing dates with mode or today
                mode_date = df_ml[col].mode().iloc[0] if not df_ml[col].mode().empty else pd.Timestamp.now()
                df_ml[col] = df_ml[col].fillna(mode_date)
                
                # Extract components
                df_ml[f"{col}_year"] = df_ml[col].dt.year
                df_ml[f"{col}_month"] = df_ml[col].dt.month
                df_ml[f"{col}_day"] = df_ml[col].dt.day
                df_ml[f"{col}_dayofweek"] = df_ml[col].dt.dayofweek
                
                # Register new numeric features
                date_features.append(col)
                final_numeric_cols.extend([f"{col}_year", f"{col}_month", f"{col}_day", f"{col}_dayofweek"])
                
                features_info.append({
                    "name": col,
                    "type": "date",
                    "min": int(df_ml[f"{col}_year"].min()),
                    "max": int(df_ml[f"{col}_year"].max()),
                    "default_year": int(mode_date.year),
                    "default_month": int(mode_date.month),
                    "default_day": int(mode_date.day)
                })

            elif pd.api.types.is_numeric_dtype(df_ml[col]):
                # Numerical Column - Impute missing values with Median
                median_val = float(df_ml[col].median()) if not df_ml[col].isna().all() else 0.0
                df_ml[col] = df_ml[col].fillna(median_val)
                numerical_imputers[col] = median_val
                final_numeric_cols.append(col)
                
                features_info.append({
                    "name": col,
                    "type": "numeric",
                    "min": float(df_ml[col].min()),
                    "max": float(df_ml[col].max()),
                    "mean": float(df_ml[col].mean())
                })

            else:
                # Categorical Column - Impute missing values with constant, then Label Encode
                df_ml[col] = df_ml[col].astype(str).fillna("missing")
                le = LabelEncoder()
                df_ml[col] = le.fit_transform(df_ml[col])
                categorical_encoders[col] = le
                final_categorical_cols.append(col)
                
                features_info.append({
                    "name": col,
                    "type": "categorical",
                    "categories": [str(c) for c in le.classes_],
                    "default": str(le.classes_[0]) if len(le.classes_) > 0 else "missing"
                })

        # 5. Build Final Training Vectors
        ml_features = final_numeric_cols + final_categorical_cols
        X = df_ml[ml_features]
        y = df_ml[target_col]

        # 6. Train-Validation Split
        if len(df_ml) >= 10:
            X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        else:
            # Overfit small datasets for safety
            X_train, X_val, y_train, y_val = X, X, y, y

        # 7. Train Random Forest Model
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        # 8. Compute Performance Metrics
        y_pred = model.predict(X_val)
        
        r2 = float(r2_score(y_val, y_pred))
        # Ensure R2 doesn't look weird (bound to [0, 1] for visual display, though handle negatives gracefully)
        r2_display = max(0.0, min(1.0, r2)) if not np.isnan(r2) else 0.0
        
        mae = float(mean_absolute_error(y_val, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))

        # 9. Extract McKinsey-Grade Feature Drivers
        importances = []
        raw_importances = model.feature_importances_
        
        # Aggregate date features back to their main date column for clean charts
        aggregated_imp = {}
        for feature_name, weight in zip(ml_features, raw_importances):
            main_col = feature_name
            # Check if this was a generated sub-date feature
            for date_col in date_features:
                if feature_name.startswith(f"{date_col}_"):
                    main_col = date_col
                    break
            aggregated_imp[main_col] = aggregated_imp.get(main_col, 0.0) + float(weight)

        for col, weight in aggregated_imp.items():
            importances.append({"name": col.replace('_', ' ').title(), "weight": round(weight * 100, 1)})
        importances = sorted(importances, key=lambda x: x['weight'], reverse=True)

        # 10. Generate Actuals vs. Predicted Alignment Coordinates (Limit to first 50 points)
        alignment = []
        plot_limit = min(50, len(y_val))
        for idx in range(plot_limit):
            alignment.append({
                "index": idx + 1,
                "actual": round(float(y_val.iloc[idx]), 2),
                "predicted": round(float(y_pred[idx]), 2)
            })

        # 11. Serialize Model Pipeline
        pipeline = {
            "model": model,
            "target_col": target_col,
            "feature_cols": valid_features,
            "final_numeric_cols": final_numeric_cols,
            "final_categorical_cols": final_categorical_cols,
            "numerical_imputers": numerical_imputers,
            "categorical_encoders": categorical_encoders,
            "date_features": date_features,
            "features_info": features_info,
            "historical_mean_target": float(y.mean())
        }
        
        model_filename = f"{os.path.basename(filepath)}_model.pkl"
        model_dir = os.path.dirname(filepath)
        model_path = os.path.join(model_dir, model_filename)
        
        with open(model_path, 'wb') as f:
            pickle.dump(pipeline, f)

        return {
            "success": True,
            "r2": round(r2_display * 100, 1),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "importances": importances,
            "alignment": alignment,
            "features_info": features_info,
            "historical_mean_target": round(float(y.mean()), 2),
            "model_path": model_filename
        }

    except Exception as e:
        print(f"ML ENGINE TRAINING ERROR: {traceback.format_exc()}")
        return {"error": f"Machine Learning Training Failed: {str(e)}"}


def run_prediction(model_dir, model_filename, user_inputs):
    """
    Loads a serialized ML pipeline and runs a live prediction using user slider inputs.
    """
    try:
        model_path = os.path.join(model_dir, model_filename)
        if not os.path.exists(model_path):
            return {"error": "Trained predictive model not found. Please retrain."}

        with open(model_path, 'rb') as f:
            pipeline = pickle.load(f)

        model = pipeline["model"]
        numerical_imputers = pipeline["numerical_imputers"]
        categorical_encoders = pipeline["categorical_encoders"]
        date_features = pipeline["date_features"]
        final_numeric_cols = pipeline["final_numeric_cols"]
        final_categorical_cols = pipeline["final_categorical_cols"]
        
        # Prepare inputs row
        row_dict = {}

        # 1. Preprocess inputs
        for col_name, raw_val in user_inputs.items():
            # Check if this is a Date Column
            if col_name in date_features:
                try:
                    dt = pd.to_datetime(raw_val, errors='coerce')
                    if pd.isna(dt):
                        dt = pd.Timestamp.now()
                except:
                    dt = pd.Timestamp.now()
                
                row_dict[f"{col_name}_year"] = dt.year
                row_dict[f"{col_name}_month"] = dt.month
                row_dict[f"{col_name}_day"] = dt.day
                row_dict[f"{col_name}_dayofweek"] = dt.dayofweek
            
            # Check if Numerical Feature
            elif col_name in numerical_imputers:
                try:
                    row_dict[col_name] = float(raw_val)
                except:
                    row_dict[col_name] = numerical_imputers[col_name]
                    
            # Check if Categorical Feature
            elif col_name in categorical_encoders:
                le = categorical_encoders[col_name]
                clean_str = str(raw_val).strip()
                if clean_str in le.classes_:
                    row_dict[col_name] = le.transform([clean_str])[0]
                else:
                    # Fallback to first class or index 0 if not found
                    row_dict[col_name] = 0

        # Fill any missing expected model features with defaults
        all_features = final_numeric_cols + final_categorical_cols
        final_row = []
        for feat in all_features:
            if feat in row_dict:
                final_row.append(row_dict[feat])
            else:
                # Fallback imputer
                if feat in numerical_imputers:
                    final_row.append(numerical_imputers[feat])
                else:
                    final_row.append(0)

        # 2. Reshape & Predict
        X_pred = np.array(final_row).reshape(1, -1)
        predicted_val = model.predict(X_pred)[0]

        return {"prediction": round(float(predicted_val), 2)}

    except Exception as e:
        print(f"ML ENGINE PREDICTION ERROR: {traceback.format_exc()}")
        return {"error": f"Prediction failed: {str(e)}"}
