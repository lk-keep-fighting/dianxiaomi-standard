#!/usr/bin/env python3
"""
Script Expiration Management Utility
Used to manage the expiration settings and reset the timer for distribution
"""

import os
import time
import datetime
import sys
import argparse


def reset_expiration():
    """Reset the expiration timer by removing the timestamp file"""
    timestamp_file = ".script_start_time"
    
    if os.path.exists(timestamp_file):
        os.remove(timestamp_file)
        print("✅ Expiration timer has been reset")
        print("🔄 The script will run for another 8 hours from the next execution")
    else:
        print("ℹ️  No expiration timer found (script hasn't been run yet)")


def check_expiration_status():
    """Check the current expiration status"""
    timestamp_file = ".script_start_time"
    
    if not os.path.exists(timestamp_file):
        print("📊 Status: Script hasn't been run yet")
        return
    
    try:
        with open(timestamp_file, 'r') as f:
            start_time = float(f.read().strip())
        
        current_time = time.time()
        elapsed_time = current_time - start_time
        expiration_seconds = 8 * 60 * 60  # 8 hours
        remaining_time = expiration_seconds - elapsed_time
        
        print("📊 Script Expiration Status")
        print("=" * 40)
        print(f"🚀 First run time: {datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Current time: {datetime.datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏳ Elapsed time: {elapsed_time/3600:.1f} hours")
        
        if remaining_time > 0:
            print(f"✅ Status: ACTIVE")
            print(f"⏰ Remaining time: {remaining_time/3600:.1f} hours")
            print(f"🔚 Expires at: {datetime.datetime.fromtimestamp(start_time + expiration_seconds).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"❌ Status: EXPIRED")
            print(f"⚠️  Expired {abs(remaining_time)/3600:.1f} hours ago")
            
    except Exception as e:
        print(f"❌ Error reading expiration data: {e}")


def create_distribution_package():
    """Create a clean distribution package without expiration history"""
    import shutil
    import tempfile
    
    print("📦 Creating distribution package...")
    
    # Files to exclude from distribution
    exclude_files = [
        ".script_start_time",
        "auth_state.json", 
        "__pycache__",
        ".git",
        "EXPIRATION_GUIDE.md",
        "manage_expiration.py",
        "*.pyc",
        ".DS_Store",
        "screenshots/",
        "logs/"
    ]
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        dist_dir = os.path.join(temp_dir, "digital_chief_automation_dist")
        
        # Copy all files except excluded ones
        current_dir = os.getcwd()
        
        def should_exclude(path):
            for exclude in exclude_files:
                if exclude in path or path.endswith('.pyc'):
                    return True
            return False
        
        # Copy files
        os.makedirs(dist_dir)
        for root, dirs, files in os.walk(current_dir):
            # Skip hidden directories and excluded ones
            dirs[:] = [d for d in dirs if not d.startswith('.') and not should_exclude(d)]
            
            for file in files:
                if not should_exclude(file) and not file.startswith('.'):
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, current_dir)
                    dst_path = os.path.join(dist_dir, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
        
        # Create final distribution archive
        output_file = f"digital_chief_automation_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        archive_path = shutil.make_archive(output_file, 'zip', temp_dir, "digital_chief_automation_dist")
        
        print(f"✅ Distribution package created: {archive_path}")
        print("📝 This package is clean and ready for distribution with 8-hour expiration")


def main():
    parser = argparse.ArgumentParser(description="Script Expiration Management Utility")
    parser.add_argument("action", choices=["status", "reset", "package"], 
                       help="Action to perform: status (check expiration), reset (reset timer), package (create distribution)")
    
    args = parser.parse_args()
    
    print("🔧 Script Expiration Management Utility")
    print("=" * 50)
    
    if args.action == "status":
        check_expiration_status()
    elif args.action == "reset":
        reset_expiration()
    elif args.action == "package":
        create_distribution_package()
    
    print("\n💡 Usage Tips:")
    print("- Use 'reset' before giving the script to others")
    print("- Use 'package' to create a clean distribution zip")
    print("- Use 'status' to check current expiration status")


if __name__ == "__main__":
    main()