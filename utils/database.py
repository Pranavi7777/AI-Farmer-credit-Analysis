"""
🗄️ AI Farmer Credit Intelligence Platform
Database Configuration Module
SQLite + PostgreSQL Support
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
from dotenv import load_dotenv

# Load production environment consistently for CLI scripts and utilities.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / '.env.production', override=False)

Base = declarative_base()

class DatabaseConfig:
    """Database configuration for both SQLite and PostgreSQL"""
    
    def __init__(self, use_postgresql=False):
        self.use_postgresql = use_postgresql
        
        if use_postgresql:
            # PostgreSQL Configuration
            self.DATABASE_URL = self.get_postgresql_url()
        else:
            # SQLite Configuration (Default)
            self.DATABASE_URL = "sqlite:///farmer_credit_enterprise.db"
    
    def get_postgresql_url(self):
        """Get PostgreSQL connection URL"""
        # Check for full DATABASE_URL first (for cloud deployment)
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # Supabase requires SSL; append when missing.
            if 'supabase.com' in database_url and 'sslmode=' not in database_url:
                separator = '&' if '?' in database_url else '?'
                database_url = f"{database_url}{separator}sslmode=require"
            return database_url
        
        # Fallback to individual credentials (for local development)
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'Alekhya')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'farmer_credit_ai')
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    def create_engine(self):
        """Create database engine"""
        if self.use_postgresql:
            connect_args = {
                'connect_timeout': 10
            }

            # Keep startup responsive when remote DB is slow.
            connect_args['options'] = '-c statement_timeout=15000'

            engine_kwargs = {
                'pool_pre_ping': True,
                'pool_recycle': 300,
                'connect_args': connect_args
            }

            if 'pooler.supabase.com' in self.DATABASE_URL:
                # Supabase pooler behaves better without app-side pooling.
                engine_kwargs['poolclass'] = NullPool
            else:
                engine_kwargs['pool_size'] = 10
                engine_kwargs['max_overflow'] = 20

            if 'supabase.com' in self.DATABASE_URL:
                # Avoid psycopg2 hstore OID probe during connect on some poolers.
                engine_kwargs['use_native_hstore'] = False

            engine = create_engine(self.DATABASE_URL, **engine_kwargs)
            print(f"✅ Connected to PostgreSQL database")
        else:
            engine = create_engine(self.DATABASE_URL, connect_args={'check_same_thread': False})
            print(f"✅ Connected to SQLite database")
        
        return engine

# Database Models
class Farmer(Base):
    __tablename__ = 'farmers'
    
    farmer_unique_id = Column(String(50), primary_key=True)
    mobile = Column(String(15), nullable=False)
    village_code = Column(String(20), nullable=False)
    farmer_name = Column(String(100))
    total_purchases = Column(Float, default=0.0)
    total_credit_taken = Column(Float, default=0.0)
    total_payments = Column(Float, default=0.0)
    current_outstanding = Column(Float, default=0.0)
    last_transaction_date = Column(String(50))
    credit_score = Column(Integer, default=0)
    risk_level = Column(String(20), default='UNKNOWN')
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    
    # Relationship
    transactions = relationship("Transaction", back_populates="farmer")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_unique_id = Column(String(50), ForeignKey('farmers.farmer_unique_id'))
    transaction_date = Column(String(50))
    purchase_amount = Column(Float)
    credit_amount = Column(Float)
    payment_amount = Column(Float)
    crop_season = Column(String(20))
    delay_days = Column(Integer, default=0)
    transaction_type = Column(String(20))
    dealer_id = Column(String(50))
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    
    # Relationship
    farmer = relationship("Farmer", back_populates="transactions")

class Village(Base):
    __tablename__ = 'villages'
    
    village_code = Column(String(20), primary_key=True)
    village_name = Column(String(100))
    risk_index = Column(Float, default=0.8)
    total_farmers = Column(Integer, default=0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())

# 🔐 Enterprise Authentication Models
class User(Base):
    """User authentication and role management"""
    __tablename__ = 'users'
    
    user_id = Column(String(50), primary_key=True, default=lambda: f"USER{secrets.randbelow(100000):05d}")
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False)  # ADMIN, DEALER, BANK_OFFICER
    village_code = Column(String(20))  # For dealers
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def get_permissions(self):
        """Get role-based permissions"""
        permissions = {
            'ADMIN': ['view_all', 'add_dealer', 'village_analytics', 'system_stats'],
            'DEALER': ['add_farmer', 'add_transaction', 'view_village_farmers'],
            'BANK_OFFICER': ['search_farmer', 'view_credit_score', 'export_reports']
        }
        return permissions.get(self.role, [])

class AuditLog(Base):
    """Track all system actions for security"""
    __tablename__ = 'audit_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)  # LOGIN, ADD_FARMER, VIEW_SCORE
    resource = Column(String(100))  # farmer_id, transaction_id
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(50))
    details = Column(String(500))

class UserSession(Base):
    """Manage active user sessions"""
    __tablename__ = 'user_sessions'
    
    session_id = Column(String(100), primary_key=True)
    user_id = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(50))
    is_active = Column(Boolean, default=True)


class DataLakeRecord(Base):
    """Store raw CSV rows from data folder for Supabase-backed archival/sync."""
    __tablename__ = 'data_lake_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(255), nullable=False)
    record_hash = Column(String(64), nullable=False)
    payload_json = Column(Text, nullable=False)
    imported_at = Column(String(50), default=lambda: datetime.now().isoformat())

def init_database(use_postgresql=False):
    """Initialize database with tables"""
    config = DatabaseConfig(use_postgresql)
    engine = config.create_engine()
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Initialize sample villages if not exist
    sample_villages = [
        ('VILL001', 'Rampur', 0.85),
        ('VILL002', 'Krishnaganj', 0.92),
        ('VILL003', 'Shaktigarh', 0.75),
        ('VILL004', 'Dhanipur', 0.88),
        ('VILL005', 'Sultanpur', 0.79)
    ]
    
    for village_code, village_name, risk_index in sample_villages:
        existing = session.query(Village).filter_by(village_code=village_code).first()
        if not existing:
            village = Village(
                village_code=village_code,
                village_name=village_name,
                risk_index=risk_index
            )
            session.add(village)
    
    session.commit()
    session.close()
    
    print(f"🗄️ Database initialized successfully!")
    print(f"📊 Sample villages created")
    
    # Create demo users if they don't exist
    _create_demo_users(engine, Session)
    
    # Create sample farmer data  
    _create_sample_farmers(engine, Session)
    
    return engine, Session

def _create_demo_users(engine, Session):
    """Create demo users for testing if they don't exist"""
    session = Session()
    
    try:
        # Check if any users exist
        user_count = session.query(User).count()
        if user_count > 0:
            return  # Users already exist
        
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
                'username': 'bank1',
                'email': 'bank1@farmercredit.ai',
                'password': 'bank123',
                'role': 'BANK_OFFICER',
                'full_name': 'Bank Officer',
                'village_code': None
            }
        ]
        
        created_users = []
        for user_data in demo_users:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                full_name=user_data['full_name'],
                village_code=user_data['village_code']
            )
            user.set_password(user_data['password'])
            session.add(user)
            created_users.append(user_data['username'])
        
        session.commit()
        print(f"👤 Demo users created: {', '.join(created_users)}")
        
    except Exception as e:
        session.rollback()
        print(f"⚠️ Could not create demo users: {e}")
    finally:
        session.close()

