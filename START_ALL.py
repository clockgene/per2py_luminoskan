# run anaconda prompt
# type >>> conda activate per2py
# type >>> spyder
# open this file in spyder or idle and run with F5
# v.2024.12.12
# changelog:  polar scatter plot

from __future__ import division

# imports
import numpy  as np
import scipy as sp
import pandas as pd
from matplotlib import gridspec
import matplotlib.pyplot as plt
import PlotOptions as plo
import Bioluminescence as blu
import DecayingSinusoid as dsin
import CellularRecording as cr
import winsound
import glob
import matplotlib as mpl
import seaborn as sns
import math
import warnings


#inputs nms pre
PULL_FROM_IMAGEJ = False    # for Lumi data. Need to use mock _XY.csv and _signal.csv in analysis folder
INPUT_DIR = 'data/'
INPUT_EXT = '.csv'

# input files from Lumi need to be 2, id_signal and id_XY. From LV200 need only 1 trackmate output file.
INPUT_FILES   = ['241127']

# default is 6, lower values speed up fitting DecayingSinusoid by reducing overfitting, experimental !
max_degree = 3

# what is the lowest and highest expected period value (default is 18 and 30 h)
circ_low = 15
circ_high = 60

# Do you want to plot even empty/low signal wells in XY-heatmap, polar plot and histogram? True or False.
plot_all_wells = True

# How much plots of insidivual cells/wells do you need? Set nth=1 for all, nth=10 for every 10th, ...
nth = 20

# if recording 1 frame/hour (384 well plate in Luminoskan), set time_factor to 1, if 1 frame/0.25h (96 well plate), set to 0.25, etc...
time_factor = 1

# IN REAL HOURS or 0, plot and analyze only data from this timepoint, settings for truncate_t variable - 
treatment = 0

# IN REAL HOURS or None (for whole dataset), plot and analyze only data to this timepoint, settings for end variable
end_h = None
     
#
#
#                Code below this line should not be edited.
#

# for preanalyzed data from Lumi, use this and put signal and XY input files in analysis_output__ folder first
timestamp = '_'    

# supress annoying UserWarning: tight_layout: falling back to Agg renderer
def fxn():
    warnings.warn("tight_layout", UserWarning)

# APPLY 96MASK to filter out wells without any samples, if available. Beta version.
mydir = f'./{INPUT_DIR}analysis_output_{timestamp}/'
signal_data = pd.read_csv(glob.glob(f'{mydir}*signal.csv')[0])
try:
    #heatmap_mask_import = pd.read_excel(glob.glob(f'{mydir}*96mask.xlsx')[0]) # for 96mask.xlsx
    heatmap_mask_import = pd.read_csv(glob.glob(f'{mydir}*96mask*.csv')[0])   # for 96mask.csv
    heatmap_mask = heatmap_mask_import.iloc[:, 1:].T.values.flatten()
    mask = np.insert(heatmap_mask, 0, [True, True])
    flat_mask = [item for sublist in [list(i) for i in zip(heatmap_mask, heatmap_mask)] for item in sublist]  # idiotic way to make XY coordinates mask
    data_filtered = signal_data.loc[:, mask]   
    # locations = np.array([i[flat_mask] for i in locations])  # need to move after import
    mask_check = 1
    data_filtered.to_csv(f'{mydir}{INPUT_FILES[0]}_signal.csv', index=None)
    signal_data.to_csv(f'{mydir}{INPUT_FILES[0]}_signal_no_mask.csv', index=None)
    
    
    
    #data_filtered.to_csv(f'{mydir}{INPUT_FILES[0]}_signal_filtered.csv', index=None)    
except IndexError:
    mask_check = 0
    pass

# list all the datasets
all_inputs=[]
for input_fi in INPUT_FILES:
    all_inputs.append(cr.generate_filenames_dict(INPUT_DIR, input_fi,
                                    PULL_FROM_IMAGEJ, input_ij_extension=INPUT_EXT))

