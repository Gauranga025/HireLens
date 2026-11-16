"""
Cumulative import isolation diagnostic to find PyTorch DLL failure.
Tests cumulative imports in the same process to identify the failing combination.
"""
import subprocess
import sys
import os

# Get the venv Python executable
VENV_PYTHON = os.path.join(os.path.dirname(sys.executable), "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

# Use the backend directory as the working directory (parent of app directory)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Real import order based on app/main.py and its dependencies
# These are imported when app.main is loaded
CUMULATIVE_IMPORTS = [
    # Level 1: Direct imports from app/main.py
    "app.core.config",
    "app.schemas.common",
    "app.db.database",
    "app.api.routes.resumes",
    "app.api.routes.jobs",
    "app.api.routes.matching",
    "app.api.routes.reports",
]


def test_cumulative_imports(prefix_modules):
    """Test importing a prefix of modules in the same process, then torch."""
    modules_str = ", ".join(prefix_modules)
    modules_list = str(prefix_modules)
    script = f"""
import sys
import os
os.chdir(r"{BACKEND_DIR}")

# Add backend to path
sys.path.insert(0, r"{BACKEND_DIR}")

print(f"[TEST] Importing modules: {modules_str}")

# Import each module in sequence
for module in {modules_list}:
    try:
        __import__(module)
        print(f"  [OK] Imported {{module}}")
    except Exception as e:
        print(f"  [FAIL] Failed to import {{module}}: {{e}}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Now test torch
print(f"[TEST] Attempting import torch after importing {{len({modules_list})}} modules...")
try:
    import torch
    print(f"  [OK] SUCCESS: torch {{torch.__version__}}")
    sys.exit(0)
except Exception as e:
    print(f"  [FAIL] FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    result = subprocess.run(
        [VENV_PYTHON, "-c", script],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
        encoding="utf-8",
        errors="replace"
    )
    return result.returncode == 0, result.stdout + result.stderr


def test_torch_before_app():
    """Test importing torch before app.main."""
    script = f"""
import sys
import os
os.chdir(r"{BACKEND_DIR}")
sys.path.insert(0, r"{BACKEND_DIR}")

print("[TEST] Importing torch first...")
try:
    import torch
    print(f"  [OK] SUCCESS: torch {{torch.__version__}}")
except Exception as e:
    print(f"  [FAIL] FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Now importing app.main...")
try:
    import app.main
    print(f"  [OK] SUCCESS: app.main imported")
except Exception as e:
    print(f"  [FAIL] FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Verifying torch still works after app.main...")
try:
    import torch
    print(f"  [OK] SUCCESS: torch still works, {{torch.__version__}}")
    sys.exit(0)
except Exception as e:
    print(f"  [FAIL] FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    result = subprocess.run(
        [VENV_PYTHON, "-c", script],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
        encoding="utf-8",
        errors="replace"
    )
    return result.returncode == 0, result.stdout + result.stderr


def test_app_before_torch():
    """Test importing app.main before torch."""
    script = f"""
import sys
import os
os.chdir(r"{BACKEND_DIR}")
sys.path.insert(0, r"{BACKEND_DIR}")

print("[TEST] Importing app.main first...")
try:
    import app.main
    print(f"  [OK] SUCCESS: app.main imported")
except Exception as e:
    print(f"  [FAIL] FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Now importing torch...")
try:
    import torch
    print(f"  [OK] SUCCESS: torch {{torch.__version__}}")
    sys.exit(0)
except Exception as e:
    print(f"  [FAIL] FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    result = subprocess.run(
        [VENV_PYTHON, "-c", script],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
        encoding="utf-8",
        errors="replace"
    )
    return result.returncode == 0, result.stdout + result.stderr


def capture_environment_after_imports(prefix_modules):
    """Capture environment changes after importing modules."""
    modules_list = str(prefix_modules)
    script = f"""
import sys
import os
os.chdir(r"{BACKEND_DIR}")
sys.path.insert(0, r"{BACKEND_DIR}")

print("[ENV] Initial state:")
print(f"  PATH: {{os.environ.get('PATH', 'NOT_SET')[:200]}}...")
print(f"  CWD: {{os.getcwd()}}")
print(f"  sys.path[0]: {{sys.path[0]}}")

# Import modules
for module in {modules_list}:
    __import__(module)

print(f"[ENV] After importing {{len({modules_list})}} modules:")
print(f"  PATH: {{os.environ.get('PATH', 'NOT_SET')[:200]}}...")
print(f"  CWD: {{os.getcwd()}}")
print(f"  sys.path[0]: {{sys.path[0]}}")

# Check for native library modules
native_modules = [k for k in sys.modules.keys() if any(x in k.lower() for x in ['numpy', 'torch', 'sklearn', 'scipy', 'cv2', 'sqlalchemy', 'asyncpg'])]
print(f"  Native modules loaded: {{len(native_modules)}}")
for m in native_modules[:10]:  # First 10
    print(f"    - {{m}}")
"""
    result = subprocess.run(
        [VENV_PYTHON, "-c", script],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
        encoding="utf-8",
        errors="replace"
    )
    return result.stdout + result.stderr


def main():
    print("=" * 80)
    print("CUMULATIVE IMPORT ISOLATION DIAGNOSTIC")
    print("=" * 80)

    # Test 1: torch before app.main
    print("\n" + "=" * 80)
    print("TEST 1: Import torch BEFORE app.main")
    print("=" * 80)
    success, output = test_torch_before_app()
    print(f"Result: {'✓ SUCCESS' if success else '❌ FAILED'}")
    print(output)

    # Test 2: app.main before torch
    print("\n" + "=" * 80)
    print("TEST 2: Import app.main BEFORE torch")
    print("=" * 80)
    success, output = test_app_before_torch()
    print(f"Result: {'✓ SUCCESS' if success else '❌ FAILED'}")
    print(output)

    # Test 3: Cumulative imports
    print("\n" + "=" * 80)
    print("TEST 3: Cumulative import isolation")
    print("=" * 80)
    
    failing_prefix = None
    for i in range(1, len(CUMULATIVE_IMPORTS) + 1):
        prefix = CUMULATIVE_IMPORTS[:i]
        print(f"\n--- Testing prefix of {i} modules: {', '.join(prefix)} ---")
        success, output = test_cumulative_imports(prefix)
        print(f"Result: {'✓ SUCCESS' if success else '❌ FAILED'}")
        if not success:
            print(output)
            failing_prefix = prefix
            break
        else:
            print("  (torch imported successfully)")

    # Test 4: Environment capture
    print("\n" + "=" * 80)
    print("TEST 4: Environment changes after imports")
    print("=" * 80)
    if failing_prefix:
        print(f"Capturing environment after failing prefix: {', '.join(failing_prefix)}")
        env_output = capture_environment_after_imports(failing_prefix)
    else:
        print("Capturing environment after all modules")
        env_output = capture_environment_after_imports(CUMULATIVE_IMPORTS)
    print(env_output)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    print("\nImport order tested:")
    for i, module in enumerate(CUMULATIVE_IMPORTS, 1):
        print(f"  {i}. {module}")
    
    if failing_prefix:
        print(f"\n❌ FAILING PREFIX: {', '.join(failing_prefix)}")
        print(f"\nThis is the smallest cumulative import combination that breaks torch.")
    else:
        print("\n✓ All cumulative import prefixes tested successfully")
        print("The issue may require the full app.main import or a different combination.")


if __name__ == "__main__":
    main()
