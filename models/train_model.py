"""
AI Farmer Credit Intelligence Platform
Enterprise ML Training Module
Random Forest with Village Risk Indexing
"""

import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import warnings
warnings.filterwarnings('ignore')

class EnterpriseMLEngine:
    def __init__(self):
        self.model = None
        self.feature_columns = None
        self.village_risk_map = {}

    def _safe_div(self, numerator, denominator):
        if denominator in [0, None]:
            return 0.0
        return float(numerator) / float(denominator)

    def _farm_activity_score(self, level):
        level = str(level or '').lower()
        if level == 'high':
            return 0.95
        if level == 'medium':
            return 0.75
        if level == 'low':
            return 0.55
        return 0.7

    def _tx_consistency_score(self, value):
        text = str(value or '').lower()
        if text in ['regular', 'high', 'good']:
            return 0.9
        if text in ['irregular', 'low', 'poor']:
            return 0.45
        return 0.65
    
    def load_and_preprocess_data(self, file_path):
        """Load and preprocess farmer transaction data"""
        print("Loading enterprise farmer data...")
        data = pd.read_csv(file_path)

        # Support transformed farmer_credit_dataset.csv schema.
        if 'total_purchases' in data.columns:
            data['TotalPurchase'] = data['total_purchases']
            data['CreditTaken'] = data['credit_taken']
            data['PaymentDone'] = data['payments_made']
            data['DelayDays'] = data['payment_delay_days']
            data['OutstandingAmount'] = data['outstanding_balance']
            data['VillageCode'] = data['village_code']
            data['CropType'] = data.get('crop_type', 'Mixed')
            data['CropSeason'] = data.get('crop_season', 'Kharif')
            data['VillageRiskIndex'] = data.get('village_risk_index', 0.8)
            data['SeasonIncome'] = data.get('season_income', data['TotalPurchase'] * 1.15)
            data['FarmActivityLevel'] = data.get('farm_activity_level', 'medium')
            data['TransactionConsistencyLabel'] = data.get('transaction_consistency', 'regular')
            data['WeatherRiskIndex'] = data.get('weather_risk_index', 0.4)
            data['InputDependency'] = data.get('input_dependency', 0.5)

        # Backward compatibility for legacy CSV schema.
        if 'TotalPurchase' not in data.columns:
            data['TotalPurchase'] = data.get('total_purchase', 0.0)
        if 'CreditTaken' not in data.columns:
            data['CreditTaken'] = data.get('credit_taken', 0.0)
        if 'PaymentDone' not in data.columns:
            data['PaymentDone'] = data.get('payment_done', 0.0)
        if 'DelayDays' not in data.columns:
            data['DelayDays'] = data.get('delay_days', 0)
        if 'OutstandingAmount' not in data.columns:
            data['OutstandingAmount'] = data.get('outstanding_amount', 0.0)
        if 'VillageCode' not in data.columns:
            data['VillageCode'] = data.get('village_code', 'VILL001')
        if 'CropSeason' not in data.columns:
            data['CropSeason'] = data.get('crop_season', 'Kharif')
        if 'CropType' not in data.columns:
            data['CropType'] = data.get('crop_type', 'Mixed')
        if 'VillageRiskIndex' not in data.columns:
            data['VillageRiskIndex'] = data.get('village_risk_index', 0.8)
        if 'SeasonIncome' not in data.columns:
            data['SeasonIncome'] = data['TotalPurchase'].astype(float) * 1.15
        if 'FarmActivityLevel' not in data.columns:
            data['FarmActivityLevel'] = np.select(
                [data['TotalPurchase'] >= 150000, data['TotalPurchase'] >= 60000],
                ['high', 'medium'],
                default='low'
            )
        if 'TransactionConsistencyLabel' not in data.columns:
            data['TransactionConsistencyLabel'] = data.get('transaction_consistency', 'regular')
        if 'WeatherRiskIndex' not in data.columns:
            data['WeatherRiskIndex'] = 0.4
        if 'InputDependency' not in data.columns:
            data['InputDependency'] = (data['CreditTaken'] / data['TotalPurchase'].replace(0, np.nan)).fillna(0.0)

        # Normalize types
        data['TotalPurchase'] = pd.to_numeric(data['TotalPurchase'], errors='coerce').fillna(0.0)
        data['CreditTaken'] = pd.to_numeric(data['CreditTaken'], errors='coerce').fillna(0.0)
        data['PaymentDone'] = pd.to_numeric(data['PaymentDone'], errors='coerce').fillna(0.0)
        data['DelayDays'] = pd.to_numeric(data['DelayDays'], errors='coerce').fillna(0).astype(int)
        data['OutstandingAmount'] = pd.to_numeric(data['OutstandingAmount'], errors='coerce').fillna(0.0)
        data['VillageRiskIndex'] = pd.to_numeric(data['VillageRiskIndex'], errors='coerce').fillna(0.8).clip(0.0, 1.0)
        data['SeasonIncome'] = pd.to_numeric(data['SeasonIncome'], errors='coerce').fillna(0.0)
        data['WeatherRiskIndex'] = pd.to_numeric(data['WeatherRiskIndex'], errors='coerce').fillna(0.4).clip(0.0, 1.0)
        data['InputDependency'] = pd.to_numeric(data['InputDependency'], errors='coerce').fillna(0.5).clip(0.0, 1.5)
        data['CropSeason'] = data['CropSeason'].fillna('Kharif').astype(str)
        data['CropType'] = data['CropType'].fillna('Mixed').astype(str)
        data['FarmActivityLevel'] = data['FarmActivityLevel'].fillna('medium').astype(str)
        data['TransactionConsistencyLabel'] = data['TransactionConsistencyLabel'].fillna('regular').astype(str)

        # Build behavior features used by both rule-based and ML scoring.
        data['PaymentRatio'] = (data['PaymentDone'] / data['CreditTaken'].replace(0, np.nan)).fillna(0)
        data['UtilizationRatio'] = (data['CreditTaken'] / data['TotalPurchase'].replace(0, np.nan)).fillna(0)
        data['OutstandingRatio'] = (data['OutstandingAmount'] / data['CreditTaken'].replace(0, np.nan)).fillna(0)
        data['FarmActivityScore'] = data['FarmActivityLevel'].map(lambda v: self._farm_activity_score(v))
        data['TransactionConsistency'] = data['TransactionConsistencyLabel'].map(lambda v: self._tx_consistency_score(v))
        income_base = (data['CreditTaken'] * 1.4).replace(0, np.nan)
        data['SeasonIncomeStrength'] = (data['SeasonIncome'] / income_base).replace([np.inf, -np.inf], np.nan).fillna(0.7).clip(0.0, 1.2)

        crop_stability_map = {
            'paddy': 0.8,
            'maize': 0.76,
            'wheat': 0.79,
            'pulses': 0.72,
            'vegetables': 0.68,
            'cotton': 0.63,
            'sugarcane': 0.66,
            'mixed': 0.74
        }
        data['CropStabilityScore'] = data['CropType'].str.lower().map(crop_stability_map).fillna(0.7)

        # Build target from farmer behavior if explicit label not present.
        if 'LoanRepaid' not in data.columns:
            data['LoanRepaid'] = (
                (data['PaymentRatio'] >= 0.7)
                & (data['DelayDays'] <= 10)
                & (data['OutstandingRatio'] <= 0.4)
            ).astype(int)

        # Create risk buckets
        data['DelayCategory'] = pd.cut(
            data['DelayDays'],
            bins=[-1, 5, 15, 30, 100],
            labels=['Low', 'Medium', 'High', 'Critical']
        )

        # Village risk mapping
        village_risk = data.groupby('VillageCode')['LoanRepaid'].mean()
        self.village_risk_map = village_risk.to_dict()
        
        print(f"Loaded {len(data)} farmer records from {data['VillageCode'].nunique()} villages")
        print(f"Village Risk Index: {dict(village_risk)}")
        
        return data
    
    def prepare_features(self, data):
        """Prepare feature matrix for ML model"""
        
        # Select features for training
        feature_columns = [
            'TotalPurchase', 'CreditTaken', 'PaymentDone', 
            'DelayDays', 'OutstandingAmount', 'VillageRiskIndex',
            'PaymentRatio', 'UtilizationRatio', 'OutstandingRatio',
            'SeasonIncome', 'FarmActivityScore', 'TransactionConsistency',
            'WeatherRiskIndex', 'InputDependency',
            'CropStabilityScore', 'SeasonIncomeStrength'
        ]
        
        X = data[feature_columns].copy()
        
        # Add categorical features
        categorical_features = pd.get_dummies(data['CropSeason'], prefix='Season')
        crop_features = pd.get_dummies(data['CropType'], prefix='Crop')
        activity_features = pd.get_dummies(data['FarmActivityLevel'], prefix='FarmActivity')
        delay_categories = pd.get_dummies(data['DelayCategory'], prefix='Delay')
        
        # Combine all features
        X = pd.concat([X, categorical_features, crop_features, activity_features, delay_categories], axis=1)
        
        # Target variable
        y = data['LoanRepaid']
        
        self.feature_columns = X.columns.tolist()
        
        print(f"Prepared {len(self.feature_columns)} features for training")
        print(f"Features: {self.feature_columns}")
        
        return X, y
    
    def train_model(self, X, y):
        """Train Random Forest Model"""
        print("Training Enterprise Random Forest Model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Initialize model with optimized parameters
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )
        
        # Train model
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        # Predictions
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        print("=" * 50)
        print("MODEL PERFORMANCE REPORT")
        print("=" * 50)
        print(f"Training Accuracy: {train_score:.3f}")
        print(f"Testing Accuracy: {test_score:.3f}")
        print(f"ROC AUC Score: {roc_auc_score(y_test, y_prob):.3f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nTop 5 feature importance:")
        for idx, row in feature_importance.head().iterrows():
            print(f"- {row['feature']}: {row['importance']:.3f}")
        
        return self.model
    
    def save_model(self):
        """Save trained model and components"""
        joblib.dump(self.model, 'credit_model_enterprise.pkl')
        joblib.dump(self.feature_columns, 'model_columns_enterprise.pkl')
        joblib.dump(self.village_risk_map, 'village_risk_map.pkl')
        
        print("\nModel saved successfully!")
        print("- credit_model_enterprise.pkl")
        print("- model_columns_enterprise.pkl")
        print("- village_risk_map.pkl")

def main():
    """Main training pipeline"""
    print("AI FARMER CREDIT INTELLIGENCE PLATFORM")
    print("Enterprise ML Training Pipeline")
    print("=" * 60)
    
    # Initialize ML Engine
    ml_engine = EnterpriseMLEngine()
    
    # Load and preprocess data
    data_path = os.path.join('..', 'data', 'farmer_credit_dataset.csv')
    if not os.path.exists(data_path):
        data_path = os.path.join('..', 'data', 'farmer_transactions.csv')
    if not os.path.exists(data_path):
        data_path = 'data/farmer_credit_dataset.csv'
    if not os.path.exists(data_path):
        data_path = 'data/farmer_transactions.csv'

    print(f"Training dataset: {data_path}")
    data = ml_engine.load_and_preprocess_data(data_path)
    
    # Prepare features
    X, y = ml_engine.prepare_features(data)
    
    # Train model
    model = ml_engine.train_model(X, y)
    
    # Save model
    ml_engine.save_model()
    
    print("\nEnterprise ML Model Training Complete!")
    print("Ready for production deployment!")

if __name__ == "__main__":
    main()