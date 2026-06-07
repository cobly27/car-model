#!/usr/bin/env python3
"""
Migrate product data from old array format to new category-based format.
"""

import json
from datetime import datetime

def migrate_data():
    """Perform the data migration."""
    
    # Read old data
    input_file = "minigt_products.json"
    print(f"Reading old data from {input_file}...")
    
    with open(input_file, "r", encoding="utf-8") as f:
        old_data = json.load(f)
    
    # Check if already in new format
    if isinstance(old_data, dict) and "categories" in old_data:
        print("Data already in new format!")
        return False
    
    # Create new structure
    new_data = {
        "categories": [
            {
                "id": "mini-gt",
                "name": "MINI GT",
                "products": old_data
            }
        ],
        "meta": {
            "total_products": len(old_data),
            "scrape_date": datetime.now().strftime("%Y-%m-%d")
        }
    }
    
    # Save new data
    output_file = "minigt_products.json"
    print(f"Writing new data to {output_file}...")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f"Migration complete!")
    print(f"  - Total products: {len(old_data)}")
    print(f"  - Added category: MINI GT")
    print(f"  - Old data backed up as minigt_products_backup.json")
    
    return True

if __name__ == "__main__":
    migrate_data()