def _create_sample_farmers(engine, Session):
    """Create sample farmer data for testing"""
    session = Session()
    
    try:
        # Check if farmers already exist
        farmer_count = session.query(Farmer).count()
        if farmer_count > 0:
            return  # Sample farmers already exist
        
        # Sample farmers based on the CSV data 
        sample_farmers = [
            {
                'farmer_unique_id': '9876543210VILL001',
                'mobile': '9876543210',
                'village_code': 'VILL001',
                'farmer_name': 'Ramesh Kumar',
                'total_purchases': 50000,
                'current_outstanding': 0,
                'credit_score': 785,
                'risk_level': 'LOW RISK'
            },
            {
                'farmer_unique_id': '9876543211VILL001', 
                'mobile': '9876543211',
                'village_code': 'VILL001',
                'farmer_name': 'Suresh Patel',
                'total_purchases': 70000,
                'current_outstanding': 20000,
                'credit_score': 425,
                'risk_level': 'HIGH RISK'
            },
            {
                'farmer_unique_id': '9876543212VILL002',
                'mobile': '9876543212', 
                'village_code': 'VILL002',
                'farmer_name': 'Raj Singh',
                'total_purchases': 40000,
                'current_outstanding': 0,
                'credit_score': 798,
                'risk_level': 'LOW RISK'
            },
            {
                'farmer_unique_id': '9876543213VILL002',
                'mobile': '9876543213',
                'village_code': 'VILL002', 
                'farmer_name': 'Mohan Reddy',
                'total_purchases': 80000,
                'current_outstanding': 40000,
                'credit_score': 356,
                'risk_level': 'HIGH RISK'
            },
            {
                'farmer_unique_id': '9876543215VILL003',
                'mobile': '9876543215',
                'village_code': 'VILL003',
                'farmer_name': 'Vijay Gupta', 
                'total_purchases': 90000,
                'current_outstanding': 35000,
                'credit_score': 412,
                'risk_level': 'HIGH RISK'
            },
            {
                'farmer_unique_id': '9876543218VILL003',
                'mobile': '9876543218',
                'village_code': 'VILL003',
                'farmer_name': 'Deepak Shah',
                'total_purchases': 52000,
                'current_outstanding': 0,
                'credit_score': 721,
                'risk_level': 'MEDIUM RISK'
            }
        ]
        
        created_farmers = []
        for farmer_data in sample_farmers:
            farmer = Farmer(
                farmer_unique_id=farmer_data['farmer_unique_id'],
                mobile=farmer_data['mobile'],
                village_code=farmer_data['village_code'],
                farmer_name=farmer_data['farmer_name'],
                total_purchases=farmer_data['total_purchases'],
                current_outstanding=farmer_data['current_outstanding'],
                credit_score=farmer_data['credit_score'],
                risk_level=farmer_data['risk_level']
            )
            session.add(farmer)
            created_farmers.append(farmer_data['farmer_name'])
        
        session.commit()
        print(f"🌾 Sample farmers created: {len(created_farmers)} farmers across villages")
        
    except Exception as e:
        session.rollback()
        print(f"⚠️ Could not create sample farmers: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # Test database setup
    print("🧪 Testing Database Configuration...")
    
    # Test SQLite
    print("\n1. Testing SQLite...")
    engine_sqlite, Session_sqlite = init_database(use_postgresql=False)
    
    # Test PostgreSQL (uncomment when PostgreSQL is available)
    print("\n2. Testing PostgreSQL...")
    try:
        engine_pg, Session_pg = init_database(use_postgresql=True)
        print("✅ PostgreSQL connection successful!")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("💡 Run 'python setup_database.py' to set up PostgreSQL database")
    
    print("\n✅ Database testing complete!")