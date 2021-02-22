from neo.core.analogsignal import AnalogSignal
from quantities.quantity import Quantity
from quantities import second
from neo_importers.neo_wrapper import ElectricalStimulusWrapper
from typing import Iterable
import numpy as np
import random as rnd
from statistics import median
from math import pi, cos
from metrics import median_RMS
from scipy.signal import argrelextrema
from quantities import ms

# TODO: currently, the number of values in the linear spaces are hardcoded. We should probably change this in the future, to enable for larger or finer search spaces.

## Function to calculate the track correlation as defined by Turnquist et al. in the following paper: https://www.sciencedirect.com/science/article/abs/pii/S0165027016000054
# @param sweeps List of all sweeps
# @param center_sweep_idx Index of the sweep that we are currently analysing. Called k in the paper.
# @param latency Latency for which to calculate the TC, called t in the paper (in sencods)
# @param radius Radius of sweeps for which the TC should be calculated, called R in the paper.
# @param window_size The radius of the window for which the signal values are considered during RMS calculation.
# @return Returns the track correlation, i.e. the maximum RMS for different slopes, as well as the slope for which the maximum was achieved.
def track_correlation(raw_signal: AnalogSignal, el_stimuli: Iterable[ElectricalStimulusWrapper], center_sweep_idx: int, latency: Quantity, max_slope: Quantity = 0.005 * second, \
    radius: int = 2, window_size = 2 * ms):
    
    # build a linear space of float values between the minimum and maximum latency shift, i.e. the slope of the linear approximation of the track
    slopes = np.linspace(start = -max_slope, stop = max_slope, num = 26)
    rms = [median_RMS(raw_signal = raw_signal, el_stimuli = el_stimuli, center_stim_idx = center_sweep_idx, latency_slope = slope, latency = latency, radius = radius, window_size = window_size) for slope in slopes]
    
    # get the maximum shift, i.e. the optimal slope
    max_slope = slopes[np.argmax(rms)]
    # return it together with the track correlation
    return max(rms), max_slope

## Runs a search for the maximum track correlation around a given latency as defined in the Turnquist paper. TC means track correlation, RMS means Root Mean Square.
# @param sweeps List of sweeps
# @param sweep_idx Currently selected sweep on which we want to search the TC maximum
# @param latency The latency around which we search for the maximum
# @param max_shift Max. latency shift, i.e., the size of the "search window"
# @param max_slope Max. slope that is allowed when calculating the TC
# @param radius Number of sweeps in up- and downward direction to consider when calculating the median RMS/TC
# @param slope_penalty_term Decides which penalty term should be applied when selecting the next latency. 'cos' keeps the slope change compared to the previous track elements small.
# @param established_slope Previous approximation of the track's slope to compute the penalty from
# @param window_size Size of the window for which the RMS is calculated.
def search_for_max_tc(raw_signal: AnalogSignal, el_stimuli: Iterable[ElectricalStimulusWrapper], sweep_idx: int, latency: Quantity, max_shift: Quantity = 0.01 * second, \
    max_slope: Quantity = 0.001 * second, radius: int = 2, enforce_local_maximum: bool = False, slope_penalty_term: 'str' = None, \
        established_slope: Quantity = None, window_size: Quantity = 2 * ms):
    
    # create a linear space of latencies that we want to search
    latencies = np.linspace(start = latency - max_shift, stop = latency + max_shift, num = 26)

    # calculate the tc and slopes for all latencies
    # TODO parallelize this is some way
    # Problem is that multiprocessing copies the objects, resulting in extreme memory requirements
    # so maybe we have to extract the arrays and use their array manager objects
    tcs_slopes = np.array([track_correlation(raw_signal = raw_signal, el_stimuli = el_stimuli, latency = lat, \
        center_sweep_idx = sweep_idx, max_slope = max_slope, radius = radius, window_size = window_size) \
            for lat in latencies])
    
    # keep only the track correlations where we have a local maximum
    if enforce_local_maximum == True:

        # THIS BLOCK IS THE CRITERION AS DESCRIBED IN THE PAPER BUT IT DOES ONLY WORSEN THE RESULTS AS WELL.
        '''
        qualified_tcs = [min(tc - track_correlation(sweeps, center_sweep_idx = sweep_idx, latency = lat - 0.003, max_slope = max_slope, radius = radius, window_size = window_size)[0], \
                            tc - track_correlation(sweeps, center_sweep_idx = sweep_idx, latency = lat + 0.003, max_slope = max_slope, radius = radius, window_size = window_size)[0]) > 0 \
                            for (tc, _), lat in zip(tcs_slopes, latencies)]

        tcs_slopes = tcs_slopes[qualified_tcs]
        '''

        # THIS BLOCK USES AN AVERAGING FILTER AND RELATIVE MAXIMUM FUNCTION TO KEEP ONLY THOSE TC VALUES THAT ARE LOCAL MAXIMA. HOWEVER, THIS DOES NOT WORK ATM.
        '''
        tcs = np.array([tc for tc, _ in tcs_slopes])
        # define a little averaging filter and convolve with the TCs to get a filtered signal
        filt_size = 3
        avg_filter = np.array([1 / filt_size] * filt_size)
        filt_tcs = np.convolve(tcs, avg_filter)
        # now, retrieve the local maxima from the filtered TCs
        max_tcs = argrelextrema(filt_tcs, np.greater)
        # restrict to only these TC maxima (if there are any, else look everywhere)
        if not len(max_tcs[0]) == 0:
            tcs_slopes = tcs_slopes[max_tcs[0]]
        '''

    # If we want to extend a track, we need to use the cosine penalty as defined in the paper
    if slope_penalty_term == 'cos' and established_slope != None:
        tcs = [tc * cos(pi / max_shift * (established_slope - slope)) for tc, slope in tcs_slopes]
    else:
        tcs = [tc for tc, _ in tcs_slopes]

    # print("TCs: " + str(tcs))
    # print("Prev. Slope: " + str(established_slope))
    # print("Max. new slope: " + str(tcs_slopes[np.argmax(tcs)][1]))
    
    # and retrieve the latency for the maximum TC
    max_tc_latency = latencies[np.argmax(tcs)]
    # to return it together with its TC
    return max_tc_latency, max(tcs)

