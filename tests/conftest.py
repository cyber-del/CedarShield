import os
import sys
import importlib.util
import pytest

# Ensure root directory and src directory are on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Set dummy AWS credentials for safe unit and moto testing
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
os.environ.setdefault("AWS_REGION_NAME", "ap-southeast-2")
os.environ.setdefault("AUDIT_TABLE_NAME", "cedarshield-audit-log")
os.environ.setdefault("DYNAMODB_TABLE", "cedarshield-audit-log")


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: marks tests as requiring real AWS credentials and cloud infrastructure"
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        # Automatically mark any test located under tests/live/ as @pytest.mark.live
        fspath_str = str(item.fspath).replace("\\", "/")
        if "/tests/live/" in fspath_str:
            item.add_marker(pytest.mark.live)


def load_lambda_module(function_name: str):
    """
    Helper to dynamically import Lambda modules located in src/functions/<function_name>/app.py.
    This accommodates hyphenated directory names like diagnose-denial and generate-patch.
    """
    fpath = os.path.join(SRC_DIR, "functions", function_name, "app.py")
    if not os.path.isfile(fpath):
        raise FileNotFoundError(f"Lambda handler not found at {fpath}")
    mod_name = function_name.replace("-", "_")
    spec = importlib.util.spec_from_file_location(mod_name, fpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
