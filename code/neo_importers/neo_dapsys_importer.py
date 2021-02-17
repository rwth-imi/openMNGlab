from fibre_tracking import ap_template
import os
import csv
import pandas as pd
import numpy as np
from pathlib import Path
from math import ceil, floor
from typing import List, Iterable
from operator import itemgetter
from scipy.signal import argrelextrema
from tqdm import tqdm
from quantities import Quantity, second
from neo.core import Event, IrregularlySampledSignal, AnalogSignal, SpikeTrain
from typing import Union

# these are imports from our own packages
from fibre_tracking import ActionPotentialTemplate, APTrack
from metrics import normalized_cross_correlation #, sliding_window_normalized_cross_correlation

## this function fixes the problem with dapsys csv files that use the comma not only as csv-separator but also for decimal numbers
# @param in_path Path where the original files are placed
# @param out_path Path where the fixed files should be written (filenames are preserved), will be created on demand
# @param new_separator New separator character for the CSV file
def _fix_separator_decimal_matching(in_path: str, out_path: str, new_separator = ","):
    # create the output directory if necessary
    Path(out_path).mkdir(parents = True, exist_ok = True)

    # get a list of the files in the directory and load all of them sequentially
    for path in os.listdir(in_path):
        in_path_full = in_path + '\\' + path
        out_path_full = out_path + '\\' + path

        # open the input and output csv files
        with open(in_path_full, 'r', newline = '\n') as in_csv_file, \
             open(out_path_full, 'a', newline = '\n') as out_csv_file:
            csv_reader = csv.reader(in_csv_file, delimiter = ',')
            csv_writer = csv.writer(out_csv_file, delimiter = new_separator, \
                quoting = csv.QUOTE_NONNUMERIC, escapechar = "\\")

            # enumerate over the rows to replace every second "," with a decimal point
            for i, row in enumerate(csv_reader):
                out_row = []
                # for every second value, append the next using a decimal point
                for idx in range(0, len(row) - 1, 2):
                    num = float(f"{row[idx]}.{row[idx + 1]}")
                    out_row.append(num)
                # for some files, there is something like a comment that we need to append as well
                if len(row) % 2 != 0:
                    if isinstance(row[-1], float):
                        out_row.append(row[-1])
                    else:
                        out_row.append(f"{row[len(row) - 1]}")
                # then, write the new row into the output csv file
                csv_writer.writerow(out_row)

## Read the main pulse file which has "pulses" in its name
def _read_main_pulse_file(filepaths: List[str]) -> Event:
    try: 
        # read pulse file
        pulse_file = [file for file in filepaths if "pulses" in os.path.basename(file).lower()][0]
        pulses_df = pd.read_csv(filepath_or_buffer = pulse_file, header = None, names = ["timestamp", "comment"])
        times = Quantity(pulses_df["timestamp"], "s")
        return Event(times =  times, labels = pulses_df["comment"])
    except Exception as ex:
        print(ex)

## Read signal file
# @param signal_unit You can provide a unit for the signal, else it will be dimensionless
def _read_signal_file(filepaths: List[str], signal_unit: Quantity = None) -> IrregularlySampledSignal:
    # things are a bit complicated here as the signal is not necessarily covering the whole experiment!
    try:
        # get the continous signal file
        signal_file = [file for file in filepaths if "continuous" in os.path.basename(file).lower()][0]

        times = []
        signal = []

        # open the file for reading
        with open(signal_file, "r") as file:
            
            # and create a reader
            reader = csv.reader(file, delimiter = ",")
            # this try/catch handles the exception that is raised by "next" if the reader reached the file ending
            try:
                while True:
                    # read time and signal rows
                    time_row = np.array([float(val) for val in next(reader)])
                    signal_row = np.array([float(val) for val in next(reader)])
                    assert len(time_row) == len(signal_row)

                    times.append(time_row)
                    signal.append(signal_row)
            except StopIteration:
                pass

        # concatenate our list of arrays
        times = np.concatenate(times) * second
        signal = np.concatenate(signal)
        assert len(times) == len(signal)
        
        if not signal_unit is None:
            signal = signal * signal_unit
        else:
            signal = Quantity(signal, "dimensionless")

        return IrregularlySampledSignal(times = times, signal = signal)

    # something might go wrong as we perform some IO operations here
    except Exception as ex:
        print(ex)

## reads the template file with the given index
def _read_template_file(filepaths: List[str], track_idx: int) -> ActionPotentialTemplate:
    try:
        # find the right file
        template_files = [file for file in filepaths if "template" in os.path.basename(file).lower() and "track" in os.path.basename(file).lower()]
        template_file = [file for file in template_files if "track" + str(track_idx) + ".csv" in file.lower()][0]
        # read and return the AP template
        template_df = pd.read_csv(filepath_or_buffer = template_file, header = None, names = ["signal_value"])
        return ActionPotentialTemplate(signal_template = template_df["signal_value"].values)
    except Exception as ex:
        print(ex)