## This function returns an estimate of the track correlation noise.
# It samples a number of random points from the sweeps (we need to control for bias here!) and calculates the track correlation for each of these points.
# Then, it returns a threshold based on the median of these track correlation scores.
# @param sweeps List of all sweeps
# @param num_samples Number of random points in the recording that should be sampled
# @param minimum_latency Min. latency that a sample must have to the electrical stimulus. This is to avoid having high-scoring tracks following the electrical stimulus artifacts.
# @param verbose Set this to True if you want detailed information about the TCs as well as the points that have been sampled.
# @return Tuple of the TCs median and also the list of all TCs that have been calculated
def get_tc_noise_estimate(el_stimuli: Iterable[ElectricalStimulusWrapper], num_samples: int = 1000, minimum_latency: float = 20 * ms, verbose = False):
    
    # get the maximum and minimum time from all the sweeps in the recording
    t_min = min([sweep.t_start for sweep in el_stimuli])
    t_max = max([sweep.t_end for sweep in el_stimuli])
    
    # get num_samples random timestamps from where to sample the TC
    # sort them in ascending order s.t. we don't have to iterate over the sweeps multiple times
    sample_times = [rnd.uniform(t_min, t_max) for i in range(num_samples)]
    sample_times = sorted(sample_times)
    
    # start with the first sweep
    sweep_idx = 0
    tcs = []
    for t in sample_times:
        # iterate through the sweeps until we found the one in which the sampled time t lies
        while el_stimuli[sweep_idx].t_end < t and sweep_idx < len(el_stimuli) - 1:
            sweep_idx += 1
            
        # calculate the latency at which we look for the track correlation
        latency = t - el_stimuli[sweep_idx].t_start 
        # if the latency is too small, we'll probably record the artefact from the electrical stimulus
        if latency < minimum_latency:
            latency += minimum_latency
        
        # find the optimal TC and slope, and append the TC to a list of TCs for later median calculation
        tc, slope = track_correlation(el_stimuli, center_sweep_idx = sweep_idx, latency = latency)
        tcs.append(tc)
        
        if verbose == True:
            print("t = " + str(t) + ", lat = " + str(latency) + ", sweep_idx = " + str(sweep_idx) + "\nTC = " + str(tc) + " with slope " + str(slope))
    
    if verbose == True:
        print("\nFound these TCs:")
        print(tcs)
    
    return median(tcs), tcs