# process the data for every set of inputs
for files_dict in all_inputs:
    # assign all filenames to correct local variables
    data_type = files_dict['data_type']
    input_data = files_dict['input_data']
    input_dir = files_dict['input_dir']
    input_ij_extension = files_dict['input_ij_extension']
    input_ij_file = files_dict['input_ij_file']
    output_cosine = files_dict['output_cosine']
    output_cosine_params = files_dict['output_cosine_params']
    output_detrend = files_dict['output_detrend']
    output_zscore = files_dict['output_zscore']
    output_detrend_smooth = files_dict['output_detrend_smooth']
    output_detrend_smooth_xy = files_dict['output_detrend_smooth_xy']
    output_pgram = files_dict['output_pgram']
    output_phases = files_dict['output_phases']
    pull_from_imagej = files_dict['pull_from_imagej']
    raw_signal = files_dict['raw_signal']
    raw_xy = files_dict['raw_xy']

    # does the actual processing of the data
    # I. IMPORT DATA
    # only perform this step if pull_from_imagej is set to True
    if pull_from_imagej:
        cr.load_imagej_file(input_data, raw_signal, raw_xy, time_factor)

    raw_times, raw_data, locations, header = cr.import_data(raw_signal, raw_xy)
    time_factor = time_factor   
   
    if mask_check == 1:        
        locations = np.array([i[flat_mask] for i in locations])
    else:
        locations = locations      
    
    # II. INTERPOLATE MISSING PARTS
    # truncate 0 h and interpolate
    interp_times, interp_data, locations = cr.truncate_and_interpolate(
        raw_times, raw_data, locations, truncate_t=0)

    # III. DETREND USING HP Filter
    #(Export data for presentation of raw tracks with heatmap in Prism.)
    
    detrended_times, detrended_data, trendlines = cr.hp_detrend(
                                        interp_times, interp_data)


    # IV. SMOOTHING USING EIGENDECOMPOSITION or SAVITZKY-GOLAY Filter
    # try eigendecomposition, if fail due to inadequate number of values, use savgol
    try:
        denoised_times, denoised_data, eigenvalues = cr.eigensmooth(detrended_times, detrended_data, ev_threshold=0.05, dim=40)
        savgol=False
    except IndexError:        
        denoised_times, denoised_data, eigenvalues = cr.savgolsmooth(detrended_times, detrended_data, time_factor=time_factor)
        savgol=True     
    
    # TRUNCATE INITIAL HOURS OR FROM/UNTIL TREATMENT/END  
    final_times, final_data, locations = cr.truncate_and_interpolate_before(denoised_times,
                                    denoised_data, locations, truncate_t=treatment, end_h=end_h, time_factor=time_factor)

    # V. LS PERIODOGRAM TEST FOR RHYTHMICITY
    #lspers, pgram_data, circadian_peaks, lspeak_periods, rhythmic_or_not = cr.LS_pgram(final_times, final_data)
    lspers, pgram_data, circadian_peaks, lspeak_periods, rhythmic_or_not = cr.LS_pgram(final_times, final_data, circ_low=circ_low, circ_high=circ_high)

    # VI. GET A SINUSOIDAL FIT TO EACH CELL
    # use final_times, final_data
    # use forcing to ensure period within 1h of LS peak period

    sine_times, sine_data, phase_data, refphases, periods, amplitudes, decays, r2s, meaningful_phases =\
         cr.sinusoidal_fitting(final_times, final_data, rhythmic_or_not, max_degree=max_degree,
                               fit_times=raw_times, forced_periods=lspeak_periods)
   
    # get metrics
    circadian_metrics = np.vstack([rhythmic_or_not, circadian_peaks, refphases, periods, amplitudes,
                                   decays, r2s])     
     
    # VII. SAVING ALL COMPONENTS
    timer = plo.laptimer()
    print("Saving data... time: ",)

    # detrended
    cell_ids = header[~np.isnan(header)]
    #cell_ids = header[2:]   # to work with strings in cell ids but needs more code adjustment
    output_array_det = np.nan*np.ones((len(detrended_times)+1, len(cell_ids)+2))
    output_array_det[1:,0] = detrended_times
    output_array_det[1:,1] = np.arange(len(detrended_times))
    output_array_det[0,2:] = refphases
    output_array_det[1:,2:] = detrended_data
    output_df = pd.DataFrame(data=output_array_det,
            columns = ['TimesH', 'Frame']+list(cell_ids))
    output_df.loc[0,'Frame']='RefPhase'
    output_df.to_csv(output_detrend, index=False)
    del output_df # clear it

    # detrended-denoised
    output_array = np.nan*np.ones((len(final_times)+1, len(cell_ids)+2))
    output_array[1:,0] = final_times
    output_array[1:,1] = np.arange(len(final_times))
    output_array[0,2:] = refphases
    output_array[1:,2:] = final_data
    output_df = pd.DataFrame(data=output_array,
            columns = ['TimesH', 'Frame']+list(cell_ids))
    output_df.loc[0,'Frame']='RefPhase'
    output_df.to_csv(output_detrend_smooth, index=False)
    del output_df # clear it

    # Z-Score
    output_array = np.nan*np.ones((len(final_times)+1, len(cell_ids)+2))
    output_array[1:,0] = final_times
    output_array[1:,1] = np.arange(len(final_times))
    output_array[1:,2:] = sp.stats.zscore(final_data, axis=0, ddof=0)
    output_df = pd.DataFrame(data=output_array,
            columns = ['TimesH', 'Frame']+list(cell_ids))
    output_df.loc[0,'Frame']='RefPhase'
    output_df.loc[0,list(cell_ids)]=refphases
    output_df.to_csv(output_zscore, index=False)
    del output_df # clear it

    # LS Pgram
    output_array = np.nan*np.ones((len(lspers), len(pgram_data[0,:])+1))
    output_array[:,0] = lspers
    output_array[:,1:] = pgram_data
    output_df = pd.DataFrame(data=output_array,
            columns = ['LSPeriod']+list(cell_ids))
    output_df.to_csv(output_pgram, index=False)
    del output_df # clear it

    #sinusoids
    output_array = np.nan*np.ones((len(sine_times), len(cell_ids)+2))
    output_array[:,0] = sine_times
    output_array[:,1] = np.arange(len(sine_times))
    output_array[:,2:] = sine_data
    output_df = pd.DataFrame(data=output_array,
            columns = ['TimesH', 'Frame']+list(cell_ids))
    output_df.to_csv(output_cosine, index=False)
    del output_df

    #phases
    output_array = np.nan*np.ones((len(sine_times), len(cell_ids)+2))
    output_array[:,0] = sine_times
    output_array[:,1] = np.arange(len(sine_times))
    output_array[:,2:] = phase_data
    output_df = pd.DataFrame(data=output_array,
            columns = ['TimesH', 'Frame']+list(cell_ids))
    output_df.to_csv(output_phases, index=False)
    del output_df
    
    #trends    
    if end_h is None:
        end_t = len(raw_times)
    else:
        end_t = int(end_h * 1/time_factor)    
    trendlines_trunc = trendlines[int(treatment*1/time_factor):end_t, :]
    trend_array = [np.mean(i) for i in trendlines_trunc.T]
    trend_a = np.asarray(trend_array).reshape((1,len(trend_array)))

    # sinusoid parameters and XY locations
    # this gets the locations for each cell by just giving their mean
    # location and ignoring the empty values. this is a fine approximation.
    locs_fixed = np.zeros([2,len(cell_ids)])
    for idx in range(len(cell_ids)):
        locs_fixed[0, idx] = np.nanmean(locations[:,idx*2])
        locs_fixed[1, idx] = np.nanmean(locations[:,idx*2+1])
    output_array = np.nan*np.ones((9, len(cell_ids)))
    output_array = np.concatenate((circadian_metrics,locs_fixed, trend_a), axis=0)  #updated with trend/mesor
    output_array[2,:] *= 360/2/np.pi #transform phase into 360-degree circular format
    output_df = pd.DataFrame(data=output_array,
            columns = list(cell_ids), index=['Rhythmic','CircPeak','Phase','Period','Amplitude',
                                            'Decay','Rsq', 'X', 'Y', 'Trend'])
    output_df.T.to_csv(output_cosine_params, index=True)
    del output_df # clear it
    print(str(np.round(timer(),1))+"s")

    print("Generating and saving plots: ",)
    #cellidxs=np.random.randint(len(cell_ids),size=PLOTCOUNT)
    #for cellidx, trackid in enumerate(cell_ids.astype(int)):
    for cellidx, trackid in enumerate(cell_ids.astype(int)[::nth]):
        cr.plot_result(cellidx, raw_times, raw_data, trendlines,
                    detrended_times, detrended_data, eigenvalues,
                    final_times, final_data, rhythmic_or_not,
                    lspers, pgram_data, sine_times, sine_data, r2s,
                    INPUT_DIR+f'analysis_output_{timestamp}/', data_type, trackid, savgol)
    print(str(np.round(timer(),1))+"s")

    print("All data saved. Run terminated successfully for "+data_type+'.\n')

