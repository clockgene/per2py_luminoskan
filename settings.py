import datetime as dt
import os
from tkinter import filedialog
import tkinter as tk


def clicked():    
    global filename                      # Allow user to select a directory and store it in global var folder_path
    filename = filedialog.askopenfilename(filetypes=[('Table', ['.csv', '.xlsx', '.xls'])])    
    print(filename)
    #window.destroy()                          # close window after pushing button, does not work


def init():
    global INPUT_FILES
    global INPUT_DIR
    global INPUT_EXT
    global INPUT_FILE
    
    window = tk.Tk()
    window.geometry()
    window.title("per2py")
    #open_file_label = tk.Label(window, text="Select file and close:", font=("Arial", 10), padx=5, pady=5)
    #open_file_label.grid(column=0, row=0)
    open_file_button = tk.Button(window, text="Select file and then close this window to proceed.", font=("Arial", 14), command=clicked, padx=5, pady=5)
    open_file_button.grid(column=1, row=0)
    window.mainloop()
    INPUT_FILES = []
    INPUT_FILES.append(os.path.splitext(os.path.basename(filename))[0])
    #INPUT_DIR = os.path.split(os.path.dirname(filename))[1] + '/'
    INPUT_DIR = os.path.dirname(filename) + '/'
    INPUT_EXT = os.path.splitext(os.path.basename(filename))[-1]
    INPUT_FILE = os.path.basename(filename)
    
    global timestamp
    for fls in INPUT_FILES:
        timestamp = f'{fls}_'+ dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')