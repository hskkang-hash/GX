#!/usr/bin/env python3
"""
Main script to download fonts for GuardianX Report Template
Run this script to download all necessary fonts for Korean text support
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from report_template.font_downloader import FontDownloader

def main():
    """Main function to download fonts"""
    print("🚀 GuardianX Font Downloader")
    print("=" * 50)
    
    # Check if fonts directory already exists
    fonts_dir = Path("fonts")
    if fonts_dir.exists() and any(fonts_dir.glob("*.ttf")) or any(fonts_dir.glob("*.otf")):
        print(f"📁 Fonts directory already exists at: {fonts_dir.absolute()}")
        response = input("Do you want to re-download fonts? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Using existing fonts. Exiting...")
            return
    
    # Create downloader instance
    downloader = FontDownloader()
    
    try:
        # Download all fonts
        downloaded_fonts = downloader.download_all_fonts()
        
        # Create CSS file
        downloader.create_css_file()
        
        # Verify fonts
        success = downloader.verify_fonts()
        
        if success:
            print("\n🎉 Font download completed successfully!")
            print(f"📁 Fonts directory: {downloader.fonts_dir.absolute()}")
            print("📄 CSS file: fonts.css")
            print("📋 Font mapping: font_mapping.json")
            print("\n✨ You can now use these fonts in your PDF generation!")
            print("\n📝 To use fonts in your code:")
            print("   from report_template.utils import create_korean_font_config")
            print("   font_config = create_korean_font_config('fonts')")
        else:
            print("\n⚠️  Font download completed with some issues.")
            print("Please check the missing fonts above.")
            
    except KeyboardInterrupt:
        print("\n\n❌ Font download interrupted by user.")
        print("Partial downloads may be available in the fonts directory.")
    except Exception as e:
        print(f"\n💥 Error during font download: {e}")
        print("Please check your internet connection and try again.")

if __name__ == "__main__":
    main()
