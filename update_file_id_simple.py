#!/usr/bin/env python3
"""
Script to update file_id in merged_extracted_qna_domain_Lv2345_completed.json
using management numbers and ISBNs from Excel data via ProcessFiles module.
"""

import json
import os
import sys

# Add the tools directory to the path
sys.path.append('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/tools')

try:
    import ProcessFiles as pf
except ImportError as e:
    print(f"Error importing ProcessFiles: {e}")
    print("Please make sure the ProcessFiles.py is in the tools directory")
    sys.exit(1)

def update_json_file_ids(json_file_path, mapping, output_path=None):
    """Update file_id values in JSON file using the mapping"""
    if output_path is None:
        output_path = json_file_path
    
    print(f"Loading JSON file: {json_file_path}")
    
    # Load the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} records")
    
    # Count updates
    updated_count = 0
    not_found_count = 0
    
    # Update file_id values
    for i, record in enumerate(data):
        current_file_id = record.get('file_id', '')
        
        if current_file_id in mapping:
            new_file_id = mapping[current_file_id]
            record['file_id'] = new_file_id
            updated_count += 1
            
            if i < 10:  # Show first 10 updates
                print(f"Updated: {current_file_id} -> {new_file_id}")
        else:
            not_found_count += 1
            if i < 10:  # Show first 10 not found
                print(f"Not found in mapping: {current_file_id}")
    
    # Save updated JSON
    print(f"\nSaving updated JSON to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\nUpdate Summary:")
    print(f"- Total records: {len(data)}")
    print(f"- Updated: {updated_count}")
    print(f"- Not found in mapping: {not_found_count}")
    
    return updated_count, not_found_count

def main():
    # File paths
    json_file = "/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FIN_workbook/1C/merged_extracted_qna_domain_Lv2345_completed.json"
    
    # Update the BASE_PATH in ProcessFiles to match the current user's path
    original_base_path = pf.BASE_PATH
    pf.BASE_PATH = "/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter"
    
    try:
        print("Loading Excel data using ProcessFiles module...")
        excel_data = pf.get_excel_data(1, pf.BASE_PATH)
        
        print(f"Excel data loaded with {len(excel_data)} rows")
        print(f"Columns: {list(excel_data.columns)}")
        
        # Create mapping from ISBN to management number
        mapping = {}
        for idx, row in excel_data.iterrows():
            isbn = str(row['ISBN']).strip()
            mgmt_num = str(idx).strip()  # The index is the management number
            if isbn and mgmt_num and isbn != 'nan' and mgmt_num != 'nan':
                mapping[isbn] = mgmt_num
        
        print(f"Created mapping with {len(mapping)} entries")
        
        # Show sample mappings
        print("\nSample mappings:")
        for i, (isbn, mgmt_num) in enumerate(list(mapping.items())[:5]):
            print(f"  {isbn} -> {mgmt_num}")
        
        # Update JSON file
        print(f"\nUpdating JSON file...")
        updated_count, not_found_count = update_json_file_ids(json_file, mapping)
        
        if updated_count > 0:
            print(f"\nSuccessfully updated {updated_count} file_id values!")
        else:
            print("\nNo file_id values were updated. Please check the mapping.")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the Excel file '도서목록_전체통합.xlsx' exists in the project directory")
    finally:
        # Restore original BASE_PATH
        pf.BASE_PATH = original_base_path

if __name__ == "__main__":
    main()

