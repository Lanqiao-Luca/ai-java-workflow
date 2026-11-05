"""Run the fixed structural-check benchmark once; print real observations."""
from pathlib import Path
import json
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.capability_benchmark import run_benchmark


if __name__ == '__main__':
    print(json.dumps(run_benchmark(), ensure_ascii=False, indent=2))
