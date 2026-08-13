#!/usr/bin/env python3
"""
Font Downloader for GuardianX Report Template
Downloads and organizes all necessary fonts for Korean text support
"""

import os
import urllib.request
import tempfile
import shutil
import zipfile
import json
from pathlib import Path
import subprocess
import sys

class FontDownloader:
    def __init__(self, fonts_dir="fonts"):
        self.fonts_dir = Path(fonts_dir)
        self.fonts_dir.mkdir(exist_ok=True)
        
        # Font URLs for Korean fonts - using working URLs
        self.font_urls = {
            'Nanum Gothic': {
                'url': 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf',
                'filename': 'NanumGothic-Regular.ttf'
            },
            'Nanum Gothic Bold': {
                'url': 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf',
                'filename': 'NanumGothic-Bold.ttf'
            },
            'Nanum Myeongjo': {
                'url': 'https://github.com/google/fonts/raw/main/ofl/nanummyeongjo/NanumMyeongjo-Regular.ttf',
                'filename': 'NanumMyeongjo-Regular.ttf'
            },
            'Nanum Myeongjo Bold': {
                'url': 'https://github.com/google/fonts/raw/main/ofl/nanummyeongjo/NanumMyeongjo-Bold.ttf',
                'filename': 'NanumMyeongjo-Bold.ttf'
            },
            'Noto Sans KR': {
                'url': 'https://fonts.gstatic.com/s/notosanskr/v36/1Pn6eXt6Kw-hjzqtV7jQjA.woff2',
                'filename': 'NotoSansKR-Regular.woff2'
            },
            'Noto Sans KR Bold': {
                'url': 'https://fonts.gstatic.com/s/notosanskr/v36/1Pn6eXt6Kw-hjzqtV7jQjA.woff2',
                'filename': 'NotoSansKR-Bold.woff2'
            }
        }
        
        # Fallback fonts (English) - using working URLs
        self.fallback_fonts = {
            'DejaVu Sans': {
                'url': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf',
                'filename': 'DejaVuSans.ttf'
            },
            'DejaVu Sans Bold': {
                'url': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf',
                'filename': 'DejaVuSans-Bold.ttf'
            },
            'Liberation Sans': {
                'url': 'https://github.com/liberationfonts/liberation-fonts/raw/main/liberation-fonts-ttf-2.1.5/LiberationSans-Regular.ttf',
                'filename': 'LiberationSans-Regular.ttf'
            }
        }
        
        # Font mapping for different weights and styles
        self.font_mapping = {
            'regular': ['Noto Sans KR', 'Nanum Gothic'],
            'bold': ['Noto Sans KR Bold', 'Nanum Gothic Bold'],
            'serif': ['Nanum Myeongjo'],
            'serif_bold': ['Nanum Myeongjo Bold'],
            'fallback': ['DejaVu Sans', 'Liberation Sans'],
            'fallback_bold': ['DejaVu Sans Bold']
        }

    def download_font(self, font_name, font_info):
        """Download a single font file"""
        try:
            print(f"Downloading {font_name}...")
            
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                # Download font
                urllib.request.urlretrieve(font_info['url'], temp_file.name)
                
                # Copy to fonts directory
                font_path = self.fonts_dir / font_info['filename']
                shutil.copy2(temp_file.name, font_path)
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                print(f"✓ Successfully downloaded {font_name} to {font_path}")
                return str(font_path)
                
        except Exception as e:
            print(f"✗ Failed to download {font_name}: {e}")
            return None

    def download_all_fonts(self):
        """Download all fonts"""
        print("Starting font download...")
        print(f"Fonts will be saved to: {self.fonts_dir.absolute()}")
        
        downloaded_fonts = {}
        
        # Download Korean fonts
        for font_name, font_info in self.font_urls.items():
            font_path = self.download_font(font_name, font_info)
            if font_path:
                downloaded_fonts[font_name] = font_path
        
        # Download fallback fonts
        for font_name, font_info in self.fallback_fonts.items():
            font_path = self.download_font(font_name, font_info)
            if font_path:
                downloaded_fonts[font_name] = font_path
        
        # Save font mapping
        self.save_font_mapping(downloaded_fonts)
        
        print(f"\nDownload completed! {len(downloaded_fonts)} fonts downloaded.")
        return downloaded_fonts

    def save_font_mapping(self, downloaded_fonts):
        """Save font mapping to JSON file"""
        mapping_file = self.fonts_dir / 'font_mapping.json'
        
        # Create font mapping with paths
        font_config = {
            'fonts_dir': str(self.fonts_dir.absolute()),
            'downloaded_fonts': downloaded_fonts,
            'font_mapping': self.font_mapping,
            'css_font_families': {
                'korean_sans': '"Nanum Gothic", sans-serif',
                'korean_serif': '"Nanum Myeongjo", serif',
                'fallback': '"Arial", sans-serif'
            }
        }
        
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(font_config, f, indent=2, ensure_ascii=False)
        
        print(f"Font mapping saved to: {mapping_file}")

    def create_css_file(self):
        """Create CSS file with font-face declarations"""
        css_file = self.fonts_dir / 'fonts.css'
        
        css_content = """/* Font declarations for GuardianX Report Template */
@font-face {
    font-family: 'Noto Sans KR';
    src: url('./NotoSansKR-Regular.woff2') format('woff2');
    font-weight: normal;
    font-style: normal;
}

@font-face {
    font-family: 'Noto Sans KR';
    src: url('./NotoSansKR-Bold.woff2') format('woff2');
    font-weight: bold;
    font-style: normal;
}

@font-face {
    font-family: 'Nanum Gothic';
    src: url('./NanumGothic-Regular.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
}

@font-face {
    font-family: 'Nanum Gothic';
    src: url('./NanumGothic-Bold.ttf') format('truetype');
    font-weight: bold;
    font-style: normal;
}

@font-face {
    font-family: 'Nanum Myeongjo';
    src: url('./NanumMyeongjo-Regular.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
}

@font-face {
    font-family: 'Nanum Myeongjo';
    src: url('./NanumMyeongjo-Bold.ttf') format('truetype');
    font-weight: bold;
    font-style: normal;
}

@font-face {
    font-family: 'DejaVu Sans';
    src: url('./DejaVuSans.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
}

@font-face {
    font-family: 'DejaVu Sans';
    src: url('./DejaVuSans-Bold.ttf') format('truetype');
    font-weight: bold;
    font-style: normal;
}

@font-face {
    font-family: 'Liberation Sans';
    src: url('./LiberationSans-Regular.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
}

/* Font family classes */
.korean-sans {
    font-family: "Noto Sans KR", "Nanum Gothic", sans-serif;
}

.korean-serif {
    font-family: "Nanum Myeongjo", serif;
}

.fallback-font {
    font-family: "DejaVu Sans", "Liberation Sans", "Arial", sans-serif;
}
"""
        
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        print(f"CSS file created: {css_file}")

    def verify_fonts(self):
        """Verify that all fonts are properly downloaded"""
        print("\nVerifying downloaded fonts...")
        
        missing_fonts = []
        for font_name, font_info in self.font_urls.items():
            font_path = self.fonts_dir / font_info['filename']
            if not font_path.exists():
                missing_fonts.append(font_name)
                print(f"✗ Missing: {font_name}")
            else:
                print(f"✓ Found: {font_name}")
        
        for font_name, font_info in self.fallback_fonts.items():
            font_path = self.fonts_dir / font_info['filename']
            if not font_path.exists():
                missing_fonts.append(font_name)
                print(f"✗ Missing: {font_name}")
            else:
                print(f"✓ Found: {font_name}")
        
        if missing_fonts:
            print(f"\nWarning: {len(missing_fonts)} fonts are missing!")
            return False
        else:
            print("\nAll fonts verified successfully!")
            return True

def main():
    """Main function to run font downloader"""
    print("GuardianX Font Downloader")
    print("=" * 40)
    
    # Create downloader instance
    downloader = FontDownloader()
    
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
        print("\nYou can now use these fonts in your PDF generation!")
    else:
        print("\n⚠️  Font download completed with some issues.")
        print("Please check the missing fonts above.")

if __name__ == "__main__":
    main()