#############################################################
#############################################################
####### FINAL PLOTS #########################################
#############################################################
#############################################################  

# to change CT to polar coordinates for polar plotting
# 1h = (2/24)*np.pi = (1/12)*np.pi,   circumference = 2*np.pi*radius
# use modulo to get remainder after integer division
def polarphase(x):                                          
    if x < 24:
        r = (x/12)*np.pi        
    else:
        r = ((x % 24)/12)*np.pi
    return r

# stackoverflow filter outliers - change m as needed (2 is default, 10 filters only most extreme)
def reject_outliers(data, m=10.):
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d / (mdev if mdev else 1.)
    return data[s < m]

def reject_low(data):
    x = data.Trend.min()
    return data[data.Trend > 10*x]

# https://jakevdp.github.io/PythonDataScienceHandbook/04.07-customizing-colorbars.html
def grayscale_cmap(cmap):
    from matplotlib.colors import LinearSegmentedColormap
    """Return a grayscale version of the given colormap"""
    cmap = plt.cm.get_cmap(cmap)
    colors = cmap(np.arange(cmap.N))
    
    # convert RGBA to perceived grayscale luminance
    # cf. http://alienryderflex.com/hsp.html
    RGB_weight = [0.299, 0.587, 0.114]
    luminance = np.sqrt(np.dot(colors[:, :3] ** 2, RGB_weight))
    colors[:, :3] = luminance[:, np.newaxis]
        
    return LinearSegmentedColormap.from_list(cmap.name + "_gray", colors, cmap.N)

# CHOOSE color map
#cmap="viridis"
cmap="YlGnBu"
#cmap= grayscale_cmap(cmap)


mydir = f'./{INPUT_DIR}analysis_output_{timestamp}/'

