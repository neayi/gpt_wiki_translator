#!/usr/bin/env python3
"""Pretty print translation logs."""
import sys
import csv
from pathlib import Path

def format_log():
    log_path = Path('logs/translated_log.csv')
    if not log_path.exists():
        print("❌ No log file found at logs/translated_log.csv")
        return
    
    with log_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("ℹ️  No translations logged yet")
        return
    
    print(f"\n📊 Translation Log ({len(rows)} entries)\n")
    print("="*80)
    
    for i, row in enumerate(rows, 1):
        status_emoji = {
            'translated': '✅',
            'skipped': '⏭️',
            'error': '❌'
        }.get(row['status'], '❓')
        
        print(f"\n{status_emoji} Entry #{i} - {row['status'].upper()}")
        print(f"   Source:  {row['source_page']} ({row['source_lang']})")
        print(f"   Target:  {row['target_page']} ({row['target_lang']})")
        print(f"   Date:    {row['date_iso']}")
        
        if row['notes']:
            # Truncate long notes
            notes = row['notes']
            if len(notes) > 150:
                notes = notes[:150] + "..."
            print(f"   Notes:   {notes}")
        
        print("-"*80)
    
    # Statistics
    statuses = {}
    for row in rows:
        status = row['status']
        statuses[status] = statuses.get(status, 0) + 1
    
    print(f"\n📈 Statistics:")
    for status, count in statuses.items():
        emoji = {'translated': '✅', 'skipped': '⏭️', 'error': '❌'}.get(status, '❓')
        print(f"   {emoji} {status.capitalize()}: {count}")
    print()

if __name__ == '__main__':
    try:
        format_log()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
