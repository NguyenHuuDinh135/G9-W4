"""
Build script for monitoring Lambda deployment package.
Installs dependencies and copies source files into .build/ directory.
Cross-platform (Windows/Linux/Mac).
"""

import os
import shutil
import subprocess
import sys

BUILD_DIR = os.path.join(os.path.dirname(__file__), ".build")
SRC_DIR = os.path.dirname(__file__)

def main():
    # Clean and create build directory
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)

    # Install dependencies into build directory using manylinux wheels for AWS Lambda
    print("Installing dependencies...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "-r", os.path.join(SRC_DIR, "requirements.txt"),
        "-t", BUILD_DIR,
        "--platform", "manylinux2014_x86_64",
        "--only-binary=:all:",
        "--quiet", "--no-cache-dir",
    ])

    # Copy source files
    for filename in ["monitoring_api.py", "handler.py"]:
        src = os.path.join(SRC_DIR, filename)
        dst = os.path.join(BUILD_DIR, filename)
        shutil.copy2(src, dst)
        print(f"  Copied {filename}")

    print(f"Build complete: {BUILD_DIR}")

if __name__ == "__main__":
    main()