# LOAD DATA FOR PLOTTING FROM ANALYSIS FOLDER
data = pd.read_csv(glob.glob(f'{mydir}*oscillatory_params.csv')[0], dtype={'X': int, 'Y': int})
data_dd = pd.read_csv(glob.glob(f'{mydir}*signal_detrend_denoise.csv')[0])
data_raw = pd.read_csv(glob.glob(f'{mydir}*signal.csv')[0])  # if mask used, this already contains filtered data w/o empty wells
# Filter out data from wells below 10xSD from median signal trend, but leave XY for heatmap if no mask used
if mask_check == 0 and plot_all_wells == False:    
    dd = np.abs(data.Trend - np.median(data.Trend)) #stackoverflow hack to filter out outliers
    mdevv = np.median(dd)
    ss = dd / (mdevv if mdevv else 1.)    
    data.loc[ss > 10, ['Rhythmic', 'CircPeak', 'Phase', 'Period', 'Amplitude','Decay', 'Rsq', 'Trend']] = np.nan
else:
    pass

### To save figs as vector svg with fonts editable in Corel ###
mpl.use('svg')                                                                          #import matplotlib as mpl
new_rc_params = {"font.family": 'Arial', "text.usetex": False, "svg.fonttype": 'none'}  #to store text as text, not as path in xml-coded svg file
mpl.rcParams.update(new_rc_params)

#############################################################
####### FILTER DATA #########################################
#############################################################   

# Use amplitude to filter out nans
outlier_reindex = ~(np.isnan(data['Amplitude']))    
data_filt = data[data.columns[:].tolist()][outlier_reindex]  # data w/o amp outliers

# FILTER outliers by iqr filter: within 2.22 IQR (equiv. to z-score < 3)
#cols = data_filt.select_dtypes('number').columns   # pick only numeric columns
cols = ['Period', 'Amplitude', 'Decay', 'Rsq','Trend']    # pick hand selected columns
df_sub = data.loc[:, cols]
iqr = df_sub.quantile(0.75, numeric_only=False) - df_sub.quantile(0.25, numeric_only=False)
lim = np.abs((df_sub - df_sub.median()) / iqr) < 2.22
# replace outliers with nan
data_filt.loc[:, cols] = df_sub.where(lim, np.nan)   
# replace outlier-caused nans with median values    
# data_filt['Phase'].fillna(data_filt['Phase'].median(), inplace=True)
data_filt['Period'].fillna(data_filt['Period'].median(), inplace=True)
data_filt['Amplitude'].fillna(data_filt['Amplitude'].median(), inplace=True)
data_filt['Decay'].fillna(data_filt['Decay'].median(), inplace=True)
data_filt['Rsq'].fillna(data_filt['Rsq'].median(), inplace=True)
data_filt['Trend'].fillna(data_filt['Trend'].median(), inplace=True)

#########################################################################
####### Single Polar Phase Plot #########################################
#########################################################################

phaseseries = data_filt['Phase'].values.flatten()                                           # plot Phase
data_filt.loc[data_filt['Rsq'] < 0.1, 'Rsq'] = 0.1          # filter out too low R values to avoid memory errors 
phase_sdseries = 0.1/(data_filt['Rsq'].values.flatten())                                     # plot R2 related number as width

# NAME
genes = data_filt['Unnamed: 0'].values.flatten().astype(int)                      # plot profile name as color
colorcode = plt.cm.nipy_spectral(np.linspace(0, 1, len(genes)))     # gist_ncar, RdYlBu, Accent check>>> https://matplotlib.org/examples/color/colormaps_reference.html

# LENGTH (AMPLITUDE)
amp = data_filt['Amplitude'].values.flatten()                       # plot filtered Amplitude as length
#amp = 1                                                            # plot arbitrary number if Amp problematic

# POSITION (PHASE)
#phase = [polarphase(i) for i in phaseseries]                        # if phase in in hours (cosinor)
phase = np.radians(phaseseries)                                    # if phase is in degrees (per2py))
#phase = [i for i in phaseseries]                                   # if phase is in radians already

# WIDTH (SD, SEM, R2, etc...)
#phase_sd = [polarphase(i) for i in phase_sdseries]                 # if using CI or SEM of phase, which is in hours
phase_sd = [i for i in phase_sdseries]                              # if using Rsq/R2, maybe adjust thickness 


ax = plt.subplot(111, projection='polar')                                                       #plot with polar projection
bars = ax.bar(phase, amp, width=phase_sd, color=colorcode, bottom=0, alpha=0.8)       #transparency-> alpha=0.5, , rasterized = True, bottom=0.0 to start at center, bottom=amp.max()/3 to start in 1/3 circle
#ax.set_yticklabels([])          # this deletes radial ticks
ax.set_theta_zero_location('N') # this puts CT=0 theta=0 to North - points upwards
ax.set_theta_direction(-1)      #reverse direction of theta increases
ax.set_thetagrids((0, 45, 90, 135, 180, 225, 270, 315), labels=('0', '3', '6', '9', '12', '15', '18', '21'), fontweight='bold', fontsize=12)  #set theta grids and labels, **kwargs for text properties
#ax.legend(bars, genes, fontsize=8, bbox_to_anchor=(1.1, 1.1))   # legend needs sequence of labels after object bars which contains sequence of bar plots 
ax.set_xlabel("Circadian phase (h)", fontsize=12)
#plt.title("Individual phases plot", fontsize=14, fontstyle='italic')


