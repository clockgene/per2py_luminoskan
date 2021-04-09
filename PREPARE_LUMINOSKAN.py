# -*- coding: utf-8 -*-
"""
Created on Wed Feb  3 13:01:03 2021
# v2021.02.15
@author: Martin.Sladek
"""
import numpy  as np
import pandas as pd
import settings


# Choose, which plate - if 96 well, it has 12 columns, if 384 well, it has 24 columns.
no_of_columns = 12    # comment out (add #) for 384-well plate
#no_of_columns = 24   # uncomment (delete # on this line) for 384-well plate


# calls global variables from module settings.py, for tkinter file selecting
settings.init()

# function, i-l are positions of table, modulus sets repeated row
def split_data(data, i=2, j=10, k=1, l=13, modulus=10, start=2):

    timelist = [np.array(data.iloc[i:j, k:l]).T.flatten().astype(float)]  # create df with first timepoint data
    time = [(data.iloc[i, l+2])/3600]                                   # create list with first time in hours
    for index in data.iloc[:, k:l].index: 
        if (index + start) % modulus == 0:
            try:
                if sum(sum(data.iloc[(index + i + start):(index + j + start), k:l].T.values)) > 0:
                    timelist.append(np.array(data.iloc[(index + i + start):(index + j + start), k:l]).T.flatten().astype(float))    
                    time.append((data.iloc[index + i + start, l+2])/3600)                         
            except TypeError:                
                pass
        
    df = pd.DataFrame(timelist)    
    df.columns = [f'{i}' for i in range(1, ((j-i)*(l-k)+1))]
    
    # add time and frame columns
    df.insert(0, 'Frame', np.arange(0, len(df)*0.25, 0.25))
    df.insert(1, 'TimesH', time)
    
    print('Data processed.')
    
    return df

# read input file
try:
    data = pd.read_excel(settings.INPUT_DIR + settings.INPUT_FILE)
except:
    data = pd.read_csv(settings.INPUT_DIR + settings.INPUT_FILE)


# Execute function
if no_of_columns == 12:    
    df = split_data(data)
else:    
    df = split_data(data, i=2, j=18, k=1, l=25, modulus=18, start=2)

# Export dataframe as csv file 
mydir = './data/analysis_output__/'
df.to_csv(f'{mydir}{settings.INPUT_FILES[0]}_signal.csv', index=False)


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