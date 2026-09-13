import sys
import os

# Add parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    print("Testing imports...")
    import utils
    print("Imported utils successfully!")
    
    from routes.dashboard import dashboard_bp
    print("Imported routes.dashboard successfully!")
    
    from routes.trend import trend_bp
    print("Imported routes.trend successfully!")
    
    from routes.regression import regression_bp
    print("Imported routes.regression successfully!")
    
    from routes.predictor import predictor_bp
    print("Imported routes.predictor successfully!")
    
    from routes.competitor import competitor_bp
    print("Imported routes.competitor successfully!")
    
    import main
    print("Imported main successfully!")
    
    print("\nAll imports loaded perfectly! The modularization has NO syntax or import errors.")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
