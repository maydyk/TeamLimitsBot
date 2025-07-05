# Access to teamlimits packages
import sys
import subprocess
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))


if __name__ == "__main__":
    # Run all nested tests.
    nested_tests = [
        "test_camel_to_snake.py",
        "test_coerce_list.py",
        "test_even_hex.py"
    ]

    current_dir = Path(__file__).parent

    for test_file in nested_tests:
        subprocess.run([sys.executable, test_file], cwd=current_dir)


