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

    def _safe_div(self, numerator, denominator):
        """Safely divide numbers and avoid ZeroDivisionError."""
        if not denominator:
            return 0.0
        return float(numerator) / float(denominator)

    def _crop_type_stability(self, crop_type):
        """Return a stability score for crop types (higher is safer)."""
        crop_key = str(crop_type or '').strip().lower()
        stability_map = {
            'paddy': 0.8,
            'maize': 0.76,
            'wheat': 0.79,
            'pulses': 0.72,
            'vegetables': 0.68,
            'cotton': 0.63,
            'sugarcane': 0.66,
            'mixed': 0.74
        }
        return stability_map.get(crop_key, 0.7)

    def _farm_activity_score(self, farm_activity_level):
        level = str(farm_activity_level or '').strip().lower()
        if level == 'high':
            return 0.95
        if level == 'medium':
            return 0.75
        if level == 'low':
            return 0.55
        return 0.7

    def _estimate_weather_risk(self, village_code, crop_type, crop_season):
        """Estimate weather exposure risk (0 low risk, 1 high risk)."""
        village_risk = 1.0 - min(max(self.get_village_risk_index(village_code), 0.0), 1.0)
        crop_key = str(crop_type or '').strip().lower()
        season_key = str(crop_season or '').strip().lower()

        crop_exposure = {
            'paddy': 0.55,
            'maize': 0.45,
            'wheat': 0.4,
            'pulses': 0.38,
            'vegetables': 0.5,
            'cotton': 0.58,
            'sugarcane': 0.47,
            'mixed': 0.44
        }.get(crop_key, 0.45)

        season_bump = 0.05 if season_key == 'kharif' else 0.0
        weather_risk = (0.5 * village_risk) + (0.5 * crop_exposure) + season_bump
        return min(max(weather_risk, 0.0), 1.0)

    def _build_features(self, farmer_data):
        """Build normalized feature bundle for scoring + explainability."""
        village_code = farmer_data.get('village_code')
        village_risk_index = self.get_village_risk_index(village_code)

        total_purchase = float(farmer_data.get('total_purchase', 0) or 0)
        credit_taken = float(farmer_data.get('credit_taken', 0) or 0)
        payment_done = float(farmer_data.get('payment_done', 0) or 0)
        delay_days = int(farmer_data.get('delay_days', 0) or 0)
        outstanding_amount = float(farmer_data.get('outstanding_amount', 0) or 0)

        crop_season = farmer_data.get('crop_season', 'Kharif')
        crop_type = farmer_data.get('crop_type')
        if not crop_type:
            crop_type = 'Paddy' if str(crop_season).lower() == 'kharif' else 'Wheat'

        season_income = float(farmer_data.get('season_income', 0) or 0)
        if season_income <= 0:
            season_income = max(total_purchase * 1.15, payment_done * 1.1, 10000.0)

        farm_activity_level = farmer_data.get('farm_activity_level')
        if not farm_activity_level:
            if total_purchase >= 150000:
                farm_activity_level = 'high'
            elif total_purchase >= 60000:
                farm_activity_level = 'medium'
            else:
                farm_activity_level = 'low'

        transaction_count = int(farmer_data.get('transaction_count', 0) or 0)
        tx_consistency = farmer_data.get('transaction_consistency')

        input_dependency = farmer_data.get('input_dependency')
        if input_dependency is None:
            input_dependency = self._safe_div(credit_taken, total_purchase)
        input_dependency = float(input_dependency or 0)

        weather_risk_index = farmer_data.get('weather_risk_index')
        if weather_risk_index is None:
            weather_risk_index = self._estimate_weather_risk(village_code, crop_type, crop_season)
        weather_risk_index = min(max(float(weather_risk_index), 0.0), 1.0)

        features = {
            'TotalPurchase': total_purchase,
            'CreditTaken': credit_taken,
            'PaymentDone': payment_done,
            'DelayDays': delay_days,
            'OutstandingAmount': outstanding_amount,
            'VillageRiskIndex': village_risk_index,
            'CropSeason': crop_season,
            'CropType': crop_type,
            'SeasonIncome': season_income,
            'FarmActivityLevel': farm_activity_level,
            'WeatherRiskIndex': weather_risk_index,
            'InputDependency': input_dependency,
            'TransactionCount': max(transaction_count, 0)
        }

        features['PaymentRatio'] = self._safe_div(features['PaymentDone'], features['CreditTaken'])
        features['UtilizationRatio'] = self._safe_div(features['CreditTaken'], features['TotalPurchase'])
        features['OutstandingRatio'] = self._safe_div(features['OutstandingAmount'], features['CreditTaken'])

        # Convert optional categorical consistency into normalized score.
        if tx_consistency in ['regular', 'high', 'good']:
            tx_consistency_score = 0.9
        elif tx_consistency in ['irregular', 'low', 'poor']:
            tx_consistency_score = 0.45
        elif isinstance(tx_consistency, (float, int)):
            tx_consistency_score = min(max(float(tx_consistency), 0.0), 1.0)
        else:
            monthly_density = min(self._safe_div(features['TransactionCount'], 12.0), 1.0)
            repayment_stability = min(max(features['PaymentRatio'], 0.0), 1.0)
            delay_penalty = min(max(features['DelayDays'], 0), 30) / 30.0
            tx_consistency_score = (0.5 * monthly_density) + (0.4 * repayment_stability) + (0.1 * (1.0 - delay_penalty))

        features['TransactionConsistency'] = min(max(tx_consistency_score, 0.0), 1.0)
        features['CropStabilityScore'] = self._crop_type_stability(features['CropType'])
        features['FarmActivityScore'] = self._farm_activity_score(features['FarmActivityLevel'])
        income_base = max(features['CreditTaken'] * 1.4, 1.0)
        features['SeasonIncomeStrength'] = min(max(self._safe_div(features['SeasonIncome'], income_base), 0.0), 1.2)

        return features

    def _build_credit_health_report(self, features):
        """Build CIBIL-like weighted factors and actionable suggestions."""
        payment_ratio = min(max(features.get('PaymentRatio', 0.0), 0.0), 1.5)
        utilization = min(max(features.get('UtilizationRatio', 0.0), 0.0), 1.5)
        outstanding_ratio = min(max(features.get('OutstandingRatio', 0.0), 0.0), 2.0)
        delay_days = max(int(features.get('DelayDays', 0)), 0)
        crop_stability = min(max(features.get('CropStabilityScore', 0.7), 0.0), 1.0)
        season_income_strength = min(max(features.get('SeasonIncomeStrength', 0.7), 0.0), 1.2)
        farm_activity_score = min(max(features.get('FarmActivityScore', 0.7), 0.0), 1.0)
        tx_consistency = min(max(features.get('TransactionConsistency', 0.6), 0.0), 1.0)
        weather_risk = min(max(features.get('WeatherRiskIndex', 0.45), 0.0), 1.0)
        input_dependency = min(max(features.get('InputDependency', 0.5), 0.0), 1.5)

        factor_weights = {
            'repayment_history': 24,
            'credit_utilization': 12,
            'outstanding_balance': 12,
            'payment_delay': 8,
            'crop_type': 9,
            'season_income': 11,
            'farm_activity_level': 8,
            'transaction_consistency': 8,
            'weather_risk_index': 5,
            'input_dependency': 3
        }

        factor_strength = {
            'repayment_history': min(payment_ratio, 1.0),
            'credit_utilization': max(0.0, 1.0 - min(utilization, 1.0)),
            'outstanding_balance': max(0.0, 1.0 - min(outstanding_ratio, 1.0)),
            'payment_delay': max(0.0, 1.0 - (min(delay_days, 30) / 30.0)),
            'crop_type': crop_stability,
            'season_income': min(season_income_strength, 1.0),
            'farm_activity_level': farm_activity_score,
            'transaction_consistency': tx_consistency,
            'weather_risk_index': 1.0 - weather_risk,
            'input_dependency': max(0.0, 1.0 - min(input_dependency, 1.0))
        }

        factor_breakdown = []
        for factor_name, weight in factor_weights.items():
            factor_breakdown.append({
                'factor': factor_name,
                'weight': weight,
                'strength': round(factor_strength[factor_name], 4),
                'contribution': round(weight * factor_strength[factor_name], 2)
            })

        increase_score_factors = []
        decrease_score_factors = []
        improvement_suggestions = []

        if payment_ratio >= 0.8:
            increase_score_factors.append('Strong repayment history improves score')
        else:
            decrease_score_factors.append('Low repayment ratio reduces score')
            improvement_suggestions.append('Increase repayment ratio above 80%')

        if utilization <= 0.7:
            increase_score_factors.append('Balanced credit utilization supports score')
        else:
            decrease_score_factors.append('High credit dependency lowers score')
            improvement_suggestions.append('Reduce credit utilization by increasing direct payments')

        if outstanding_ratio <= 0.3:
            increase_score_factors.append('Lower outstanding balance improves score')
        else:
            decrease_score_factors.append('High outstanding balance increases default risk')
            improvement_suggestions.append('Reduce outstanding amount to below 30% of credit')

        if delay_days <= 5:
            increase_score_factors.append('On-time payments improve score')
        else:
            decrease_score_factors.append('Frequent payment delays reduce score')
            improvement_suggestions.append('Keep payment delay under 5 days')

        if crop_stability >= 0.72:
            increase_score_factors.append('Crop type supports stable seasonal income')
        else:
            decrease_score_factors.append('Crop type has higher market/weather volatility')
            improvement_suggestions.append('Diversify to mixed crops for better income stability')

        if season_income_strength >= 0.75:
            increase_score_factors.append('Season income is strong against credit exposure')
        else:
            decrease_score_factors.append('Season income is weak relative to credit usage')
            improvement_suggestions.append('Increase seasonal income buffer before expanding credit')

        if farm_activity_score >= 0.75:
            increase_score_factors.append('Farm activity level indicates stronger repayment capacity')
        else:
            decrease_score_factors.append('Low farm activity level limits repayment capacity')
            improvement_suggestions.append('Improve farm activity volume with planned input cycles')

        if tx_consistency >= 0.7:
            increase_score_factors.append('Transaction consistency improves credit trust')
        else:
            decrease_score_factors.append('Irregular transaction behavior reduces confidence')
            improvement_suggestions.append('Maintain regular purchase/payment activity each month')

        if weather_risk <= 0.35:
            increase_score_factors.append('Low weather risk improves agricultural repayment outlook')
        else:
            decrease_score_factors.append('High weather risk lowers expected repayment stability')
            improvement_suggestions.append('Use weather-resilient crop planning and smaller credit cycles')

        if input_dependency <= 0.6:
            increase_score_factors.append('Balanced input dependency supports healthy cash flow')
        else:
            decrease_score_factors.append('High input dependency signals credit stress risk')
            improvement_suggestions.append('Reduce fertilizer/seed dependency by increasing upfront payment share')

        return {
            'cibil_style_factors': factor_weights,
            'factor_breakdown': factor_breakdown,
            'increase_score_factors': increase_score_factors,
            'decrease_score_factors': decrease_score_factors,
            'improvement_suggestions': improvement_suggestions,
            'unique_farmer_factors': {
                'crop_type': features.get('CropType'),
                'season_income': round(features.get('SeasonIncome', 0.0), 2),
                'farm_activity_level': features.get('FarmActivityLevel'),
                'transaction_consistency': round(features.get('TransactionConsistency', 0.0), 4),
                'weather_risk_index': round(features.get('WeatherRiskIndex', 0.0), 4),
                'input_dependency': round(features.get('InputDependency', 0.0), 4)
            }
        }
    
    def calculate_credit_score(self, farmer_data):
        """Calculate enterprise credit score for a farmer"""
        
        # Extract basic information
        mobile = farmer_data.get('mobile')
        village_code = farmer_data.get('village_code')
        
        # Generate unique ID
        farmer_unique_id = self.generate_farmer_unique_id(mobile, village_code)
        
        # Build feature bundle once for score + explainability.
        features = self._build_features(farmer_data)
        village_risk_index = features['VillageRiskIndex']
        
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
        
        credit_health = self._build_credit_health_report(features)

        return {
            'farmer_unique_id': farmer_unique_id,
            'credit_score': credit_score,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'probability': round(probability, 4),
            'village_risk_index': village_risk_index,
            'timestamp': datetime.now().isoformat(),
            'scoring_method': 'ML' if self.ml_mode else 'Rule-Based',
            'cibil_style_factors': credit_health['cibil_style_factors'],
            'factor_breakdown': credit_health['factor_breakdown'],
            'increase_score_factors': credit_health['increase_score_factors'],
            'decrease_score_factors': credit_health['decrease_score_factors'],
            'improvement_suggestions': credit_health['improvement_suggestions'],
            'unique_farmer_factors': credit_health.get('unique_farmer_factors', {})
        }

    def simulate_credit_score(self, farmer_data, payment_amount=0.0, planned_credit_amount=0.0, expected_delay_days=None):
        """Simulate score impact for planned actions to show real-time improvement."""
        current = self.calculate_credit_score(farmer_data)

        sim = {
            'mobile': farmer_data.get('mobile'),
            'village_code': farmer_data.get('village_code'),
            'total_purchase': float(farmer_data.get('total_purchase', 0) or 0),
            'credit_taken': float(farmer_data.get('credit_taken', 0) or 0),
            'payment_done': float(farmer_data.get('payment_done', 0) or 0),
            'outstanding_amount': float(farmer_data.get('outstanding_amount', 0) or 0),
            'delay_days': int(farmer_data.get('delay_days', 0) or 0),
            'crop_season': farmer_data.get('crop_season', 'Kharif'),
            'crop_type': farmer_data.get('crop_type'),
            'season_income': float(farmer_data.get('season_income', 0) or 0),
            'farm_activity_level': farmer_data.get('farm_activity_level'),
            'transaction_consistency': farmer_data.get('transaction_consistency'),
            'transaction_count': int(farmer_data.get('transaction_count', 0) or 0),
            'weather_risk_index': farmer_data.get('weather_risk_index'),
            'input_dependency': farmer_data.get('input_dependency')
        }

        payment_amount = max(float(payment_amount or 0), 0.0)
        planned_credit_amount = max(float(planned_credit_amount or 0), 0.0)

        if payment_amount > 0:
            sim['payment_done'] += payment_amount
            sim['outstanding_amount'] = max(sim['outstanding_amount'] - payment_amount, 0.0)

        if planned_credit_amount > 0:
            sim['credit_taken'] += planned_credit_amount
            sim['total_purchase'] += planned_credit_amount
            sim['outstanding_amount'] += planned_credit_amount

        if expected_delay_days is not None:
            sim['delay_days'] = max(int(expected_delay_days), 0)

        projected = self.calculate_credit_score(sim)

        return {
            'current': current,
            'projected': projected,
            'score_delta': projected['credit_score'] - current['credit_score'],
            'inputs': {
                'payment_amount': payment_amount,
                'planned_credit_amount': planned_credit_amount,
                'expected_delay_days': sim['delay_days']
            }
        }
    
    def _ml_score(self, farmer_data, features):
        """ML-based scoring using trained model"""
        import pandas as pd

        # Keep only numeric base features before adding one-hot vectors.
        numeric_features = {
            'TotalPurchase': features.get('TotalPurchase', 0.0),
            'CreditTaken': features.get('CreditTaken', 0.0),
            'PaymentDone': features.get('PaymentDone', 0.0),
            'DelayDays': features.get('DelayDays', 0),
            'OutstandingAmount': features.get('OutstandingAmount', 0.0),
            'VillageRiskIndex': features.get('VillageRiskIndex', 0.8),
            'PaymentRatio': features.get('PaymentRatio', 0.0),
            'UtilizationRatio': features.get('UtilizationRatio', 0.0),
            'OutstandingRatio': features.get('OutstandingRatio', 0.0),
            'SeasonIncome': features.get('SeasonIncome', 0.0),
            'FarmActivityScore': features.get('FarmActivityScore', 0.7),
            'TransactionConsistency': features.get('TransactionConsistency', 0.6),
            'WeatherRiskIndex': features.get('WeatherRiskIndex', 0.45),
            'InputDependency': features.get('InputDependency', 0.5),
            'CropStabilityScore': features.get('CropStabilityScore', 0.7),
            'SeasonIncomeStrength': features.get('SeasonIncomeStrength', 0.7)
        }

        input_df = pd.DataFrame([numeric_features])
        
        # Add categorical features
        crop_season = features.get('CropSeason') or farmer_data.get('crop_season', 'Kharif')
        crop_type = features.get('CropType') or farmer_data.get('crop_type', 'Mixed')
        farm_activity = features.get('FarmActivityLevel') or farmer_data.get('farm_activity_level', 'medium')

        season_features = pd.get_dummies([crop_season], prefix='Season')
        crop_features = pd.get_dummies([crop_type], prefix='Crop')
        activity_features = pd.get_dummies([farm_activity], prefix='FarmActivity')
        
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

        for col in crop_features.columns:
            input_df[col] = crop_features[col].iloc[0]

        for col in activity_features.columns:
            input_df[col] = activity_features[col].iloc[0]
            
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

        # Continuous refinements so score can change smoothly in simulations.
        payment_ratio = min(max(features.get('PaymentRatio', 0), 0), 1.5)
        utilization_ratio = min(max(features.get('UtilizationRatio', 0), 0), 1.5)
        outstanding_ratio = min(max(features.get('OutstandingRatio', 0), 0), 1.5)
        crop_stability = min(max(features.get('CropStabilityScore', 0.7), 0), 1.0)
        season_income_strength = min(max(features.get('SeasonIncomeStrength', 0.7), 0), 1.2)
        farm_activity_score = min(max(features.get('FarmActivityScore', 0.7), 0), 1.0)
        tx_consistency = min(max(features.get('TransactionConsistency', 0.6), 0), 1.0)
        weather_risk = min(max(features.get('WeatherRiskIndex', 0.45), 0), 1.0)
        input_dependency = min(max(features.get('InputDependency', 0.5), 0), 1.5)

        score += int(min(payment_ratio, 1.0) * 40)
        score += int((1 - min(utilization_ratio, 1.0)) * 25)
        score += int((1 - min(outstanding_ratio, 1.0)) * 35)

        # Innovation factors: reflect farmer-specific operating context.
        score += int((crop_stability - 0.5) * 70)
        score += int((min(season_income_strength, 1.0) - 0.5) * 90)
        score += int((farm_activity_score - 0.5) * 60)
        score += int((tx_consistency - 0.5) * 70)
        score += int(((1 - weather_risk) - 0.5) * 55)
        score += int((0.7 - min(input_dependency, 1.2)) * 45)
        
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