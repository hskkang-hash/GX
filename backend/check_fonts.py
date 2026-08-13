#!/usr/bin/env python3
"""
Simple font checker for GuardianX Font System
Checks font files and mapping without Django dependencies
"""

import json
import os
from pathlib import Path

def check_font_files():
    """Check if font files exist and are accessible"""
    print("🧪 Checking Font Files...")
    print("=" * 40)
    
    fonts_dir = Path("fonts")
    if not fonts_dir.exists():
        print("❌ Fonts directory not found")
        return False
    
    # Check font files
    font_files = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))
    
    if not font_files:
        print("❌ No font files found")
        return False
    
    print(f"✅ Found {len(font_files)} font files:")
    for font_file in font_files:
        size = font_file.stat().st_size
        print(f"   📄 {font_file.name} ({size:,} bytes)")
    
    return True

def check_font_mapping():
    """Check font mapping file"""
    print("\n🧪 Checking Font Mapping...")
    print("=" * 40)
    
    mapping_file = Path("fonts/font_mapping.json")
    if not mapping_file.exists():
        print("❌ Font mapping file not found")
        return False
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        print("✅ Font mapping loaded successfully")
        print(f"   📁 Fonts directory: {mapping_data.get('fonts_dir', 'N/A')}")
        
        # Check downloaded fonts
        downloaded_fonts = mapping_data.get('downloaded_fonts', {})
        print(f"   🔤 Downloaded fonts: {len(downloaded_fonts)}")
        
        for font_name, font_path in downloaded_fonts.items():
            if os.path.exists(font_path):
                print(f"      ✅ {font_name}: {font_path}")
            else:
                print(f"      ❌ {font_name}: {font_path} (not found)")
        
        # Check font families
        css_families = mapping_data.get('css_font_families', {})
        print(f"   🎨 CSS font families: {len(css_families)}")
        for family_name, family_value in css_families.items():
            print(f"      🎨 {family_name}: {family_value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading font mapping: {e}")
        return False

def check_css_file():
    """Check CSS file"""
    print("\n🧪 Checking CSS File...")
    print("=" * 40)
    
    css_file = Path("fonts/fonts.css")
    if not css_file.exists():
        print("❌ CSS file not found")
        return False
    
    try:
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        print("✅ CSS file loaded successfully")
        
        # Count @font-face declarations
        font_face_count = css_content.count('@font-face')
        print(f"   📝 Font-face declarations: {font_face_count}")
        
        # Check for Korean font references
        if 'Nanum Gothic' in css_content:
            print("   🇰🇷 Korean fonts referenced in CSS")
        else:
            print("   ⚠️  Korean fonts not found in CSS")
        
        # Check for font classes
        if '.korean-sans' in css_content and '.korean-serif' in css_content:
            print("   🎨 Korean font classes defined")
        else:
            print("   ⚠️  Korean font classes missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading CSS file: {e}")
        return False

def main():
    """Main function"""
    print("🚀 GuardianX Font System Checker")
    print("=" * 50)
    
    checks = [
        ("Font Files", check_font_files),
        ("Font Mapping", check_font_mapping),
        ("CSS File", check_css_file)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check crashed: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n📊 Check Results Summary")
    print("=" * 30)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! Font system is ready.")
        print("\n📝 Next steps:")
        print("   1. Use fonts in your Django application")
        print("   2. Call create_korean_font_config('fonts') in your code")
        print("   3. Generate PDFs with Korean text support")
    else:
        print("⚠️  Some checks failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
