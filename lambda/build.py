import os
import shutil
import subprocess
import sys

BUILD_DIR = os.path.join(os.path.dirname(__file__), ".build")
SRC_DIR = os.path.dirname(__file__)

def main():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)

    print("Installing requirements for AWS Lambda...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "-r", os.path.join(SRC_DIR, "requirements.txt"),
        "-t", BUILD_DIR,
        "--platform", "manylinux2014_x86_64",
        "--python-version", "3.12",
        "--only-binary=:all:",
        "--quiet", "--no-cache-dir",
    ])

    # Copy lambda handlers
    shutil.copy2(os.path.join(SRC_DIR, "lambda_function.py"), os.path.join(BUILD_DIR, "lambda_function.py"))
    shutil.copy2(os.path.join(SRC_DIR, "action_group_function.py"), os.path.join(BUILD_DIR, "action_group_function.py"))

    print(f"Lambda Build complete: {BUILD_DIR}")

if __name__ == "__main__":
    main()
