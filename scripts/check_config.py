#!/usr/bin/env python3
"""Configuration checker for gpt_wiki_translator."""
import sys
import os
sys.path.insert(0, 'src')

def check_config():
    """Verify that configuration is properly set up."""
    print("🔍 Checking configuration...\n")
    
    # Check .env file
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("   Create one from .env.example: cp .env.example .env")
        return False
    else:
        print("✓ .env file exists")
    
    # Try to load settings
    try:
        from gpt_wiki_translator.config import get_settings
        settings = get_settings()
        print("✓ Settings loaded successfully")
        
        # Check required fields
        checks = [
            ('OpenAI API Key', settings.openai_api_key, lambda v: v and len(v) > 20),
            ('OpenAI Model', settings.openai_model, lambda v: bool(v)),
            ('MediaWiki Username', settings.mediawiki_username, lambda v: v is not None),
            ('MediaWiki Password', settings.mediawiki_password, lambda v: v is not None),
        ]
        
        print("\n📋 Configuration values:")
        for name, value, validator in checks:
            if validator(value):
                print(f"  ✓ {name}: {'*' * min(len(str(value)), 20) if 'Key' in name or 'Password' in name else value}")
            else:
                print(f"  ⚠️  {name}: Not set or invalid")
        
        print(f"\n⚙️  Optional settings:")
        print(f"  - Max tokens per chunk: {settings.max_tokens_per_chunk}")
        print(f"  - Temperature: {settings.temperature}")
        print(f"  - Log CSV path: {settings.log_csv_path}")
        
        if settings.mediawiki_api_endpoint:
            print(f"  - Default MediaWiki endpoint: {settings.mediawiki_api_endpoint}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return False

if __name__ == '__main__':
    success = check_config()
    print("\n" + ("="*50))
    if success:
        print("✅ Configuration looks good! You can now run:")
        print("   python -m gpt_wiki_translator --target-lang en --input data/example_pages.txt --dry-run")
    else:
        print("❌ Please fix configuration issues above")
    sys.exit(0 if success else 1)
