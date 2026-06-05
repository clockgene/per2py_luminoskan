# v 26.06.02, gemini version to avoid unexpected end of data when column contains only 0

import numpy as np
import pandas as pd
import os, shutil
import settings


# Choose, which plate - if 96 well, it has 12 columns, if 384 well, it has 24 columns.
# plate = 96    # comment out (add #) for 384-well plate
plate = 384   # uncomment (delete # on this line) for 384-well plate

# calls global variables from module settings.py, for tkinter file selecting
settings.init()


def split_data(data, i=2, j=10, k=1, l=13, modulus=10, start=2):
    # Initialize using the first data matrix block at the very top of the spreadsheet
    timelist = [np.array(data.iloc[i:j, k:l]).T.flatten().astype(float)]  
    time = [(data.iloc[i, l+2])/3600]                                   
    
    for index in data.iloc[:, k:l].index: 
        if (index + start) % modulus == 0:
            
            row_start = index + i + start
            row_end = index + j + start
            
            # Boundary control check
            if row_end > len(data):
                break
                
            # UNIVERSAL VALIDITY CHECK: Inspect the structure columns or measurement block
            # If the block contains NaNs where data/well letters should be, stop execution immediately.
            check_block = data.iloc[row_start:row_end, k:l]
            
            # If the target rows are unpopulated (all values are NaN), stop
            if check_block.isna().all().all():
                break
                
            # If the well index rows (Column 0, containing A-P) become blank/NaN, stop
            if data.iloc[row_start:row_end, 0].isna().any():
                break
                
            try:
                # Coerce data to numeric: zeros stay 0.0, strings/text turn into NaN
                numeric_block = check_block.apply(pd.to_numeric, errors='coerce')
                
                # Check if coercion stripped out data (i.e., we are hitting text metadata rows)
                if numeric_block.isna().any().any():
                    # If the rows contain mixed metadata text rather than numbers, stop here
                    break
                    
                # Append the flattened matrix values cleanly
                flat_data = numeric_block.values.T.flatten().astype(float)
                timelist.append(flat_data)    
                
                # Process the corresponding timestamp
                time_val = (data.iloc[row_start, l+2])/3600
                time.append(time_val)                         
                
            except (TypeError, ValueError):
                # Safely terminate if parsing errors break down at the file's footer
                break
        
    # Generate final output table structure
    df = pd.DataFrame(timelist)    
    df.columns = [f'{n}' for n in range(1, ((j-i)*(l-k)+1))]
    
    # Add standardized timeframe reference trackers
    df.insert(0, 'Frame', np.arange(0, len(df)*1, 1))
    df.insert(1, 'TimesH', time)
    
    print(f'Data processed successfully! Extracted exactly {len(df)} timepoints.')
    
    return df

# File reading safety operations
try:
    data = pd.read_excel(settings.INPUT_DIR + settings.INPUT_FILE)  
except:
    data = pd.read_csv(settings.INPUT_DIR + settings.INPUT_FILE)

# Execute geometry profiles
if plate == 96:    
    df = split_data(data, i=2, j=10, k=1, l=13, modulus=10, start=2)
if plate == 384:   
    df = split_data(data, i=2, j=18, k=1, l=25, modulus=18, start=2)

# Export downstream CSV matrix
mydir = './data/analysis_output__/'
os.makedirs(mydir, exist_ok = True)  
df.to_csv(os.path.join(mydir, f'{settings.INPUT_FILES[0]}_signal.csv'), index=False)

# Copy correct XY file to analysis_output__/ and rename it
template_dir = './_templates/analysis_output__/'
if plate == 96:
    shutil.copy(f'{template_dir}96_XY.csv', f'{mydir}{settings.INPUT_FILES[0]}_XY.csv')
if plate == 384:
    shutil.copy(f'{template_dir}384_XY.csv', f'{mydir}{settings.INPUT_FILES[0]}_XY.csv')

# test data 
# 96 well
#print(data.iloc[2:10, :13])
#print(data.iloc[12:20, :13])
# 384 well
#print(data.iloc[2:18, :25])
#print(data.iloc[20:36, :25])
#times
#data.iloc[2, 15]
#data.iloc[12, 15]