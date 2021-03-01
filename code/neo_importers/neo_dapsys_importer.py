from scipy import signal
from fibre_tracking import ap_template
import os
import csv
import pandas as pd
import numpy as np
from pathlib import Path
from math import ceil, floor
from typing import List, Iterable
from operator import itemgetter, truediv
from scipy.signal import argrelextrema
from tqdm import tqdm
from quantities import Quantity, second
from neo.core.block import Block
from neo.core import Event, IrregularlySampledSignal, AnalogSignal, SpikeTrain, Segment
from typing import Union
import warnings
import traceback
import bisect

# these are imports from our own packages
from fibre_tracking import ActionPotentialTemplate, APTrack
from metrics.normalized_cross_correlation import sliding_window_normalized_cross_correlation
from neo_importers.neo_wrapper import TypeID
from neo_importers.neo_utils import quantity_concat, convert_irregularly_sampled_signal_to_analog_signal

def _get_files_with_extension(path: str, extension: str) -> List[str]:
    return [filepath for filepath in [os.path.join(path, fname) for fname in os.listdir(path)] \
        if os.path.isfile(filepath) and os.path.splitext(filepath)[1].lower() == extension]

## this function fixes the problem with dapsys csv files that use the comma not only as csv-separator but also for decimal numbers
# @param in_path Path where the original files are placed
# @param out_path Path where the fixed files should be written (filenames are preserved), will be created on demand
# @param new_separator New separator character for the CSV file
def _fix_separator_decimal_matching(in_path: str, out_path: str, new_separator = ","):
    # create the output directory if necessary
    Path(out_path).mkdir(parents = True, exist_ok = True)

    # get a list of the files in the directory and load all of them sequentially
    for in_filepath in tqdm(_get_files_with_extension(in_path, ".csv"), desc = "Converting dapsys csv exports to valid format."):
        
        out_filepath = os.path.join(out_path, os.path.split(in_filepath)[1])

        # open the input and output csv files
        with open(in_filepath, 'r', newline = '\n') as in_csv_file, \
             open(out_filepath, 'a', newline = '\n') as out_csv_file:
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

def _do_files_need_fixing(in_path: str) -> bool:
    files = _get_files_with_extension(in_path, ".csv")
    assert len(files) > 0

    with open(files[0], "r", newline = "\n") as f:
        first_line = f.readline()
        if not "." in first_line:
            return True
        if first_line.count(".") < first_line.count(","):
            return True

    return False

## Read the main pulse file which has "pulses" in its name
def _read_main_pulse_file(filepaths: List[str]) -> Event:
    try: 
        # read pulse file
        pulse_file = [file for file in filepaths if "pulses" in os.path.basename(file).lower()][0]
        pulses_df = pd.read_csv(filepath_or_buffer = pulse_file, header = None, names = ["timestamp", "comment"])
        times = Quantity(pulses_df["timestamp"], "s")

        pulses = Event(times =  times, labels = pulses_df["comment"], name = "Dapsys Main Pulse", file_origin = pulse_file)
        pulses.annotate(id = f"{TypeID.ELECTRICAL_STIMULUS.value}.0", type_id = TypeID.ELECTRICAL_STIMULUS.value)

        intervals: Quantity = np.diff(times)
        intervals = quantity_concat(intervals, np.array([float("inf")]) * second)
        pulses.array_annotate(intervals = intervals)

        return pulses
    except Exception as ex:
        traceback.print_exc()

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
            signal = Quantity(signal, signal_unit)
        else:
            signal = Quantity(signal, "dimensionless")

        result = IrregularlySampledSignal(times = times, signal = signal, name = "Irregularly Sampled Signal", file_origin = signal_file)
        result.annotate(id = f"{TypeID.RAW_DATA.value}.0", type_id = TypeID.RAW_DATA.value)
        return result

    # something might go wrong as we perform some IO operations here
    except Exception as ex:
        traceback.print_exc()

## reads the template file with the given index
def _read_template_file(filepaths: List[str], track_idx: int, sampling_rate: Quantity) -> ActionPotentialTemplate:
    try:
        # find the right file
        template_files = [file for file in filepaths if "template" in os.path.basename(file).lower() and "track" in os.path.basename(file).lower()]
        template_file = [file for file in template_files if "track" + str(track_idx) + ".csv" in file.lower()][0]
        # read and return the AP template
        template_df = pd.read_csv(filepath_or_buffer = template_file, header = None, names = ["signal_value"])
        signal_template = AnalogSignal(signal = template_df["signal_value"].values, units = "uV", sampling_rate = sampling_rate)
        return ActionPotentialTemplate(signal_template = signal_template)
    except Exception as ex:
        warnings.warn(f"""Cannot load AP template for track no. {track_idx}!""")
        # traceback.print_exc()

