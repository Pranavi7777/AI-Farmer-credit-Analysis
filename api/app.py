"""
🌾 AI Farmer Credit Intelligence Platform
Enterprise Flask API Backend
Multi-Village Dealer Management System  
PostgreSQL + SQLite Support with SQLAlchemy
"""

from flask import Flask, request, jsonify, render_template, session, redirect
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load production environment variables
load_dotenv('.env.production')

# Get the current directory and set paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

sys.path.append(parent_dir)
from utils.credit_score import EnterpriseCreditScorer
from utils.database import init_database, Farmer, Transaction, Village, User, AuditLog, DatabaseConfig
from utils.auth_routes import init_auth_routes, add_protected_routes
from utils.security import login_required, role_required, audit_action
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Configure Flask with correct template and static folders
app = Flask(__name__, 
           template_folder=os.path.join(parent_dir, 'templates'),
           static_folder=os.path.join(parent_dir, 'static'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'farmer-credit-ai-production-2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)  # 8 hour sessions

# Database Configuration - Support both local and cloud
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'true').lower() == 'true'
DATABASE_URL = os.getenv('DATABASE_URL')

# Configure Flask for production
if os.getenv('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.config['ENV'] = 'production'
else:
    app.config['DEBUG'] = True

class EnterpriseAPI:
    def __init__(self):
        self.credit_scorer = EnterpriseCreditScorer()
        self.init_database()
    
    def init_database(self):
        """Initialize SQLAlchemy database (PostgreSQL or SQLite)"""
        try:
            self.engine, self.SessionLocal = init_database(use_postgresql=USE_POSTGRESQL)
            
            if USE_POSTGRESQL:
                print("✅ Enterprise Supabase Database initialized!")
                db_url = os.getenv('DATABASE_URL', '')
                if 'supabase.com' in db_url:
                    print("🔗 Connection: Supabase PostgreSQL (Cloud)")
                else:
                    print("🔗 Connection: Local PostgreSQL")
            else:
                print("✅ SQLite Database initialized!")
                print("🔗 Connection: farmer_credit_enterprise.db")
                
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            if USE_POSTGRESQL:
                print("🔄 Falling back to SQLite...")
                self.engine, self.SessionLocal = init_database(use_postgresql=False)
            else:
                raise e

# Initialize Enterprise API
enterprise_api = EnterpriseAPI()

# 🔐 Initialize Authentication System
init_auth_routes(app, enterprise_api.SessionLocal)
add_protected_routes(app, enterprise_api.SessionLocal)

@app.route('/')
def dashboard():
    """Main dashboard - redirects based on user role"""
    if 'user_id' in session:
        role = session.get('user_role')
        print(f"🔍 Dashboard redirect: User role = {role}")  # Debug log
        if role == 'ADMIN':
            return redirect('/admin_dashboard')
        elif role == 'DEALER':
            return redirect('/dealer')
        elif role == 'BANK_OFFICER':
            return redirect('/bank_dashboard')
    return redirect('/login')

@app.route('/dealer')
@login_required
@role_required(['DEALER', 'ADMIN'])
@audit_action('VIEW_DEALER_PAGE')
def dealer_app():
    """Dealer data entry interface"""
    return render_template('dealer_app.html')

@app.route('/analytics')
@login_required
@role_required(['ADMIN', 'BANK_OFFICER'])
@audit_action('VIEW_ANALYTICS')
def analytics():
    """Risk analytics dashboard"""
    return render_template('analytics.html')

@app.route('/api/register_farmer', methods=['POST'])
@login_required
@role_required(['DEALER', 'ADMIN'])
@audit_action('REGISTER_FARMER')
def register_farmer():
    """Register new farmer or update existing farmer"""
    try:
        data = request.json
        mobile = data['mobile']
        village_code = data['village_code']
        farmer_name = data.get('farmer_name', '')
        
        # Generate unique ID
        farmer_unique_id = f"{mobile}{village_code}"
        
        session = enterprise_api.SessionLocal()
        try:
            # Check if farmer exists
            existing_farmer = session.query(Farmer).filter_by(farmer_unique_id=farmer_unique_id).first()
            
            if existing_farmer:
                # Update existing farmer
                existing_farmer.farmer_name = farmer_name
                existing_farmer.last_transaction_date = datetime.now().isoformat()
                message = "Farmer profile updated successfully!"
            else:
                # Create new farmer
                new_farmer = Farmer(
                    farmer_unique_id=farmer_unique_id,
                    mobile=mobile,
                    village_code=village_code,
                    farmer_name=farmer_name
                )
                session.add(new_farmer)
                message = "New farmer registered successfully!"
            
            session.commit()
            
            return jsonify({
                'success': True,
                'message': message,
                'farmer_unique_id': farmer_unique_id
            })
            
        finally:
            session.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/add_transaction', methods=['POST'])
@login_required
@role_required(['DEALER', 'ADMIN'])
@audit_action('ADD_TRANSACTION')
def add_transaction():
    """Add new transaction and update credit score with dealer tracking"""
    try:
        data = request.json
        mobile = data['mobile']
        village_code = data['village_code']
        purchase_amount = float(data.get('purchase_amount', 0))
        credit_amount = float(data.get('credit_amount', 0))
        payment_amount = float(data.get('payment_amount', 0))
        crop_season = data.get('crop_season', 'Kharif')
        delay_days = int(data.get('delay_days', 0))
        dealer_id = data.get('dealer_id', 'DEALER001')
        
        farmer_unique_id = f"{mobile}{village_code}"
        
        session = enterprise_api.SessionLocal()
        try:
            # Get or create farmer first, then insert transaction to avoid FK autoflush issues.
            farmer = session.query(Farmer).filter_by(farmer_unique_id=farmer_unique_id).first()
            if not farmer:
                farmer = Farmer(
                    farmer_unique_id=farmer_unique_id,
                    mobile=mobile,
                    village_code=village_code,
                    farmer_name='Unknown'
                )
                session.add(farmer)

            # Add transaction after farmer exists in session.
            new_transaction = Transaction(
                farmer_unique_id=farmer_unique_id,
                transaction_date=datetime.now().isoformat(),
                purchase_amount=purchase_amount,
                credit_amount=credit_amount,
                payment_amount=payment_amount,
                crop_season=crop_season,
                delay_days=delay_days,
                transaction_type='PURCHASE',
                dealer_id=dealer_id
            )
            session.add(new_transaction)
            
            # Update farmer totals
            farmer.total_purchases = (farmer.total_purchases or 0) + purchase_amount
            farmer.total_credit_taken = (farmer.total_credit_taken or 0) + credit_amount
            farmer.total_payments = (farmer.total_payments or 0) + payment_amount
            farmer.current_outstanding = (farmer.current_outstanding or 0) + credit_amount - payment_amount
            farmer.last_transaction_date = datetime.now().isoformat()
            
            session.commit()
            
            # Calculate credit score
            farmer_data = {
                'mobile': mobile,
                'village_code': village_code,
                'total_purchase': farmer.total_purchases,
                'credit_taken': farmer.total_credit_taken,
                'payment_done': farmer.total_payments,
                'outstanding_amount': farmer.current_outstanding,
                'delay_days': delay_days,
                'crop_season': crop_season
            }
            
            credit_result = enterprise_api.credit_scorer.calculate_credit_score(farmer_data)
            
            # Update credit score in database
            farmer.credit_score = credit_result['credit_score']
            farmer.risk_level = credit_result['risk_level']
            session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Transaction added and credit score updated!',
                'credit_result': credit_result
            })

        except Exception:
            session.rollback()
            raise
            
        finally:
            session.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/get_credit_score', methods=['POST'])
