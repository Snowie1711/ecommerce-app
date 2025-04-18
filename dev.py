"""
Quick development server starter
Installs required dependencies and starts the server
"""
import subprocess
import sys
import os
import shutil

def check_and_install_package(package):
    """Check if a package is installed and install if not"""
    try:
        __import__(package)
        print(f"✅ {package} is already installed")
        return True
    except ImportError:
        print(f"⚠️ {package} is not installed. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed successfully")
            return True
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False

def check_and_install_npm_package(package):
    """Check if an npm package is installed and install if not"""
    # Check if npm is available
    if not shutil.which('npm'):
        print("❌ npm is not installed. Please install Node.js and npm.")
        return False
    
    # Check if package is already installed locally
    try:
        proc = subprocess.run(
            ["npm", "list", package], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            check=False
        )
        if package in proc.stdout:
            print(f"✅ {package} is already installed")
            return True
    except Exception:
        pass  # Continue to installation if check fails
    
    print(f"⚠️ {package} is not installed. Installing...")
    try:
        subprocess.check_call(["npm", "install", "--save-dev", package])
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package}")
        return False

def ensure_tailwind_config():
    """Ensure tailwind config has the forms plugin properly configured"""
    config_path = "tailwind.config.js"
    if not os.path.exists(config_path):
        print("⚠️ tailwind.config.js not found. Creating a default one with forms plugin...")
        with open(config_path, "w") as f:
            f.write("""module.exports = {
  content: [
    './templates/**/*.html',
    './static/**/*.js',
  ],
  theme: {
    extend: {},
  ],
  plugins: [
    require('@tailwindcss/forms'),
  ],
}""")
        print("✅ Created tailwind.config.js with forms plugin")
    else:
        # Check if forms plugin is in the config
        with open(config_path, "r") as f:
            config_content = f.read()
        if "@tailwindcss/forms" not in config_content:
            print("⚠️ @tailwindcss/forms plugin not found in tailwind.config.js. Please add it manually.")
            print("Add this to your plugins array: require('@tailwindcss/forms')")

if __name__ == "__main__":
    # Install necessary Python packages
    python_packages = ['eventlet', 'flask-socketio>=5.0.0']
    all_installed = all(check_and_install_package(p.split('>=')[0]) for p in python_packages)
    
    if not all_installed:
        print("❌ Some required Python packages could not be installed. Please install them manually.")
        sys.exit(1)
    
    # Install necessary npm packages
    npm_packages = ['tailwindcss', '@tailwindcss/forms']
    all_npm_installed = all(check_and_install_npm_package(p) for p in npm_packages)
    
    if not all_npm_installed:
        print("❌ Some required npm packages could not be installed. Please install them manually using npm.")
        print("Run: npm install tailwindcss @tailwindcss/forms --save-dev")
        
    # Ensure tailwind is configured properly
    ensure_tailwind_config()
    
    # Run the server
    print("🚀 Starting development server with WebSocket support...")
    os.environ['FLASK_DEBUG'] = '1'
    subprocess.call([sys.executable, "run.py"])