## reads the tracks from files which have track but not template in their name
def _read_track_files(filepaths: List[str], el_stimuli: Event, sampling_rate: Quantity) -> List[APTrack]:
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
                ap_track.ap_template = _read_template_file(filepaths = filepaths, track_idx = track_idx, sampling_rate = sampling_rate)
            except Exception as ex:
                traceback.print_exc()

            # append this to the list of ap tracks which we load
            ap_tracks.append(ap_track)
        except Exception as ex:
            traceback.print_exc()

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

## tries to estimate the sampling rate of an irregular signal by looking at the provided index and the next sample
def _imply_sampling_rate_from_irregular_signal(signal: IrregularlySampledSignal, sample_at_idx: int = 0) -> Quantity:
    if len(signal.times) < (sample_at_idx + 2):
        raise ValueError("Signal has fewer than two samples, therefore cannot imply sampling rate.")
    t_diff = signal.times[sample_at_idx + 1] - signal.times[sample_at_idx]
    return Quantity(1.0 / t_diff, "Hz")

# TODO add doxygen comment
def _find_action_potentials_on_tracks(ap_tracks: Iterable[APTrack], el_stimuli: Event, signal: Union[IrregularlySampledSignal, AnalogSignal], \
    window_size: Quantity = Quantity(0.003, "s"), sampling_rate = None) -> SpikeTrain:
    
    # TODO implement this function for analog signals and make it reusable
    if isinstance(signal, IrregularlySampledSignal):
        if sampling_rate is None:
            raise ValueError("If an irregularly sampled signal is passed, you need to set the sampling rate!")
    elif isinstance(signal, AnalogSignal):
        sampling_rate = signal.sampling_rate

    # initialize our list of action_potentials
    ap_times = []
    ap_waveforms = []
    
    # iterate over all the tracks
    for track_idx, ap_track in enumerate(ap_tracks):
        # first, get the template of our current AP track
        if ap_track.ap_template == None:
            warnings.warn(f"""No AP template for AP track no. {track_idx}! Cannot extract APs for this track.""")
            continue
        else:
            ap_template = ap_track.ap_template

        try:
            # then, slide the template over the window, calculating cross correlation for all the datapoints
            for sweep_idx, ap_latency in tqdm(zip(ap_track.sweep_idcs, ap_track.latencies), total = len(ap_track), \
                desc = f"""Processing AP Track {track_idx} with {len(ap_track)} latencies."""):
                # we need the time of the main pulse and add the latency to define the point around which we want to search
                window_center_time = el_stimuli.times[sweep_idx] + ap_latency

                # now, we define the indices of the first and last data points that we consider for our windowing
                if isinstance(signal, IrregularlySampledSignal):
                    signal: IrregularlySampledSignal
                    # find first signal index
                    first_signal_idx = bisect.bisect_left(signal.times, (window_center_time - window_size - ap_template.duration / 2))
                    # find last signal index
                    last_signal_idx = bisect.bisect_left(signal.times, (window_center_time + window_size + ap_template.duration / 2))
                elif isinstance(signal, AnalogSignal):
                    # TODO Check why this function is much slower for analog signals
                    first_signal_idx = floor((window_center_time - window_size - (ap_template.duration / 2.0)) * signal.sampling_rate) 
                    last_signal_idx = floor((window_center_time + window_size + (ap_template.duration / 2.0)) * signal.sampling_rate)

                # slide the template over the window
                correlations = sliding_window_normalized_cross_correlation(signal[first_signal_idx : last_signal_idx], ap_template.signal_template)
                # then, retrieve the index for which we had the maximum correlation
                max_correlation_idx = np.argmax(correlations) + first_signal_idx
                # finally, append the starting time and 
                ap_times.append(signal.times[max_correlation_idx])
                ap_waveforms.append(signal[max_correlation_idx : max_correlation_idx + len(ap_template)])
        except Exception as ex:
            traceback.print_exc()
                
    # sort the APs and return spiketrain object
    ap_times = sorted(ap_times)
    
    # build the waveforms array
    num_aps = len(ap_waveforms)
    max_len = max([len(ap) for ap in ap_waveforms])
    waveforms = np.zeros(shape = (num_aps, 1, max_len), dtype = np.float64) * signal.units
    for ap_idx, ap_waveform in enumerate(ap_waveforms):
        waveforms[ap_idx, 0, 0 : len(ap_waveform)] = ap_waveform.ravel()

    result = SpikeTrain(times = Quantity(ap_times, "s"), t_start = signal.t_start, t_stop = signal.t_stop, \
        name = "APs from tracks", waveforms = waveforms, sampling_rate = sampling_rate)
    result.annotate(id = f"{TypeID.ACTION_POTENTIAL.value}.0", type_id = TypeID.ACTION_POTENTIAL.value)
    return result

