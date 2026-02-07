import sys
import os
import shutil

print(f"Python Executable: {sys.executable}")
print(f"CWD: {os.getcwd()}")
print(f"Path: {os.environ.get('PATH')}")

# Try to find python in path
python_path = shutil.which("python")
print(f"Which python: {python_path}")

try:
    import pandas
    print(f"Pandas version: {pandas.__version__}")
except ImportError:
    print("Pandas not installed")
