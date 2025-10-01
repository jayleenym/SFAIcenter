#!/usr/bin/env python3
"""
Script to update file_id in merged_extracted_qna_domain_Lv2345_completed.json
using management numbers and ISBNs from Excel data.
"""

import json
import pandas as pd
import os
from pathlib import Path

def load_excel_data(excel_path, sheet_name, header_row=3):
    """Load Excel data and return DataFrame with management numbers and ISBNs"""
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        return df[['관리번호', 'ISBN', '도서명', '분류']]
    except Exception as e:
        print(f"Error loading Excel file: {e}")
        return None

def create_mapping_from_excel(excel_path):
    """Create mapping from ISBN to management number"""
    mapping = {}
    
    # Try different sheet names and header rows
    sheet_configs = [
        ('1차 분석', 3),
        ('2차 분석', 3), 
        ('3차 분석', 3),
        ('1차 구매', 4),
        ('2차 구매', 4),
        ('3차 구매', 4)
    ]
    
    for sheet_name, header_row in sheet_configs:
        try:
            df = load_excel_data(excel_path, sheet_name, header_row)
            if df is not None and not df.empty:
                print(f"Found data in sheet '{sheet_name}' with {len(df)} rows")
                for _, row in df.iterrows():
                    isbn = str(row['ISBN']).strip()
                    mgmt_num = str(row['관리번호']).strip()
                    if isbn and mgmt_num and isbn != 'nan' and mgmt_num != 'nan':
                        mapping[isbn] = mgmt_num
                break
        except Exception as e:
            print(f"Could not load sheet '{sheet_name}': {e}")
            continue
    
    return mapping

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
    
    # Look for Excel file
    possible_excel_paths = [
        "/Users/yejin/Library/CloudStorage/OneDrive-개인/데이터L/selectstar/도서목록_전체통합.xlsx"
    ]
    
    excel_path = None
    for path in possible_excel_paths:
        if os.path.exists(path):
            excel_path = path
            break
    
    if excel_path is None:
        print("Excel file not found. Please provide the path to '도서목록_전체통합.xlsx'")
        excel_path = input("Enter the full path to the Excel file: ").strip()
        
        if not os.path.exists(excel_path):
            print(f"File not found: {excel_path}")
            return
    
    print(f"Using Excel file: {excel_path}")
    
    # Create mapping
    print("Creating ISBN to management number mapping...")
    mapping = create_mapping_from_excel(excel_path)
    
    if not mapping:
        print("No mapping data found in Excel file")
        return
    
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

if __name__ == "__main__":
    main()
