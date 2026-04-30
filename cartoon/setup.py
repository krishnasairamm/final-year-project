import subprocess
import sys
import os

def install_dependencies():
    print("==========================================")
    print(" Installing Dependencies for Cartoon App")
    print("==========================================")
    
    requirements_file = "requirements.txt"
    
    if not os.path.exists(requirements_file):
        print(f"Error: {requirements_file} not found.")
        sys.exit(1)
        
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("\n✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error installing dependencies: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_dependencies()
    print("\nSetup complete. You can now run 'python run.py' to start the application.")
