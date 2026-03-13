"""
🌾 AI Farmer Credit Intelligence Platform
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
    
    def load_and_preprocess_data(self, file_path):
        """Load and preprocess farmer transaction data"""
        print("🔹 Loading enterprise farmer data...")
        data = pd.read_csv(file_path)
        
        # Create derived features
        data['PaymentRatio'] = data['PaymentDone'] / data['CreditTaken']
        data['PaymentRatio'] = data['PaymentRatio'].fillna(0)
        data['UtilizationRatio'] = data['CreditTaken'] / data['TotalPurchase']
        data['UtilizationRatio'] = data['UtilizationRatio'].fillna(0)
        
        # Create risk buckets
        data['DelayCategory'] = pd.cut(data['DelayDays'], 
                                     bins=[-1, 5, 15, 30, 100], 
                                     labels=['Low', 'Medium', 'High', 'Critical'])
        
        # Village risk mapping
        village_risk = data.groupby('VillageCode')['LoanRepaid'].mean()
        self.village_risk_map = village_risk.to_dict()
        
        print(f"✅ Loaded {len(data)} farmer records from {data['VillageCode'].nunique()} villages")
        print(f"🏘️ Village Risk Index: {dict(village_risk)}")
        
        return data
    
    def prepare_features(self, data):
        """Prepare feature matrix for ML model"""
        
        # Select features for training
        feature_columns = [
            'TotalPurchase', 'CreditTaken', 'PaymentDone', 
            'DelayDays', 'OutstandingAmount', 'VillageRiskIndex',
            'PaymentRatio', 'UtilizationRatio'
        ]
        
        X = data[feature_columns].copy()
        
        # Add categorical features
        categorical_features = pd.get_dummies(data['CropSeason'], prefix='Season')
        delay_categories = pd.get_dummies(data['DelayCategory'], prefix='Delay')
        
        # Combine all features
        X = pd.concat([X, categorical_features, delay_categories], axis=1)
        
        # Target variable
        y = data['LoanRepaid']
        
        self.feature_columns = X.columns.tolist()
        
        print(f"🔧 Prepared {len(self.feature_columns)} features for training")
        print(f"📊 Features: {self.feature_columns}")
        
        return X, y
    
    def train_model(self, X, y):
        """Train Random Forest Model"""
        print("🚀 Training Enterprise Random Forest Model...")
        
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
        print("🏆 MODEL PERFORMANCE REPORT")
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
        
        print("\n🔍 TOP 5 FEATURE IMPORTANCE:")
        for idx, row in feature_importance.head().iterrows():
            print(f"• {row['feature']}: {row['importance']:.3f}")
        
        return self.model
    
    def save_model(self):
        """Save trained model and components"""
        joblib.dump(self.model, 'credit_model_enterprise.pkl')
        joblib.dump(self.feature_columns, 'model_columns_enterprise.pkl')
        joblib.dump(self.village_risk_map, 'village_risk_map.pkl')
        
        print("\n💾 Model saved successfully!")
        print("• credit_model_enterprise.pkl")
        print("• model_columns_enterprise.pkl")
        print("• village_risk_map.pkl")

def main():
    """Main training pipeline"""
    print("🌾 AI FARMER CREDIT INTELLIGENCE PLATFORM")
    print("🤖 Enterprise ML Training Pipeline")
    print("=" * 60)
    
    # Initialize ML Engine
    ml_engine = EnterpriseMLEngine()
    
    # Load and preprocess data
    data_path = os.path.join('..', 'data', 'farmer_transactions.csv')
    if not os.path.exists(data_path):
        data_path = 'data/farmer_transactions.csv'
    data = ml_engine.load_and_preprocess_data(data_path)
    
    # Prepare features
    X, y = ml_engine.prepare_features(data)
    
    # Train model
    model = ml_engine.train_model(X, y)
    
    # Save model
    ml_engine.save_model()
    
    print("\n🎉 Enterprise ML Model Training Complete!")
    print("Ready for production deployment!")

if __name__ == "__main__":
    main()