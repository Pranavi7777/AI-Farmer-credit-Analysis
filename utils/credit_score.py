"""
🌾 AI Farmer Credit Intelligence Platform
Enterprise Credit Scoring Engine
"""

import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class EnterpriseCreditScorer:
    def __init__(self):
        self.model = None
        self.feature_columns = None
        self.village_risk_map = {}
        self.ml_mode = False
        self.enable_ml_model = os.getenv('ENABLE_ML_MODEL', 'false').lower() == 'true'

        if self.enable_ml_model:
            self.load_models()
        else:
            print("INFO: ML model loading disabled (ENABLE_ML_MODEL=false). Using rule-based scoring.")
            self._initialize_fallback_system()
    
    def load_models(self):
        """Load trained model and components"""
        try:
            import joblib

            # Try multiple path options
            base_paths = ['../models/', 'models/', './models/', '']
            
            for base_path in base_paths:
                model_path = base_path + 'credit_model_enterprise.pkl'
                columns_path = base_path + 'model_columns_enterprise.pkl'
                village_path = base_path + 'village_risk_map.pkl' 
                
                try:
                    self.model = joblib.load(model_path)
                    self.feature_columns = joblib.load(columns_path)
                    self.village_risk_map = joblib.load(village_path)
                    self.ml_mode = True
                    print("✅ Enterprise models loaded successfully!")
                    return
                except FileNotFoundError:
                    continue
            
            # Fallback: Use rule-based scoring
            print("⚠️ ML models not found. Using rule-based scoring system.")
            self._initialize_fallback_system()
            
        except Exception as e:
            print(f"⚠️ Error loading ML models: {e}")
            print("🔧 Using rule-based scoring as fallback")
            self._initialize_fallback_system()
    
    def _initialize_fallback_system(self):
        """Initialize fallback village risk map and scoring system"""
        # Default village risk indices
        self.village_risk_map = {
            'VILL001': 0.85,
            'VILL002': 0.92, 
            'VILL003': 0.75
        }
        self.ml_mode = False
        print("Rule-based credit scoring system initialized (ML models not available)")
    
    def generate_farmer_unique_id(self, mobile, village_code):
        """Generate FarmerUniqueID from mobile and village code"""
        return f"{mobile}{village_code}"
    
    def get_village_risk_index(self, village_code):
        """Get village risk index from historical data"""
        return self.village_risk_map.get(village_code, 0.8)  # Default risk
    
    def calculate_credit_score(self, farmer_data):
        """Calculate enterprise credit score for a farmer"""
        
        # Extract basic information
        mobile = farmer_data.get('mobile')
        village_code = farmer_data.get('village_code')
        
        # Generate unique ID
        farmer_unique_id = self.generate_farmer_unique_id(mobile, village_code)
        
        # Get village risk index
        village_risk_index = self.get_village_risk_index(village_code)
        
        # Prepare feature vector
        features = {
            'TotalPurchase': farmer_data.get('total_purchase', 0),
            'CreditTaken': farmer_data.get('credit_taken', 0),
            'PaymentDone': farmer_data.get('payment_done', 0),
            'DelayDays': farmer_data.get('delay_days', 0),
            'OutstandingAmount': farmer_data.get('outstanding_amount', 0),
            'VillageRiskIndex': village_risk_index
        }
        
        # Calculate derived features
        if features['CreditTaken'] > 0:
            features['PaymentRatio'] = features['PaymentDone'] / features['CreditTaken']
        else:
            features['PaymentRatio'] = 0
            
        if features['TotalPurchase'] > 0:
            features['UtilizationRatio'] = features['CreditTaken'] / features['TotalPurchase']
        else:
            features['UtilizationRatio'] = 0
        
        # Choose scoring method
        if self.ml_mode and self.model:
            credit_score, probability = self._ml_score(farmer_data, features)
        else:
            credit_score, probability = self._rule_based_score(features)
        
        # Determine risk level
        if credit_score >= 750:
            risk_level = "LOW RISK"
            risk_color = "green"
        elif credit_score >= 550:
            risk_level = "MEDIUM RISK"
            risk_color = "orange"
        else:
            risk_level = "HIGH RISK"
            risk_color = "red"
        
        return {
            'farmer_unique_id': farmer_unique_id,
            'credit_score': credit_score,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'probability': round(probability, 4),
            'village_risk_index': village_risk_index,
            'timestamp': datetime.now().isoformat(),
            'scoring_method': 'ML' if self.ml_mode else 'Rule-Based'
        }
    
    def _ml_score(self, farmer_data, features):
        """ML-based scoring using trained model"""
        import pandas as pd

        # Create DataFrame
        input_df = pd.DataFrame([features])
        
        # Add categorical features
        crop_season = farmer_data.get('crop_season', 'Kharif')
        season_features = pd.get_dummies([crop_season], prefix='Season')
        
        # Delay category
        delay_days = features['DelayDays']
        if delay_days <= 5:
            delay_cat = 'Low'
        elif delay_days <= 15:
            delay_cat = 'Medium'
        elif delay_days <= 30:
            delay_cat = 'High'
        else:
            delay_cat = 'Critical'
        
        delay_features = pd.get_dummies([delay_cat], prefix='Delay')
        
        # Combine features
        for col in season_features.columns:
            input_df[col] = season_features[col].iloc[0]
            
        for col in delay_features.columns:
            input_df[col] = delay_features[col].iloc[0]
        
        # Align with training features
        input_df = input_df.reindex(columns=self.feature_columns, fill_value=0)
        
        # Get prediction probability
        probability = self.model.predict_proba(input_df)[0][1]
        
        # Convert to credit score (0-900)
        credit_score = int(probability * 900)
        
        return credit_score, probability
    
    def _rule_based_score(self, features):
        """Rule-based scoring when ML models are not available"""
        score = 500  # Base score
        
        # Payment ratio component (0-200 points)
        payment_ratio = features['PaymentRatio']
        if payment_ratio >= 1.0:
            score += 200
        elif payment_ratio >= 0.8:
            score += 150
        elif payment_ratio >= 0.6:
            score += 100
        elif payment_ratio >= 0.4:
            score += 50
        # Below 0.4 gets 0 points
        
        # Delay component (-150 to +50 points)
        delay_days = features['DelayDays']
        if delay_days == 0:
            score += 50
        elif delay_days <= 5:
            score += 25
        elif delay_days <= 15:
            score -= 25
        elif delay_days <= 30:
            score -= 75
        else:
            score -= 150
        
        # Village risk component (0-100 points)
        village_risk = features['VillageRiskIndex']
        score += int(village_risk * 100)
        
        # Outstanding amount component (-100 to +50 points)
        outstanding = features['OutstandingAmount']
        credit_taken = features['CreditTaken']
        if credit_taken > 0:
            outstanding_ratio = outstanding / credit_taken
            if outstanding_ratio == 0:
                score += 50
            elif outstanding_ratio <= 0.1:
                score += 25
            elif outstanding_ratio <= 0.3:
                score -= 25
            else:
                score -= 100
        
        # Ensure score is within bounds
        score = max(300, min(900, score))
        
        # Convert to probability for consistency
        probability = score / 900
        
        return score, probability
    
    def batch_score_farmers(self, farmers_list):
        """Score multiple farmers in batch"""
        results = []
        for farmer in farmers_list:
            score_result = self.calculate_credit_score(farmer)
            results.append(score_result)
        return results
    
    def get_village_analytics(self, village_code):
        """Get analytics for a specific village"""
        village_risk = self.get_village_risk_index(village_code)
        
        return {
            'village_code': village_code,
            'risk_index': village_risk,
            'risk_category': 'Low' if village_risk > 0.9 else 'Medium' if village_risk > 0.8 else 'High',
            'recommendation': self.get_village_recommendation(village_risk)
        }
    
    def get_village_recommendation(self, risk_index):
        """Get recommendation based on village risk"""
        if risk_index > 0.9:
            return "Excellent payment history. Approve loans with standard terms."
        elif risk_index > 0.8:
            return "Good payment history. Monitor closely, moderate credit limits."
        else:
            return "High risk area. Require guarantors, shorter loan terms."

def test_credit_scorer():
    """Test the credit scoring engine"""
    print("🧪 Testing Enterprise Credit Scoring Engine...")
    
    scorer = EnterpriseCreditScorer()
    
    # Test farmer data
    test_farmer = {
        'mobile': '9876543210',
        'village_code': 'VILL001',
        'total_purchase': 50000,
        'credit_taken': 30000,
        'payment_done': 30000,
        'delay_days': 2,
        'outstanding_amount': 0,
        'crop_season': 'Kharif'
    }
    
    result = scorer.calculate_credit_score(test_farmer)
    
    print("=" * 50)
    print("📊 CREDIT SCORE RESULT")
    print("=" * 50)
    for key, value in result.items():
        print(f"{key}: {value}")
    
    # Village analytics
    village_analytics = scorer.get_village_analytics('VILL001')
    print("\n🏘️ VILLAGE ANALYTICS")
    print("=" * 30)
    for key, value in village_analytics.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    test_credit_scorer()