def get_credit_score():
    """Get real-time credit score for a farmer"""
    try:
        data = request.json
        mobile = data['mobile']
        village_code = data['village_code']
        
        farmer_unique_id = f"{mobile}{village_code}"
        
        session = enterprise_api.SessionLocal()
        try:
            # Get latest farmer data
            farmer = session.query(Farmer).filter_by(farmer_unique_id=farmer_unique_id).first()
            
            if not farmer:
                return jsonify({'success': False, 'error': 'Farmer not found'}), 404
            
            # Get village data for risk index
            village = session.query(Village).filter_by(village_code=village_code).first()
            village_risk_index = village.risk_index if village else 0.8
            
            # Get village analytics
            village_analytics = enterprise_api.credit_scorer.get_village_analytics(village_code)
            
            return jsonify({
                'success': True,
                'farmer_unique_id': farmer_unique_id,
                'farmer_name': farmer.farmer_name,
                'total_purchases': farmer.total_purchases,
                'total_credit_taken': farmer.total_credit_taken,
                'total_payments': farmer.total_payments,
                'current_outstanding': farmer.current_outstanding,
                'credit_score': farmer.credit_score,
                'risk_level': farmer.risk_level,
                'village_risk_index': village_risk_index,
                'village_analytics': village_analytics
            })
            
        finally:
            session.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/village_analytics/<village_code>')
