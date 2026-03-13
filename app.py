"""
🚀 AI Farmer Credit Intelligence Platform
Simple Application Launcher
"""

import os
import sys

def main():
    """Launch the Flask application"""
    print("🌾 AI FARMER CREDIT INTELLIGENCE PLATFORM")
    print("=" * 60)
    print("🚀 Starting Flask application...")
    print("📊 Access at: http://localhost:5000")
    print("🔐 Demo login: admin/admin123, dealer1/dealer123, bank1/bank123")
    print("=" * 60)
    
    # Set environment variables  
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = 'true'
    
    try:
        # Import and run Flask app
        from api.app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Please install requirements: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

if __name__ == "__main__":
    main()