### To save as vector svg with fonts editable in Corel ###
plt.savefig(f'{mydir}Phase plot.svg', format = 'svg', bbox_inches = 'tight') #if using rasterized = True to reduce size, set-> dpi = 1000
### To save as bitmap png for easy viewing ###
plt.savefig(f'{mydir}Phase plot.png', bbox_inches = 'tight')
#plt.show()
plt.clf()
plt.close()



###############################################################################################
####### Single Polar Histogram of frequency of phases #########################################
###############################################################################################

N_bins = 47                                                     # how much bins, 23 is for 1 bin per hour, depends on distribution
#colorcode = plt.cm.nipy_spectral(np.linspace(0, 1, N_bins))      #gist_ncar, RdYlBu, Accent check>>> https://matplotlib.org/examples/color/colormaps_reference.html
colorcode = sns.husl_palette(256)[0::int(round(len(sns.husl_palette(256)) / N_bins, 0))]

phase_hist, tick = np.histogram(phase, bins = N_bins, range=(0, 2*np.pi))           # need hist of phase in N bins from 0 to 23h
theta = np.linspace(0.0, 2 * np.pi, N_bins, endpoint=False)     # this just creates number of bins spaced along circle, in radians for polar projection, use as x in histogram
width = (2*np.pi) / N_bins                                      # equal width for all bins that covers whole circle

axh = plt.subplot(111, projection='polar')                                                      #plot with polar projection
bars_h = axh.bar(theta, phase_hist, width=width, color=colorcode, bottom=2, alpha=0.8)          # bottom > 0 to put nice hole in centre

axh.set_yticklabels([])          # this deletes radial ticks
axh.set_theta_zero_location('N') # this puts CT=0 theta=0 to North - points upwards
axh.set_theta_direction(-1)      #reverse direction of theta increases
axh.set_thetagrids((0, 45, 90, 135, 180, 225, 270, 315), labels=('0', '3', '6', '9', '12', '15', '18', '21'), fontweight='bold', fontsize=12)  #set theta grids and labels, **kwargs for text properties
axh.set_xlabel("Circadian phase (h)", fontsize=12)
#plt.title("Phase histogram", fontsize=14, fontstyle='italic')

# calculate vector sum of angles and plot "Rayleigh" vector
a_cos = map(lambda x: math.cos(x), phase)
a_sin = map(lambda x: math.sin(x), phase)
uv_x = sum(a_cos)/len(phase)
uv_y = sum(a_sin)/len(phase)
uv_radius = np.sqrt((uv_x*uv_x) + (uv_y*uv_y))
uv_phase = np.angle(complex(uv_x, uv_y))

# Alternative from http://webspace.ship.edu/pgmarr/Geo441/Lectures/Lec%2016%20-%20Directional%20Statistics.pdf
#v_angle = math.atan((uv_y/uv_radius)/(uv_x/uv_radius))

v_angle = uv_phase     # they are the same 
v_length = uv_radius*max(phase_hist)  # because hist is not (0,1) but (0, N in largest bin), need to increase radius

# Rayleigh test for non-uniformity of circular data https://github.com/circstat/pycircstat/blob/master/pycircstat/tests.py
r_Rt = uv_radius
n_Rt = len(phaseseries)
R_Rt = n_Rt * r_Rt                              # compute Rayleigh's R (equ. 27.1)
z_Rt = R_Rt ** 2 / n_Rt                         # compute Rayleigh's z (equ. 27.2)
pval_Rt = np.exp(np.sqrt(1 + 4 * n_Rt + 4 * (n_Rt ** 2 - R_Rt ** 2)) - (1 + 2 * n_Rt))     # compute p value using approxation in Zar, p. 617

#add arrow and test rounded pvalue
axh.annotate('',xy=(v_angle, v_length), xytext=(v_angle,0), xycoords='data', arrowprops=dict(width=1, color='black'))
axh.annotate(f'p={np.format_float_scientific(pval_Rt, precision=4)}', xy=(v_angle, v_length))

### To save as vector svg with fonts editable in Corel ###
plt.savefig(f'{mydir}Histogram_Phase.svg', format = 'svg', bbox_inches = 'tight') #if using rasterized = True to reduce size, set-> dpi = 1000
### To save as bitmap png for easy viewing ###
plt.savefig(f'{mydir}Histogram_Phase.png', bbox_inches = 'tight')
#plt.show()
plt.clf()
plt.close()


# POLAR SCATTER PLOT, needs work
def create_second_list(original_list):
    second_list = []
    count_dict = {}

    for num in original_list:
        if num not in count_dict:
            count_dict[num] = 1
            second_list.append(1)
        else:
            count_dict[num] += 0.05
            second_list.append(1 + count_dict[num] - 1)

    return second_list

