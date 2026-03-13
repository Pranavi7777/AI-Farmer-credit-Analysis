"""
🔐 Enterprise Authentication Routes
Login system with role-based access control
"""

from flask import render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from datetime import datetime
from utils.database import User, AuditLog
from utils.security import login_required, role_required, audit_action, create_user_session, clear_user_session
import secrets

def init_auth_routes(app, SessionLocal):
    """Initialize authentication routes"""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if request.method == 'GET':
            return render_template('login.html')
        
        try:
            data = request.json if request.is_json else request.form
            username = data['username']
            password = data['password']
            
            db_session = SessionLocal()
            user = db_session.query(User).filter_by(username=username, is_active=True).first()
            
            if user and user.check_password(password):
                # Create session
                create_user_session(user.user_id, user.role, user.village_code)
                
                # Update last login
                user.last_login = datetime.utcnow()
                db_session.commit()
                
                # Log successful login
                audit_log = AuditLog(
                    user_id=user.user_id,
                    action='LOGIN_SUCCESS',
                    ip_address=request.remote_addr
                )
                db_session.add(audit_log)
                db_session.commit()
                
                response_data = {
                    'success': True,
                    'user_role': user.role,
                    'redirect_url': get_dashboard_url(user.role)
                }
                
                if request.is_json:
                    return jsonify(response_data)
                else:
                    return redirect(get_dashboard_url(user.role))
            
            else:
                # Log failed login
                audit_log = AuditLog(
                    user_id=username,
                    action='LOGIN_FAILED',
                    ip_address=request.remote_addr,
                    details=f"Invalid credentials for username: {username}"
                )
                db_session.add(audit_log)
                db_session.commit()
                
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            db_session.close()
    
    @app.route('/logout')
    @login_required
    @audit_action('LOGOUT')
    def logout():
        """User logout"""
        clear_user_session()
        return redirect(url_for('login'))
    
    @app.route('/create_admin')
    def create_admin():
        """Create initial admin user (run once)"""
        try:
            db_session = SessionLocal()
            
            # Check if admin exists
            existing_admin = db_session.query(User).filter_by(role='ADMIN').first()
            if existing_admin:
                return jsonify({'message': 'Admin user already exists'})
            
            # Create admin
            admin = User(
                username='admin',
                email='admin@farmercredit.ai',
                role='ADMIN',
                full_name='System Administrator'
            )
            admin.set_password('admin123')  # Change this!
            
            db_session.add(admin)
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Admin user created',
                'username': 'admin',
                'password': 'admin123',
                'note': 'Please change the password immediately'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            db_session.close()

def get_dashboard_url(role):
    """Get appropriate dashboard URL based on role"""
    role_dashboards = {
        'ADMIN': '/admin_dashboard',
        'DEALER': '/dealer_dashboard',
        'BANK_OFFICER': '/bank_dashboard'
    }
    return role_dashboards.get(role, '/login')

# Protected route examples
def add_protected_routes(app, SessionLocal):
    """Add role-based protected routes"""
    
    @app.route('/admin_dashboard')
    @login_required
    @role_required(['ADMIN'])
    @audit_action('VIEW_ADMIN_DASHBOARD')
    def admin_dashboard():
        """Admin dashboard with full system access"""
        return render_template('admin_dashboard.html')
    
    @app.route('/dealer_dashboard')
    @login_required  
    @role_required(['DEALER', 'ADMIN'])
    @audit_action('VIEW_DEALER_DASHBOARD')
    def dealer_dashboard():
        """Dealer dashboard for village operations"""
        return render_template('dealer_app.html')
    
    @app.route('/bank_dashboard')
    @login_required
    @role_required(['BANK_OFFICER', 'ADMIN'])
    @audit_action('VIEW_BANK_DASHBOARD')
    def bank_dashboard():
        """Bank officer dashboard for credit analysis"""
        return render_template('bank_dashboard.html')