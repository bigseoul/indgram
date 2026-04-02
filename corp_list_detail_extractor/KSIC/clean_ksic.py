import pandas as pd
import os

def extract_ksic_levels(excel_path):
    """
    Extracts industry classification levels (2, 3, 4, 5) from the Excel file
    and saves them as separate CSV files.
    """
    print(f"Reading Excel: {excel_path}")
    
    # Read Excel file, specify sheet and treat '표준산업\n분류' as string to preserve leading zeros
    df = pd.read_excel(excel_path, sheet_name='연계표', dtype={'표준산업\n분류': str})
    
    # Remove any completely empty rows
    df = df.dropna(subset=['표준산업\n분류']).copy()
    
    # Column mapping (Code from respective columns, Name from respective columns)
    levels = {
        'level_1': {'slice': 1, 'name_col': '대분류.1', 'code_col': '대분류'},
        'level_2': {'slice': 2, 'name_col': '중분류.1'},
        'level_3': {'slice': 3, 'name_col': '소분류.1'},
        'level_4': {'slice': 4, 'name_col': '세분류.1'},
        'level_5': {'slice': 5, 'name_col': '세세분류'}
    }
    
    output_dir = os.path.dirname(excel_path)
    
    for level_name, config in levels.items():
        s = config['slice']
        name_col = config['name_col']
        code_col = config.get('code_col')
        
        # Extract unique mappings
        temp_df = df.copy()
        
        # Format the code: if code_col is specified, use it (e.g. for alphabet level 1),
        # otherwise slice the 5-digit numeric classification code.
        if code_col:
            temp_df['코드'] = temp_df[code_col].str.strip()
        else:
            temp_df['코드'] = temp_df['표준산업\n분류'].str.strip().str.zfill(5).str[:s]
            
        temp_df['명칭'] = temp_df[name_col].str.strip()
        
        # Filter and drop duplicates to ensure 1:1 mapping for each level code
        result_df = temp_df[['코드', '명칭']].dropna().drop_duplicates(subset=['코드']).sort_values('코드')
        
        # Save to CSV
        output_file = os.path.join(output_dir, f"{level_name}.csv")
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ Saved {output_file} ({len(result_df)} items)")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "11차 한국표준산업분류.xlsx")
    
    if not os.path.exists(input_file):
        print(f"❌ Error: File not found at {input_file}")
        return

    try:
        extract_ksic_levels(input_file)
        print("\n🎉 KSIC level data extraction completed successfully.")
    except Exception as e:
        print(f"❌ Error during extraction: {str(e)}")

if __name__ == "__main__":
    main()
