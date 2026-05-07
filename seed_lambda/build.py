import os
import shutil
import subprocess
import sys

BUILD_DIR = os.path.join(os.path.dirname(__file__), ".build")
SRC_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(SRC_DIR)), "data_package", "structured_data")

def main():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)

    # Install dependencies into build directory using manylinux wheels
    print("Installing psycopg2-binary for AWS Lambda...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "-r", os.path.join(SRC_DIR, "requirements.txt"),
        "-t", BUILD_DIR,
        "--platform", "manylinux2014_x86_64",
        "--only-binary=:all:",
        "--quiet", "--no-cache-dir",
    ])

    # Copy handler
    shutil.copy2(os.path.join(SRC_DIR, "handler.py"), os.path.join(BUILD_DIR, "handler.py"))
    
    # Copy data directory (CSV files)
    build_data_dir = os.path.join(BUILD_DIR, "data")
    if os.path.exists(build_data_dir):
        shutil.rmtree(build_data_dir)
    shutil.copytree(DATA_DIR, build_data_dir)

    print(f"Seed Lambda Build complete: {BUILD_DIR}")

if __name__ == "__main__":
    main()