## reads the tracks from files which have track but not template in their name
def _read_track_files(filepaths: List[str], el_stimuli: Event) -> List[APTrack]:
    # then, we want to add the AP tracks as they are produced by Dapsys (if there are any)
    # here, we need the main pulses / electric stimuli already which is why we extract them from the recording first
    # get the track and template files
    track_files = [file for file in filepaths if "track" in os.path.basename(file).lower() and not "template" in os.path.basename(file).lower()]
    
    ap_tracks = []
    for track_file in track_files:
        # get the lowercase filename once because we'll operate on it multiple times now
        lower_fname = os.path.basename(track_file).lower()

        # let's get the index of this track s.t. we can look for the corresponding template
        track_idx_start = lower_fname.index("track") + len("track")
        track_idx_stop = lower_fname.index(".csv")
        # this could fail if somebody puts non-numeric characters between "track" and ".csv" in the filename
        try:
            track_idx = int(lower_fname[track_idx_start : track_idx_stop])
            track_df = pd.read_csv(filepath_or_buffer = track_file, header = None, names = ["timestamp", "latency", "comments"])

            # into this list, we write the latencies as tuples (sweep index, latency)
            latencies = []
            sweep_idx = 0
            for timestamp, latency in zip(track_df["timestamp"].values, track_df["latency"].values):
                # increase the sweep index, until the main pulse time is larger than the timestamp
                while (timestamp > el_stimuli.times[sweep_idx] and sweep_idx < len(el_stimuli) - 1):
                    sweep_idx += 1
                # then append the latency for this sweep index
                latencies.append((sweep_idx, latency * second))

            # now, we can make a track out of this
            ap_track = APTrack(latencies = latencies)

            # now, get the template
            try:
                ap_track.ap_template = _read_template_file(filepaths = filepaths, track_idx = track_idx)
            except Exception as ex:
                print(ex)

            # append this to the list of ap tracks which we load
            ap_tracks.append(ap_track)
        except Exception as ex:
            print(ex)

    return ap_tracks

# TODO implement if necessary
def _determine_threshold_from_tracks():
    # # iterate over the action potentials, getting the maximum signal value for each of them
    # max_sig_vals = []
    # for ap in self.track_aps:
    #     max_sig_vals.append(max(ap.raw_signal))
    # # now, we determine the threshold by taking the given quantile which means that we assume for the lowest 5 percent of values that they got here erroneously
    # return np.quantile(max_sig_vals, q = quantile)
    pass

# TODO add doxygen comment
def _find_action_potentials_on_tracks(self, ap_tracks: Iterable[APTrack], el_stimuli: Event, signal: Union[IrregularlySampledSignal, AnalogSignal], \
    window_size: Quantity = Quantity(0.003, "s")) -> List[SpikeTrain]:
    
    # TODO implement this function for analog signals and make it reusable
    if isinstance(signal, AnalogSignal):
        raise NotImplementedError("Not implemented for analog signals yet.")

    # initialize our list of action_potentials
    track_aps = []
    
    # iterate over all the tracks
    for track_idx, ap_track in enumerate(ap_tracks):
        # first, get the template of our current AP track
        ap_template = ap_track.ap_template
        # start in the beginning for of the signal, for each track
        signal_idx = 0

        # then, slide the template over the window, calculating cross correlation for all the datapoints
        for sweep_idx, ap_latency in zip(ap_track.sweep_idcs, ap_track.latencies):
            # now, we need the time of the main pulse and add the latency to define the point around which we want to search
            window_center_time = el_stimuli.times[sweep_idx] + ap_latency
            # now, we define the indices of the first and last data points that we consider for our windowing
            
            if isinstance(signal, IrregularlySampledSignal):
                signal: IrregularlySampledSignal
                # find first signal index
                while signal.times[signal_idx] < (window_center_time - window_size - len(ap_template) / 2):
                    signal_idx += 1
                first_signal_idx = signal_idx
                # find last signal index
                while signal.times[signal_idx] < (window_center_time + window_size + len(ap_template) / 2):
                    signal_idx += 1
                last_signal_idx = signal_idx
            else:
                # TODO implement index calculation for regularly sampled signals
                # first_signal_idx = floor((window_center_time - window_size) * self.sampling_rate - (len(ap_template) / 2.0)) 
                # last_signal_idx = floor((window_center_time + window_size) * self.sampling_rate + (len(ap_template) / 2.0)) 
                pass

            # slide the template over the window
            correlations = sliding_window_normalized_cross_correlation(signal[first_signal_idx : last_signal_idx], ap_template.signal_template)
            # then, retrieve the index for which we had the maximum correlation
            max_correlation_idx = np.argmax(correlations) + first_signal_idx
            # finally, create the AP
            track_aps.append(signal.times[max_correlation_idx])

    signal: IrregularlySampledSignal
    return SpikeTrain(times = Quantity(track_aps, "s"), t_start = signal.t_start, t_stop = signal.t_stop)

