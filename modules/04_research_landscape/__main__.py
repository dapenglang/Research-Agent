"""Standalone runner for Module 04."""
import os, sys
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from implementation import ResearchLandscapeModule

if __name__ == "__main__":
    config = {"output": {"paper_dir": "output/paper"}, "llm": {"type": "mock"}}
    try:
        instance = ResearchLandscapeModule()
        instance.load_config(config)
        print(f"[OK] Module 04 — {ResearchLandscapeModule.__name__} loaded successfully")
        print(f"     Module ID: {getattr(instance, 'MODULE_ID', 'N/A')}")
        print(f"     Module Name: {getattr(instance, 'MODULE_NAME', 'N/A')}")
    except Exception as e:
        print(f"[FAIL] Module 04: {e}")