phase_rounded = np.round(phase, 1)
r_from_amp = create_second_list(phase_rounded)
dfr = pd.DataFrame(r_from_amp)
max_size = max(dfr[0].value_counts()) # this is cca. radius of the plot - use it to change v_length in annotate, but must be for all compared plots same
ax = plt.subplot(111, projection='polar')                                                       #plot with polar projection
ax.scatter(phase_rounded, r_from_amp, alpha=0.5, marker=".", edgecolors='none', color='black') # color=colorcode,
ax.set_theta_zero_location('N') # this puts CT=0 theta=0 to North - points upwards
ax.set_theta_direction(-1)      #reverse direction of theta increases
ax.set_thetagrids((0, 45, 90, 135, 180, 225, 270, 315), labels=('0', '3', '6', '9', '12', '15', '18', '21'), fontweight='bold', fontsize=12)  #set theta grids and labels, **kwargs for text properties
ax.yaxis.grid(False)   # turns off circles
ax.xaxis.grid(False)  # turns off radial grids
ax.set_yticklabels([])
ax.tick_params(pad=2)
ax.set_xlabel("Circadian phase (h)", fontsize=12)   
ax.annotate('',xy=(v_angle, v_length/20), xytext=(v_angle,0), xycoords='data', arrowprops=dict(width=0.5, color='black', headwidth=5, headlength=5)) # , headlength=10
ax.annotate(f'p={np.format_float_scientific(pval_Rt, precision=4)}', xy=(v_angle, v_length))

### To save as vector svg with fonts editable in Corel ###
plt.savefig(f'{mydir}Phase scatter plot.svg', format = 'svg', bbox_inches = 'tight') #if using rasterized = True to reduce size, set-> dpi = 1000
### To save as bitmap png for easy viewing ###
# plt.savefig(f'{mydir}Phase scatter plot.png', bbox_inches = 'tight')    # this is very slow when number of rois is > 500
#plt.show()
plt.clf()
plt.close()


###############################################################################################
####### Single Histogram of frequency of periods ##############################################
###############################################################################################

#outlier_reindex_per = ~(np.isnan(reject_outliers(data[['Period']])))['Period'] 
#data_filt_per = data_filt[outlier_reindex_per]
data_filt_per = data_filt.copy()

######## Single Histogram ##########
y = "Period"
x_lab = y
y_lab = "Frequency"
ylim = (0, 0.4)
xlim = (math.floor(data_filt['Period'].min() - 1), math.ceil(data_filt_per['Period'].max() + 1))
suptitle_all = f'{x_lab} vs {y_lab}'
x_coord = xlim[0] + (xlim[1]-xlim[0])/8
y_coord = ylim[1] - (ylim[1]/8)

with warnings.catch_warnings():  # supress annoying UserWarning: tight_layout: falling back to Agg renderer
    warnings.simplefilter("ignore")
    fxn()

    allplot = sns.FacetGrid(data_filt_per)
    allplot = allplot.map(sns.distplot, y, kde=False)
    plt.xlim(xlim)
    #plt.legend(title='Sex')
    plt.xlabel(x_lab)
    plt.ylabel(y_lab)
    plt.text(x_coord, y_coord, f'n = ' + str(data_filt_per[y].size - data_filt_per[y].isnull().sum()) + '\nmean = ' + str(round(data_filt_per[y].mean(), 3)) + ' ± ' + str(round(data_filt_per[y].sem(), 3)) + 'h')
    #loc = plticker.MultipleLocator(base=4.0) # this locator puts ticks at regular intervals
    #allplot.xaxis.set_major_locator(loc)
    
    ### To save as vector svg with fonts editable in Corel ###
    plt.savefig(f'{mydir}' + '\\' + 'Histogram_Period.svg', format = 'svg', bbox_inches = 'tight')
    ### To save as bitmap png for easy viewing ###
    plt.savefig(f'{mydir}' + '\\' + 'Histogram_Period.png', format = 'png', bbox_inches = 'tight')
    plt.clf()
    plt.close()


############################################################
###### XY coordinates Heatmap of phase #####################
############################################################

# round values to 1 decimal
data_round = np.round(data[['X', 'Y', 'Phase']], decimals=3)
# pivot and transpose for heatmap format
df_heat = data_round.pivot(index='X', columns='Y', values='Phase').transpose()

suptitle1 = "Phase of PER2 expression"
titleA = "XY wellplate coordinates"
                                   
fig, axs = plt.subplots(ncols=2, nrows=1, sharex=False, sharey=False,  gridspec_kw={'width_ratios': [20, 1]}) 
heat1 = sns.heatmap(df_heat.astype(float), annot=False, square=True, cbar=True, ax=axs[0], cbar_ax=axs[1], cmap=mpl.colors.ListedColormap(sns.husl_palette(256)))  #tell sns which ax to use  #cmap='coolwarm'  #yticklabels=n >> show every nth label

fig.suptitle(suptitle1, fontsize=12, fontweight='bold')
axs[0].set_title(titleA, fontsize=10, fontweight='bold')
axs[0].set(xlabel='columns', ylabel='rows')

### To save as vector svg with fonts editable in Corel ###
plt.rcParams['svg.fonttype'] = 'none'    #to store text as text, not as path in xml-coded svg file, but avoid bugs that prevent rotation of ylabes when used before setting them
plt.savefig(f'{mydir}Heatmap_XY_Phase.svg', format = 'svg', bbox_inches = 'tight')
### To save as bitmap png for easy viewing ###
plt.savefig(f'{mydir}Heatmap_XY_Phase.png', format = 'png')
plt.clf()
plt.close()


