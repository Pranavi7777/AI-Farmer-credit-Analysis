"""
🔐 Initialize Demo Users for Testing
Creates admin, dealer, and bank users for system testing
"""

import os
from sqlalchemy.orm import sessionmaker
from utils.database import init_database, User
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_demo_users(reset_existing=False):
    """Create demo users for authentication testing.

    If reset_existing is True, existing demo users are updated with default
    credentials and profile fields.
    """
    try:
        # Use production environment 
        from dotenv import load_dotenv
        load_dotenv('.env.production')
        
        # Initialize database connection
        USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'true').lower() == 'true'
        
        try:
            engine, SessionLocal = init_database(use_postgresql=USE_POSTGRESQL)
            print("✅ Connected to PostgreSQL database")
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            if USE_POSTGRESQL:
                print("🔄 Falling back to SQLite...")
                engine, SessionLocal = init_database(use_postgresql=False)
                print("✅ Connected to SQLite database")
            else:
                raise e
        
        # Create session
        db_session = SessionLocal()
        
        # Demo users to create
        demo_users = [
            {
                'username': 'admin',
                'email': 'admin@farmercredit.ai',
                'password': 'admin123',
                'role': 'ADMIN',
                'full_name': 'System Administrator',
                'village_code': None
            },
            {
                'username': 'dealer1',
                'email': 'dealer1@farmercredit.ai',
                'password': 'dealer123',
                'role': 'DEALER',
                'full_name': 'Village Dealer 1',
                'village_code': 'VILL001'
            },
            {
                'username': 'dealer2',
                'email': 'dealer2@farmercredit.ai',
                'password': 'dealer123',
                'role': 'DEALER',
                'full_name': 'Village Dealer 2',
                'village_code': 'VILL002'
            },
            {
                'username': 'bank1',
                'email': 'bank1@farmercredit.ai',
                'password': 'bank123',
                'role': 'BANK_OFFICER',
                'full_name': 'Bank Officer',
                'village_code': None
            }
        ]
        
        print("🔐 Initializing Demo Users...")
        print("=" * 40)
        
        created_users = []
        reset_users = []
        for user_data in demo_users:
            # Check if user already exists
            existing = db_session.query(User).filter_by(username=user_data['username']).first()
            
            if existing:
                if reset_existing:
                    existing.email = user_data['email']
                    existing.role = user_data['role']
                    existing.full_name = user_data['full_name']
                    existing.village_code = user_data['village_code']
                    existing.is_active = True
                    existing.set_password(user_data['password'])
                    reset_users.append(user_data)
                    print(f"🔄 Reset credentials for {user_data['username']}")
                else:
                    print(f"⚠️  User {user_data['username']} already exists")
                continue
            
            # Create new user
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                full_name=user_data['full_name'],
                village_code=user_data['village_code']
            )
            user.set_password(user_data['password'])
            
            db_session.add(user)
            created_users.append(user_data)
            print(f"✅ Created {user_data['role']} user: {user_data['username']}")
        
        if created_users or reset_users:
            db_session.commit()
            if created_users:
                print(f"\n🎉 Successfully created {len(created_users)} demo users!")
            if reset_users:
                print(f"\n🔐 Reset passwords for {len(reset_users)} existing demo users!")
            print("\n📋 Login Credentials:")
            print("=" * 30)
            for user in created_users + reset_users:
                print(f"👤 {user['role']}: {user['username']} / {user['password']}")
                if user['village_code']:
                    print(f"   🏘️  Village: {user['village_code']}")
                    
        else:
            print("ℹ️  All demo users already exist")
        
        db_session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating demo users: {e}")
        return False

if __name__ == "__main__":
    print("🔐 AI FARMER CREDIT INTELLIGENCE PLATFORM")
    print("🔧 Demo User Initialization")
    print("=" * 50)
    
    reset_existing = os.getenv('RESET_DEMO_PASSWORDS', 'false').lower() == 'true'
    if reset_existing:
        print("🔄 Reset mode enabled: existing demo user passwords will be updated")

    success = create_demo_users(reset_existing=reset_existing)
    
    if success:
        print("\n✅ Demo users ready for testing!")
        print("🌐 Start the server with: python api/app.py")
    else:
        print("\n❌ Failed to create demo users")
        exit(1)