""", ap_signal_threshold: Quantity, sampling_rate: Quantity"""
def import_dapsys_csv_files(directory: str, ap_correlation_window_size: Quantity = Quantity(0.003, "s")):

    csv_files = [file for file in [os.path.join(directory, fname) for fname in os.listdir(directory)] \
        if os.path.isfile(file) and os.path.splitext(file)[1].lower() == ".csv"]

    # read the individual files
    pulses: Event = _read_main_pulse_file(filepaths = csv_files)
    signal: IrregularlySampledSignal = _read_signal_file(filepaths = csv_files)
    ap_tracks: List[APTrack] = _read_track_files(filepaths = csv_files, el_stimuli = pulses)
    track_aps: List[SpikeTrain] = _find_action_potentials_on_tracks(ap_tracks = ap_tracks, el_stimuli = pulses, \
        signal = signal, window_size = ap_correlation_window_size)

## This class reads Dapsys data after they have been extract in .csv format
class DapsysImporter():
	## Constructs an importer object by reading four different .csv files used for analysis
	# @param dir_path String | Path to the directory which contains four .csv files
    def __init__(self, dir_path, ap_signal_threshold = "auto", sampling_rate = 10000):

        # finally, we can try to search for the action potentials
        # we do this, by using our cross-correlation in a certain window around the latency given by our AP-tracks
        self.find_action_potentials_on_tracks(window_size = 0.001)

        # TODO find action potentials using some kind of thresholding + cross correlation
        self.find_action_potentials_per_threshold(signal_threshold = ap_signal_threshold, correlation_threshold = 0.8, window_size = 0.002)

    # TODO add comment
    def autodetermine_threshold_from_tracks(self, quantile = 0.05) -> float:
        pass

    # TODO add comment
    def find_action_potentials_per_threshold(self, signal_threshold, correlation_threshold, window_size = 0.003):
        
        # initialize our AP list
        self.action_potentials = []
        
        # get a mask for the values which are above the threshold and convert into indices by using the mask for the "index" of values
        abv_thr_idcs = np.array(range(len(self.raw_signal)))[self.raw_signal > signal_threshold] 
        # then, get the local signal maxima
        # but first, smooth the array a little bit s.t. we don't get as many extreme values
        filter_sz = int((window_size) * self.sampling_rate + 1)
        filter = np.ones(filter_sz) / filter_sz
        # convolve the filter we've defined with the 
        smoothed_sig = np.convolve(filter, self.raw_signal, mode = 'same')
        # then get the relative maxima from the smoothed signal
        loc_sig_max = argrelextrema(smoothed_sig, np.greater)[0]
        # only retain the indices which are a local maximum and above the threshold
        abv_thr_idcs = np.array(list(set(abv_thr_idcs) & set(loc_sig_max)))
        # get the length of the longest template
        longest_template_len = max([len(ap_track.ap_template) for ap_track in self.ap_tracks])

        # for each of these indices, define a small window over which we slide the AP template
        # TODO this function should also work without a template, I guess?
        print("Processing the points where the signal is above threshold " + str(signal_threshold))
        for abv_thr_idx in tqdm(abv_thr_idcs):
            # calculate the first and last indices of the signal which we window
            window_first_signal_idx = int(max(0, abv_thr_idx - window_size * self.sampling_rate - longest_template_len / 2.0))
            window_last_signal_idx = int(min(len(self.raw_signal), abv_thr_idx + window_size * self.sampling_rate + longest_template_len / 2.0))

            # store the correlation scores in this list of arrays
            correlations = []
            # now, use the information from the AP tracks to find signal artifacts that look suspiciously like APs
            for ap_track in self.ap_tracks:
                # get the signal template
                signal_template = ap_track.ap_template.signal_template
                # then, extract the signal according to the template size
                window_signal = self.raw_signal[window_first_signal_idx : window_last_signal_idx]
                # calculate the normalized cross correlation for every point in the window
                correlations.append(sliding_window_normalized_cross_correlation(window_signal, signal_template))
        
            # now, we get the index with the highest correlation and index for each of the tracks
            # so we have (track index, index of max. correlation score for this template, max. correlation score)
            correlations = [(track_idx, np.argmax(correlation_scores), max(correlation_scores)) for track_idx, correlation_scores in enumerate(correlations)]
            # then, we get the tuple for which the max. correlation was the highest
            max_correlation_track_idx, max_correlation_idx, max_correlation_value = max(correlations, key = itemgetter(2))

            # when this template scored above the threshold, we make an AP out of it
            if max_correlation_value > correlation_threshold:
                # so, we get the first and last signal indices
                ap_first_signal_idx = window_first_signal_idx + max_correlation_idx
                ap_last_signal_idx = min(len(self.raw_signal), window_first_signal_idx + max_correlation_idx + len(self.ap_tracks[max_correlation_track_idx].ap_template))
                # from this, we can calculate back to the times
                ap_t_onset = float(ap_first_signal_idx) / float(self.sampling_rate)
                ap_t_offset = float(ap_last_signal_idx) / float(self.sampling_rate)
                # and finally, we can create the AP
                ap = ActionPotential(onset = ap_t_onset, offset = ap_t_offset, raw_signal = self.raw_signal[ap_first_signal_idx : ap_last_signal_idx], verbose = False)
                self.action_potentials.append(ap)