@login_required
@role_required(['ADMIN', 'BANK_OFFICER'])
@audit_action('VIEW_VILLAGE_ANALYTICS')
def village_analytics(village_code):
    """Get analytics for a specific village"""
    try:
        session = enterprise_api.SessionLocal()
        try:
            # Get village info first
            village = session.query(Village).filter_by(village_code=village_code).first()
            if not village:
                return jsonify({'success': False, 'error': 'Village not found'}), 404
            
            # Get farmers for this village
            farmers = session.query(Farmer).filter_by(village_code=village_code).all()
            
            # Calculate statistics (handle empty farmer list)
            total_farmers = len(farmers)
            
            if total_farmers == 0:
                # Return village info with zero stats but don't error
                village_analytics_data = enterprise_api.credit_scorer.get_village_analytics(village_code)
                
                return jsonify({
                    'success': True,
                    'village_code': village_code,
                    'village_name': village.village_name,
                    'total_farmers': 0,
                    'avg_credit_score': 0,
                    'total_purchases': 0,
                    'total_outstanding': 0,
                    'risk_distribution': {
                        'low_risk': 0,
                        'medium_risk': 0,
                        'high_risk': 0
                    },
                    'village_risk_index': village_analytics_data['risk_index'],
                    'recommendation': village_analytics_data['recommendation'],
                    'status': 'No farmers registered yet'
                })
            
            # Calculate statistics with farmer data
            total_purchases = sum(f.total_purchases or 0 for f in farmers)
            total_outstanding = sum(f.current_outstanding or 0 for f in farmers)
            avg_credit_score = sum(f.credit_score or 0 for f in farmers) / total_farmers if total_farmers > 0 else 0
            
            # Risk distribution
            low_risk_count = len([f for f in farmers if f.risk_level == 'LOW RISK'])
            medium_risk_count = len([f for f in farmers if f.risk_level == 'MEDIUM RISK'])
            high_risk_count = len([f for f in farmers if f.risk_level == 'HIGH RISK'])
            
            # Get village recommendation
            village_analytics_data = enterprise_api.credit_scorer.get_village_analytics(village_code)
            
            return jsonify({
                'success': True,
                'village_code': village_code,
                'village_name': village.village_name,
                'total_farmers': total_farmers,
                'avg_credit_score': round(avg_credit_score, 2),
                'total_purchases': round(total_purchases, 2),
                'total_outstanding': round(total_outstanding, 2),
                'risk_distribution': {
                    'low_risk': low_risk_count,
                    'medium_risk': medium_risk_count,
                    'high_risk': high_risk_count
                },
                'village_risk_index': village_analytics_data['risk_index'],
                'recommendation': village_analytics_data['recommendation'],
                'status': 'Active'
            })
            
        finally:
            session.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/dashboard_stats')
def dashboard_stats():
    """Get overall platform statistics"""
    try:
        session = enterprise_api.SessionLocal()
        try:
            # Get all farmers
            farmers = session.query(Farmer).all()
            
            if not farmers:
                return jsonify({
                    'success': True,
                    'total_farmers': 0,
                    'total_villages': 0,
                    'avg_credit_score': 0,
                    'total_business': 0,
                    'total_outstanding': 0
                })
            
            # Calculate overall statistics
            total_farmers = len(farmers)
            total_villages = len(set(f.village_code for f in farmers))
            total_business = sum(f.total_purchases or 0 for f in farmers)
            total_outstanding = sum(f.current_outstanding or 0 for f in farmers)
            avg_credit_score = sum(f.credit_score or 0 for f in farmers) / total_farmers if total_farmers > 0 else 0
            
            return jsonify({
                'success': True,
                'total_farmers': total_farmers,
                'total_villages': total_villages,
                'avg_credit_score': round(avg_credit_score, 2),
                'total_business': round(total_business, 2),
                'total_outstanding': round(total_outstanding, 2)
            })
            
        finally:
            session.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# 🔧 Admin API Endpoints
