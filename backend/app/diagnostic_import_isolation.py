"""
Import isolation diagnostic to find the module causing PyTorch DLL failure.
Tests each HireLens import in a fresh subprocess to identify the conflicting module.
"""
import subprocess
import sys
import os

# Modules to test in import order
MODULES_TO_TEST = [
    ("app.core.config", "Configuration module"),
    ("app.schemas.common", "Common schemas"),
    ("app.db.database", "Database initialization"),
    ("app.db.base", "Database base models"),
    ("app.models.job", "Job model"),
    ("app.models.resume", "Resume model"),
    ("app.models.screening_result", "Screening result model"),
    ("app.repositories.job_repository", "Job repository"),
    ("app.repositories.resume_repository", "Resume repository"),
    ("app.repositories.screening_repository", "Screening repository"),
    ("app.services.skill_service", "Skill service"),
    ("app.services.job_analysis_service", "Job analysis service"),
    ("app.services.evidence_extraction_service", "Evidence extraction"),
    ("app.services.semantic_matching_service", "Semantic matching"),
    ("app.services.scoring_service", "Scoring service"),
    ("app.services.matching_service", "Matching service"),
    ("app.utils.text_processor", "Text processor"),
    ("app.api.routes.resumes", "Resumes router"),
    ("app.api.routes.jobs", "Jobs router"),
    ("app.api.routes.matching", "Matching router"),
    ("app.api.routes.reports", "Reports router"),
]


def test_torch_in_subprocess():
    """Test torch import in a fresh subprocess."""
    script = """
import sys
try:
    import torch
    print(f"SUCCESS: torch {torch.__version__}")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    return result.returncode == 0, result.stdout + result.stderr


def test_module_import(module_name):
    """Test importing a module in a fresh subprocess."""
    script = f"""
import sys
import os
os.chdir(r"{os.getcwd()}")

# Add backend to path
sys.path.insert(0, r"{os.getcwd()}")

try:
    import {module_name}
    print(f"SUCCESS: {module_name} imported")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {module_name} - {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    return result.returncode == 0, result.stdout + result.stderr


def test_module_then_torch(module_name):
    """Test importing a module, then test torch in a fresh subprocess."""
    # First, import the module
    import_success, import_output = test_module_import(module_name)
    
    if not import_success:
        return False, f"Module import failed: {import_output}"
    
    # Then test torch in a fresh subprocess
    torch_success, torch_output = test_torch_in_subprocess()
    
    return torch_success, f"Torch after {module_name}: {torch_output}"


def main():
    print("=" * 80)
    print("IMPORT ISOLATION DIAGNOSTIC")
    print("=" * 80)
    
    # Baseline: test torch without any HireLens imports
    print("\n[BASELINE] Testing torch import without HireLens modules...")
    baseline_success, baseline_output = test_torch_in_subprocess()
    print(f"Baseline result: {'SUCCESS' if baseline_success else 'FAILED'}")
    if not baseline_success:
        print(baseline_output)
        print("\nERROR: Baseline torch import failed. Check environment.")
        return
    
    print("\n" + "=" * 80)
    print("TESTING EACH MODULE INDIVIDUALLY")
    print("=" * 80)
    
    cumulative_imports = []
    failing_module = None
    
    for module_name, description in MODULES_TO_TEST:
        print(f"\n[{module_name}] {description}")
        
        # Test module import
        import_success, import_output = test_module_import(module_name)
        if not import_success:
            print(f"  ❌ Module import failed: {import_output}")
            failing_module = module_name
            break
        
        print(f"  ✓ Module imported successfully")
        
        # Test torch after this module
        torch_success, torch_output = test_module_then_torch(module_name)
        if not torch_success:
            print(f"  ❌ Torch import FAILED after this module")
            print(f"  Output: {torch_output}")
            failing_module = module_name
            break
        else:
            print(f"  ✓ Torch still works after this module")
        
        cumulative_imports.append(module_name)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if failing_module:
        print(f"\n❌ FAILING MODULE IDENTIFIED: {failing_module}")
        print(f"\nModules imported successfully before failure:")
        for m in cumulative_imports:
            print(f"  - {m}")
        print(f"\nFailing module: {failing_module}")
    else:
        print("\n✓ All modules tested successfully")
        print("✓ Torch import works after all individual module imports")
        print("\nThis suggests the issue may be from:")
        print("  - Import order/combination effects")
        print("  - Multiple imports in the same process")
        print("  - Uvicorn-specific initialization")


if __name__ == "__main__":
    main()
