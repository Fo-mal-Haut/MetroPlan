#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
try:
    import backend.app
    print("✅ Flask app imported successfully")
    print(f"✅ Flask routes: {[str(r) for r in backend.app.app.url_map.iter_rules()]}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
