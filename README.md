# per2py_luminoskan

1. Prepare data for analysis:

   Open file PREPARE_LUMINOSKAN.py, for 96-well plate set no_of_columns = 12, for 384-well plate set no_of_columns = 24. Run by pressing F5, select the path to output (i.e. 
   the  unformatted xls or xlsx table from Luminoskan) and close the slection window, the script will generate file with the same ID_signal.csv in .\data\analysis_output__\
   
   Also need ID_XY.csv. See \_templates\ for examples. Use 96 or 384-well XY.csv template for corresponding signal.csv file.
   
   Copy your ID_XY.csv to output folder: \data\analysis_output__\ next to signal.csv file.
   

2. Open file START.py in IDLE (via conda-per2py environment or using batch file, see installation notes)

3. Change INPUT_FILES = ['ID'] to match your file names ID_signal.csv  (ID can be any character string)

4. Change time_factor if needed (for 96 well usually 0.25, for 384 well 1 hour).

5. Change treatment and end_h variables as needed (i.e. start and end times in hours for analysis of selected time intervals).

6. Run by pressing F5 or via menu Run - Run module. It can take a long time on weaker PC and with many traces, be patinet. Should beep once everything finished OK.

7. Plots are saved as png (for viewing) and svg (import to Corel Draw), output tables as csv files in .\data\analysis_output__\

8. Remove the analyzed files from .\data\analysis_output__\ before new analysis, otherwise the will be ovewritten.