############################################################
###### XY coordinates Heatmap of amplitude #################
############################################################

data_a = data[['X', 'Y', 'Amplitude']]
# pivot and transpose for heatmap format
df_heat = data_a.pivot(index='X', columns='Y', values='Amplitude').transpose()

suptitle1 = "Amplitude of PER2 expression"
titleA = "XY wellplate coordinates"
                                    
fig, axs = plt.subplots(ncols=2, nrows=1, sharex=False, sharey=False,  gridspec_kw={'width_ratios': [20, 1]}) 
heat1 = sns.heatmap(df_heat.astype(float), annot=False, square=True, cbar=True, ax=axs[0], cbar_ax=axs[1], cmap=cmap)  #tell sns which ax to use  #cmap='YlGnBu'  #yticklabels=n >> show every nth label

fig.suptitle(suptitle1, fontsize=12, fontweight='bold')
axs[0].set_title(titleA, fontsize=10, fontweight='bold')
axs[0].set(xlabel='columns', ylabel='rows')

### To save as vector svg with fonts editable in Corel ###
plt.rcParams['svg.fonttype'] = 'none'    #to store text as text, not as path in xml-coded svg file, but avoid bugs that prevent rotation of ylabes when used before setting them
plt.savefig(f'{mydir}Heatmap_XY_Amp.svg', format = 'svg', bbox_inches = 'tight')
### To save as bitmap png for easy viewing ###
plt.savefig(f'{mydir}Heatmap_XY_Amp.png', format = 'png')
plt.clf()
plt.close()


############################################################
###### XY coordinates Heatmap of period ####################
############################################################

data_p = np.round(data[['X', 'Y', 'Period']], decimals=3)
# pivot and transpose for heatmap format
df_heat = data_p.pivot(index='X', columns='Y', values='Period').transpose()

suptitle1 = "Period of PER2 expression"
titleA = "XY wellplate coordinates"
                                    
fig, axs = plt.subplots(ncols=2, nrows=1, sharex=False, sharey=False,  gridspec_kw={'width_ratios': [20, 1]}) 
heat1 = sns.heatmap(df_heat.astype(float), annot=False, square=True, cbar=True, ax=axs[0], cbar_ax=axs[1], cmap=cmap)  #tell sns which ax to use  #cmap='coolwarm'  #yticklabels=n >> show every nth label

fig.suptitle(suptitle1, fontsize=12, fontweight='bold')
axs[0].set_title(titleA, fontsize=10, fontweight='bold')
axs[0].set(xlabel='columns', ylabel='rows')

### To save as vector svg with fonts editable in Corel ###
plt.rcParams['svg.fonttype'] = 'none'    #to store text as text, not as path in xml-coded svg file, but avoid bugs that prevent rotation of ylabes when used before setting them
plt.savefig(f'{mydir}Heatmap_XY_Period.svg', format = 'svg', bbox_inches = 'tight')
### To save as bitmap png for easy viewing ###
plt.savefig(f'{mydir}Heatmap_XY_Period.png', format = 'png')
plt.clf()
plt.close()


############################################################
###### XY coordinates Heatmap of trend ####################
############################################################

data_t = data[['X', 'Y', 'Trend']]
# pivot and transpose for heatmap format
df_heat = data_t.pivot(index='X', columns='Y', values='Trend').transpose()

suptitle1 = "Baseline trend of PER2 expression"
titleA = "XY wellplate coordinates"
                                    
fig, axs = plt.subplots(ncols=2, nrows=1, sharex=False, sharey=False,  gridspec_kw={'width_ratios': [20, 1]}) 
heat1 = sns.heatmap(df_heat.astype(float), annot=False, square=True, cbar=True, ax=axs[0], cbar_ax=axs[1], cmap=cmap)  #tell sns which ax to use  #cmap='coolwarm'  #yticklabels=n >> show every nth label

fig.suptitle(suptitle1, fontsize=12, fontweight='bold')
axs[0].set_title(titleA, fontsize=10, fontweight='bold')
axs[0].set(xlabel='columns', ylabel='rows')

### To save as vector svg with fonts editable in Corel ###
plt.rcParams['svg.fonttype'] = 'none'    #to store text as text, not as path in xml-coded svg file, but avoid bugs that prevent rotation of ylabes when used before setting them
plt.savefig(f'{mydir}Heatmap_XY_Trend.svg', format = 'svg', bbox_inches = 'tight')
### To save as bitmap png for easy viewing ###
plt.savefig(f'{mydir}Heatmap_XY_Trend.png', format = 'png')
plt.clf()
plt.close()

############################################################
###### Dual Heatmap of Raw and Denoised Signal #############
############################################################

sns.set_context("paper", font_scale=1)

x_lab = "time"
suptitle = "Individual luminescence traces"

# NonSorted Raw data Heatmap
newi1 = data_raw.iloc[:-2, 1:].astype(float).set_index(data_raw.columns[1]).index.astype(int)   #set 'Frame' as index
df_heat_spec1  = data_raw.iloc[:-2, 2:].astype(float).set_index(newi1).transpose()
titleA = "raw"

