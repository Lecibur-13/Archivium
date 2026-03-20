#!/usr/bin/env python3
"""
Build script to create Archivium executable
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

def clean_build():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__', '*.spec']
    for dir_name in dirs_to_clean:
        if dir_name == '*.spec':
            # Remove any .spec files
            import glob
            for spec_file in glob.glob('*.spec'):
                try:
                    os.remove(spec_file)
                    print(f"✓ Removed spec file: {spec_file}")
                except Exception as e:
                    print(f"⚠️ Could not remove {spec_file}: {e}")
        elif os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ Cleaned directory: {dir_name}")

def build_executable():
    """Build executable using PyInstaller"""
    print("🔨 Building executable...")
    
    # PyInstaller configuration
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',                    # Single executable file
        '--windowed',                   # No console window
        '--name=Archivium',             # Executable name
        '--icon=img/logo.ico',          # Executable icon
        '--add-data=img;img',           # Include images folder
        '--hidden-import=customtkinter', # Required hidden imports
        '--hidden-import=tkinter',
        '--hidden-import=PIL',
        '--clean',                      # Clean cache
        'main.py'                       # Main file
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Executable created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating executable: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def create_release_folder():
    """Create release folder with necessary files"""
    release_dir = Path("release")
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    release_dir.mkdir()
    
    # Copy executable
    exe_path = Path("dist/Archivium.exe")
    if exe_path.exists():
        shutil.copy2(exe_path, release_dir / "Archivium.exe")
        print("✓ Executable copied to release folder")
    
    # Copy README
    if Path("README.md").exists():
        shutil.copy2("README.md", release_dir / "README.md")
        print("✓ README copied to release folder")
    
    print(f"📦 Release prepared at: {release_dir.absolute()}")

def cleanup_build_artifacts():
    """Clean up build artifacts using PowerShell command"""
    print("🧹 Cleaning up build artifacts...")
    try:
        # Use PowerShell to remove build and dist directories
        cmd = ["powershell", "-Command", "Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue"]
        subprocess.run(cmd, check=False)  # Don't fail if directories don't exist
        
        # Also remove any .spec files
        import glob
        for spec_file in glob.glob('*.spec'):
            try:
                os.remove(spec_file)
                print(f"✓ Removed spec file: {spec_file}")
            except Exception as e:
                print(f"⚠️ Could not remove {spec_file}: {e}")
        
        print("✓ Build artifacts cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not clean build artifacts: {e}")

def main():
    """Main build script function"""
    print("🚀 Starting build process for Archivium v1.0.0")
    print("=" * 50)
    
    # Verify we're in the correct directory
    if not Path("main.py").exists():
        print("❌ Error: main.py not found. Run from project directory.")
        sys.exit(1)
    
    # Clean previous builds
    clean_build()
    
    # Build executable
    if not build_executable():
        print("❌ Executable build failed")
        sys.exit(1)
    
    # Create release folder
    create_release_folder()
    
    # Clean up build artifacts
    cleanup_build_artifacts()
    
    print("=" * 50)
    print("✅ Build completed successfully!")
    print("📁 Find your executable at: release/Archivium.exe")

if __name__ == "__main__":
    main()