@app.route('/api/admin/stats')
@login_required
@role_required(['ADMIN'])
@audit_action('VIEW_ADMIN_STATS')
def admin_stats():
    """Get admin dashboard statistics"""
    try:
        session = enterprise_api.SessionLocal()
        
        # Count users
        total_users = session.query(User).count()
        
        # Count farmers
        total_farmers = session.query(Farmer).count()
        
        # Count villages
        total_villages = session.query(Village).count()
        
        # Calculate total outstanding credit
        farmers = session.query(Farmer).all()
        total_credit = sum(farmer.current_outstanding or 0 for farmer in farmers)
        
        # Today's activities (audit logs)
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        today_activities = session.query(AuditLog).filter(
            AuditLog.timestamp >= today,
            AuditLog.timestamp < today + timedelta(days=1)
        ).count()
        
        return jsonify({
            'success': True,
            'users': total_users,
            'farmers': total_farmers,
            'villages': total_villages,
            'credit': total_credit,
            'activities': today_activities
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()

@app.route('/api/admin/create_user', methods=['POST'])
@login_required
@role_required(['ADMIN'])
@audit_action('CREATE_USER')
def admin_create_user():
    """Create new user account"""
    try:
        data = request.json
        session = enterprise_api.SessionLocal()
        
        # Check if username exists
        existing_user = session.query(User).filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            role=data['role'],
            village_code=data.get('village_code'),
            full_name=data.get('full_name')
        )
        new_user.set_password(data['password'])
        
        session.add(new_user)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f"User {data['username']} created successfully",
            'user_id': new_user.user_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()

# 🏦 Credit Recommendation API
@app.route('/api/credit_recommendation/<farmer_id>')
@login_required
@role_required(['BANK_OFFICER', 'ADMIN'])
@audit_action('CREDIT_RECOMMENDATION')
def credit_recommendation(farmer_id):
    """Generate credit recommendation for a farmer"""
    try:
        session = enterprise_api.SessionLocal()
        
        # Get farmer data
        farmer = session.query(Farmer).filter_by(farmer_unique_id=farmer_id).first()
        if not farmer:
            return jsonify({'success': False, 'error': 'Farmer not found'}), 404
        
        # Calculate recommendation based on credit score and history
        credit_score = farmer.credit_score or 0
        outstanding = farmer.current_outstanding or 0
        total_payments = farmer.total_payments or 0
        total_credit = farmer.total_credit_taken or 0
        
        # Payment ratio
        payment_ratio = (total_payments / total_credit) if total_credit > 0 else 0
        
        # Determine recommended credit limit
        if credit_score >= 750:
            recommended_limit = max(50000, outstanding * 2)
            risk_assessment = "LOW RISK - Excellent credit history"
            recommendations = "Approve full credit limit. Consider premium rates."
        elif credit_score >= 650:
            recommended_limit = max(30000, outstanding * 1.5)
            risk_assessment = "MEDIUM RISK - Good credit history"
            recommendations = "Approve with standard terms. Monitor repayment."
        elif credit_score >= 500:
            recommended_limit = max(15000, outstanding)
            risk_assessment = "MODERATE RISK - Average credit history"
            recommendations = "Approve with enhanced monitoring. Consider collateral."
        else:
            recommended_limit = min(10000, outstanding * 0.5)
            risk_assessment = "HIGH RISK - Poor credit history"
            recommendations = "Limited credit only. Require guarantor or collateral."
        
        # Additional factors
        if outstanding > recommended_limit:
            recommendations += " WARNING: Current outstanding exceeds recommended limit."
        
        if payment_ratio < 0.7:
            recommendations += " Consider payment plan restructuring."
        
        return jsonify({
            'success': True,
            'farmer_id': farmer_id,
            'credit_score': credit_score,
            'recommended_limit': recommended_limit,
            'current_outstanding': outstanding,
            'risk_assessment': risk_assessment,
            'recommendations': recommendations,
            'payment_ratio': round(payment_ratio * 100, 1)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()

if __name__ == '__main__':
    print("🌾 AI FARMER CREDIT INTELLIGENCE PLATFORM")
    print("🚀 Enterprise API Server Starting...")
    print("=" * 50)
    print("📡 Village Dealer System: http://localhost:5000/dealer")
    print("📊 Risk Analytics Dashboard: http://localhost:5000/analytics")  
    print("🏠 Main Dashboard: http://localhost:5000")
    print("=" * 50)

@app.route('/api/test_database')
def test_database():
    """Test endpoint to check database content"""
    try:
        session = enterprise_api.SessionLocal()
        try:
            # Count entities
            farmer_count = session.query(Farmer).count()
            village_count = session.query(Village).count()
            user_count = session.query(User).count()
            
            # Get some sample data
            farmers = session.query(Farmer).limit(3).all()
            villages = session.query(Village).limit(3).all()
            
            farmer_list = []
            for f in farmers:
                farmer_list.append({
                    'id': f.farmer_unique_id,
                    'name': f.farmer_name,
                    'village': f.village_code,
                    'score': f.credit_score
                })
            
            village_list = []
            for v in villages:
                village_list.append({
                    'code': v.village_code,
                    'name': v.village_name,
                    'risk_index': v.risk_index
                })
            
            return jsonify({
                'success': True,
                'counts': {
                    'farmers': farmer_count,
                    'villages': village_count,
                    'users': user_count
                },
                'sample_farmers': farmer_list,
                'sample_villages': village_list
            })
            
        finally:
            session.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    app.run(debug=True, host='0.0.0.0', port=5000)

# For Vercel deployment - export the app instance
application = app