# NonSorted Detrended traces (Looks good)
data_dd.pop('Frame')
newi2 = data_dd.iloc[1:-2, :].astype(float).set_index('TimesH').index.astype(int)  #removes 2 last cols
df_heat_spec2 = data_dd.iloc[1:-2, 1:].astype(float).set_index(newi2).transpose()  #removes 2 last cols
titleB = "interpolated detrended"
# to plot sorted by phases, use first row in data_dd to sort before transposition

fig, axs = plt.subplots(ncols=5, nrows=1, sharex=False, sharey=False,  gridspec_kw={'width_ratios': [20, 1, 1, 20, 1]}) 
heat1 = sns.heatmap(df_heat_spec1.astype(float), xticklabels=96, yticklabels=False, annot=False, cbar=True, ax=axs[0], cbar_ax=axs[1], cmap="viridis")  #tell sns which ax to use  #cmap='coolwarm'  
heat2 = sns.heatmap(df_heat_spec2.astype(float), xticklabels=96, yticklabels=False, annot=False, cbar=True, ax=axs[3], cbar_ax=axs[4], cmap="coolwarm")    # yticklabels=10 #use every 10th label

fig.suptitle(suptitle, fontsize=12, fontweight='bold')
axs[0].set_title(titleA, fontsize=10, fontweight='bold')
axs[0].set(xlabel='Time (h)')
axs[2].set_axis_off()  # to put more space between plots so that cbar does not overlap, use 3d axis and set it off
axs[3].set_title(titleB, fontsize=10, fontweight='bold')
axs[3].set(xlabel='Time (h)')

plt.rcParams['svg.fonttype'] = 'none'    #to store text as text, not as path in xml-coded svg file, but avoid bugs that prevent rotation of ylabes when used before setting them
plt.savefig(f'{mydir}Dual_Heatmap.svg', format = 'svg', bbox_inches = 'tight')
plt.savefig(f'{mydir}Dual_Heatmap.png', format = 'png')
plt.clf()
plt.close()


############################################
###### Composite_Raw_Line_Plot #############
############################################
# for 384-well plate
if time_factor == 1:
    fig, axs = plt.subplots(16, 24, sharex=True, sharey=True)
    #fig.subplots_adjust(hspace=0.3, wspace=-0.9)  # negative wspace moves left and right close but there is empty space    
    counter = 1
    yc = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
    for j in range(24):
        for i in range(16):        
            axs[i, j].plot(data_raw[str(counter)], linewidth=0.1)
            axs[i, j].label_outer()
            axs[i, j].set_yticklabels([])
            axs[i, j].set_xticklabels([]) 
            axs[i, j].set_xlabel(f'{yc[i]}{j + 1} n.{counter}', fontsize=2, labelpad=-10) 
            axs[i, j].set_xticks([])
            axs[i, j].set_yticks([])
            axs[i, j].spines['top'].set_visible(False) # to turn off individual borders 
            axs[i, j].spines['right'].set_visible(False)
            axs[i, j].spines['bottom'].set_visible(False)
            axs[i, j].spines['left'].set_visible(False)            
            counter += 1
    
    ### To save as bitmap png for easy viewing ###
    plt.savefig(f'{mydir}Composite_Raw_Line_Plot.png', dpi=1000)
    ### To save as vector svg with fonts editable in Corel ###
    plt.savefig(f'{mydir}Composite_Raw_Line_Plot.svg', format = 'svg') #if using rasterized = True to reduce size, set-> dpi = 1000
    plt.clf()
    plt.close()

# for 96-well plate
if time_factor == 0.25:
    fig, axs = plt.subplots(8, 12, sharex=True, sharey=True)
    #fig.subplots_adjust(hspace=0.3, wspace=-0.9)  # negative wspace moves left and right close but there is empty space  
    counter = 1
    yc = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    for j in range(12):
        for i in range(8):        
            axs[i, j].plot(data_raw[str(counter)], linewidth=0.1)
            axs[i, j].label_outer()
            axs[i, j].set_yticklabels([])
            axs[i, j].set_xticklabels([]) 
            axs[i, j].set_xlabel(f'{yc[i]}{j + 1} n.{counter}', fontsize=2, labelpad=-10) 
            axs[i, j].set_xticks([])
            axs[i, j].set_yticks([])
            axs[i, j].spines['top'].set_visible(False) # to turn off individual borders 
            axs[i, j].spines['right'].set_visible(False)
            axs[i, j].spines['bottom'].set_visible(False)
            axs[i, j].spines['left'].set_visible(False)            
            counter += 1
    
    ### To save as bitmap png for easy viewing ###
    plt.savefig(f'{mydir}Composite_Raw_Line_Plot.png', dpi=1000)
    ### To save as vector svg with fonts editable in Corel ###
    plt.savefig(f'{mydir}Composite_Raw_Line_Plot.svg', format = 'svg') #if using rasterized = True to reduce size, set-> dpi = 1000
    plt.clf()
    plt.close()

print(f'Finished Plots at {mydir}') 
winsound.Beep(500, 800)