import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.module_14_reviewer_loop.implementation import ReviewerLoopModule
from modules.module_14_reviewer_loop.schema import Module14Input

if __name__ == "__main__":
    module = ReviewerLoopModule()
    input_data = Module14Input()
    result = module.execute(input_data)
    print(f"Success: {result.success}")
    print(f"Decision: {result.decision}")