# TODO add comment
def _find_action_potentials_per_threshold(raw_signal: IrregularlySampledSignal, ap_tracks: Iterable[APTrack], signal_threshold: Quantity, \
    correlation_threshold: float, window_size: Union[Quantity, int] = Quantity(0.003, "s")) -> SpikeTrain:
    
    action_potentials = []    
    sampling_rate = _imply_sampling_rate_from_irregular_signal(raw_signal, sample_at_idx = 0)

    # get a mask for the values which are above the threshold and convert into indices by using the mask for the "index" of values
    abv_thr_idcs = np.array(range(len(raw_signal)))[raw_signal > signal_threshold] 
    # then, get the local signal maxima
    # but first, smooth the array a little bit s.t. we don't get as many extreme values
    if isinstance(window_size, int):
        filter_sz = window_size
    elif isinstance(window_size, Quantity):
        filter_sz = int((window_size) * sampling_rate + 1)
    else:
        raise Exception("Window size must be either an integer or time quantity")
    filter = np.ones(filter_sz, dtype = np.float) / filter_sz
    # convolve the filter we've defined with the 
    smoothed_sig = np.convolve(filter, raw_signal, mode = 'same')
    # then get the relative maxima from the smoothed signal
    loc_sig_max = argrelextrema(smoothed_sig, np.greater)[0]
    # only retain the indices which are a local maximum and above the threshold
    abv_thr_idcs = np.array(list(set(abv_thr_idcs) & set(loc_sig_max)))
    # get the length of the longest template
    longest_template_len = max([len(ap_track.ap_template) for ap_track in ap_tracks])

    # for each of these indices, define a small window over which we slide the AP template
    # TODO this function should also work without a template, I guess?
    print("Processing the points where the signal is above threshold " + str(signal_threshold))
    for abv_thr_idx in tqdm(abv_thr_idcs):
        # calculate the first and last indices of the signal which we window
        window_first_signal_idx = int(max(0, abv_thr_idx - window_size * sampling_rate - longest_template_len / 2.0))
        window_last_signal_idx = int(min(len(raw_signal), abv_thr_idx + window_size * sampling_rate + longest_template_len / 2.0))

        # store the correlation scores in this list of arrays
        correlations = []
        # now, use the information from the AP tracks to find signal artifacts that look suspiciously like APs
        for ap_track in ap_tracks:
            # get the signal template
            signal_template = ap_track.ap_template.signal_template
            # then, extract the signal according to the template size
            window_signal = raw_signal[window_first_signal_idx : window_last_signal_idx]
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
            ap_last_signal_idx = min(len(raw_signal), window_first_signal_idx + max_correlation_idx + len(ap_tracks[max_correlation_track_idx].ap_template))
            # from this, we can calculate back to the times
            ap_t_onset = float(ap_first_signal_idx) / float(sampling_rate)
            ap_t_offset = float(ap_last_signal_idx) / float(sampling_rate)
            # and finally, we can create the AP
            action_potentials.append((ap_t_onset, ap_t_offset - ap_t_onset))

    # TODO make a SpikeTrain object from the action potentials
    return None


""", ap_signal_threshold: Quantity, sampling_rate: Quantity"""
def import_dapsys_csv_files(directory: str, sampling_rate: Union[Quantity, str] = "imply", ap_correlation_window_size: Quantity = Quantity(0.003, "s")):

    block: Block = Block(name = "Base block of dapsys csv recording")
    segment: Segment = Segment(name = "This recording consists of one segment")

    csv_files = _get_files_with_extension(directory, ".csv")
    segment.events.append(_read_main_pulse_file(filepaths = csv_files))

    # read the signal file and store this irregularly sampled signal for later computations
    irregular_sig: IrregularlySampledSignal = _read_signal_file(filepaths = csv_files, signal_unit = "uV")
    segment.irregularlysampledsignals.append(irregular_sig)

    # imply sampling rate if necessary
    if isinstance(sampling_rate, str) and sampling_rate == "imply":
        sampling_rate = _imply_sampling_rate_from_irregular_signal(irregular_sig)
    # we need to convert the irregularly sampled signal to an analog signal
    analog_sig: AnalogSignal = convert_irregularly_sampled_signal_to_analog_signal(irregular_sig, sampling_rate = sampling_rate)
    analog_sig.annotate(id = f"{TypeID.RAW_DATA.value}.1", type_id = TypeID.RAW_DATA.value)
    segment.analogsignals.append(analog_sig)
    
    ap_tracks: List[APTrack] = _read_track_files(filepaths = csv_files, el_stimuli = segment.events[0], sampling_rate = sampling_rate)
    segment.spiketrains.append(_find_action_potentials_on_tracks(ap_tracks = ap_tracks, el_stimuli = segment.events[0], \
        signal = irregular_sig, window_size = ap_correlation_window_size, sampling_rate = sampling_rate))

    # other_aps: SpikeTrain = _find_action_potentials_per_threshold(raw_signal = signal, ap_tracks = ap_tracks, \
    #     signal_threshold = Quantity(0.01, "dimensionless"), correlation_threshold = 0.5)
    
    block.segments.append(segment)
    return block