# -*- coding: utf-8 -*-
"""
Created on Fri Aug 4 14:10:16 2020

@author: Radomir
"""
import os
import csv
import pandas as pd
import numpy as np
from pathlib import Path


from importers.mng_importer import MNGImporter
from typing import List
from signal_artifacts import ActionPotential
from signal_artifacts import ElectricalStimulus
from fibre_tracking import ActionPotentialTemplate


## This class reads Dapsys data after they have been extract in .csv format
class DapsysImporter(MNGImporter):
    
    template = None 
    track_times = None
    main_pulses = None 
    point_data = [] 
    
	## Constructs an importer object by reading four different .csv files used for analysis
	# @param dir_path String | Path to the directory which contains four .csv files
    def __init__(self, dir_path):
        
        print("Reading files ... ")
        
        for path in os.listdir(dir_path):
            path_short = path.split('/')[-1].lower()
            path_full = dir_path+'/'+path
            
            if 'csv' not in path_short:
                continue
            
            if 'pulses' in path_short: 
                self.main_pulses = self.get_electrical_stimuli(path_full, 'time')
                print(f'Stimuli: {path_short}', end =" | ")
            elif 'track' in path_short: 
                self.track_times = pd.read_csv(path_full, header=None, usecols=[0], names = ['time']).time.values
                print(f'Track times: {path_short}', end =" | ")
            elif 'template' in path_short: 
                vals = pd.read_csv(path_full, header=None, names=['amplitude']).amplitude.values
                self.template = ActionPotentialTemplate(vals)
                print(f'Template: {path_short}', end =" | ")
            else:
                recordings = [[]]
                with open(path_full, newline='\n') as csv_file:
                    csv_reader = csv.reader(csv_file, delimiter=',')
                    for i, row in enumerate(csv_reader):
                        recordings.append([])
                        for j, value in enumerate(row):
                            recordings[i].append(float(value))
            
                for i in range(0, len(recordings)-1, 2):
                    for j in range(0, len(recordings[i])):
                        self.point_data.append([recordings[i][j], recordings[i+1][j]])
                        
                del recordings
                print(f'Signal: {path_short}', end =" | ")

    ## Get raw signal out of excel file
    def get_raw_signal(self) -> List[float]:
        return np.array(self.point_data)[:, 1]   
    
    ## Generate segment-to-segment data from point data based on main pulses
    def get_raw_signal_split_by_stimuli(self):
        
        boundary_index=0
        list_copy = self.point_data
        boundary_list = self.main_pulses
        
        while list_copy[boundary_index][0]<self.main_pulses[0].timepoint: 
            boundary_index+=1
            
        list_copy = self.point_data[boundary_index:]
        boundary_list = self.main_pulses[1:]
        amplitudes_list = []
        
        while len(boundary_list)>0:
            while list_copy[boundary_index][0]<boundary_list[0].timepoint: 
                boundary_index+=1
                
            amplitudes_list.append([val[-1] for val in list_copy[:boundary_index]])
            
            list_copy = list_copy[boundary_index:]
            boundary_list = boundary_list[1:]
            boundary_index = 0
            
        return amplitudes_list
    
    ## Generate segment-to-segment data from point data based on main pulses (Based on previous Brain's mathematica code)
    def get_raw_timestamp_split_by_stimuli(self):
        
        boundary_index=0
        list_copy = self.point_data
        boundary_list = self.main_pulses
        
        while list_copy[boundary_index][0]<self.main_pulses[0].timepoint: 
            boundary_index+=1
            
        list_copy = self.point_data[boundary_index:]
        boundary_list = self.main_pulses[1:]
        times_list = []
        
        while len(boundary_list)>0:
            while list_copy[boundary_index][0]<boundary_list[0].timepoint: 
                boundary_index+=1
                
            times_list.append([val[0] for val in list_copy[:boundary_index]])
            
            list_copy = list_copy[boundary_index:]
            boundary_list = boundary_list[1:]
            boundary_index = 0
            
        return times_list
    
    ## Return main pulses
    # @param path_full String | directory of the file containing stimuli
    # @param time_column String | .csv column for stimuli
    def get_electrical_stimuli(self, path_full, time_column) -> List[ElectricalStimulus]:
        
        stimuli_values = pd.read_csv(path_full, header=None, usecols=[0], names = [time_column])[time_column].values
        el_stimuli = []
        
        for index, value in enumerate(stimuli_values):
            el_stimuli.append( ElectricalStimulus(value) )
        
        return el_stimuli
    
    ## For a list of 100% correct signal timestamps, return them in AP form with 30 datapoints interval. 
    def get_action_potentials(self):
        
        max_pos = np.argmax(self.template.signal_template)
        main_pulse_idx, track_time_idx, time_idx = 0, 0, 0
        aps = []
        
        while main_pulse_idx < len(self.main_pulses):
            
            # We define lower and upper boundary in order to define stimuli index of appearing AP
            if main_pulse_idx == len(self.main_pulses)-1:
                # If we eached to a last stimulus, upper boundary will be last timepoint (for the sake of processing)
                upper_border = self.point_data[-1][0]
            else:
                upper_border = self.main_pulses[main_pulse_idx+1].timepoint
            
            lower_border = self.main_pulses[main_pulse_idx].timepoint
            
            if self.track_times[track_time_idx] > lower_border and self.track_times[track_time_idx] < upper_border:
                # Iterate until we get to the corresponding track time 
                while self.point_data[time_idx][0] < self.track_times[track_time_idx]: 
                    time_idx += 1
                # I firstly extract the index of where is the actual maximum, since this is not being done by default when we extract track times from Dapsys! 
                max_idx = time_idx - 15 + np.argmax(np.array(self.point_data[time_idx-15 : time_idx+15])[:, 1])
                
                # Then I extract AP such that the index of a peak is the same as in the template 
                onset_idx = max_idx - max_pos
                offset_idx = max_idx + (30 - max_pos)
                raw_signal = np.array(self.point_data[ onset_idx : offset_idx ])[:, 1]
                timestamps = np.array(self.point_data[ onset_idx : offset_idx ])[:, 0]
                
                ap = ActionPotential(onset = timestamps[0], 
                                     offset = timestamps[-1], 
                                     raw_signal = raw_signal)
                ap.prev_stimuli["regular"] = self.main_pulses[main_pulse_idx]
                ap.features['stimulus_idx'] = main_pulse_idx
                
                aps.append(ap)
                track_time_idx += 1
            main_pulse_idx += 1
            
        return aps
    
    ## Go through complete recordings, extract above threshold signals (manual APs with 30 datapoints interval)
    # @param threshold float | Threshold value for extracting APs
    # @param length_of_signal int | Length of the part of the signal that we are extracting as AP
    def get_threshold_action_potentials(self, threshold, length_of_signal=30) -> List[ActionPotential]:
        
        aps = []
        amplitudes_list = self.get_raw_signal_split_by_stimuli()
        times_list = self.get_raw_timestamp_split_by_stimuli()
        spikes_crossings = self.get_spike_idxs(amplitudes_list, threshold)
        max_pos = np.argmax(self.template.signal_template)
        
        print('Got spike crossings.')
        
        for segment_idx, spike_timestamps in spikes_crossings.items():
            for i, time_idx in enumerate(spike_timestamps):
                
                # Similar procedure as with regular APs, fit it, so that max corresponds to maximum position of AP. 
                left_bound, ampl, tim = time_idx + ( length_of_signal - max_pos ), [], []
                
                # Iterate from right to left with adding values
                # This is an edge case when signal is overlaped with two different segments
                while left_bound >= len(amplitudes_list[segment_idx]):
                    ampl.insert(0, amplitudes_list[segment_idx+1][left_bound - len(amplitudes_list[segment_idx])])
                    tim.insert(0, times_list[segment_idx+1][left_bound - len(amplitudes_list[segment_idx])])
                    left_bound -= 1
                
                # Regular case
                while len(ampl) < length_of_signal and left_bound > 0:
                    ampl.insert(0, amplitudes_list[segment_idx][left_bound])
                    tim.insert(0, times_list[segment_idx][left_bound])
                    left_bound -= 1
                
                # If there is an overlap between the signals extract points that are missing from first part 
                if len(ampl)<length_of_signal:
                    length = len(amplitudes_list[segment_idx-1])
                    rest_indices = length - (length_of_signal - len(ampl))
                    for rest_idx in range(rest_indices, length):
                        ampl.insert(0, amplitudes_list[segment_idx-1][rest_idx])
                        tim.insert(0, times_list[segment_idx-1][rest_idx])
                 
                if(len(ampl)!=30):
                    print(f'Irregular signal with {len(ampl)}! Found a bug = some edge case has not been covered.')
                    
                raw_signal = np.array([ampl[i] for i in range(len(ampl))])
                timestamps = np.array([tim[i] for i in range(len(tim))])
                
                ap = ActionPotential(onset = timestamps[0], 
                                     offset = timestamps[-1], 
                                     raw_signal = raw_signal)
                
                ap.prev_stimuli["regular"] = self.main_pulses[segment_idx]
                ap.features['stimulus_idx'] = segment_idx
                
                aps.append(ap)
                
        return aps
    
    ## For each segment, return indices of full signal that contain above threshold amplitudes
    # @param amplitudes_list list | Seg2seg amplitudes from get_raw_signal_split_by_stimuli() function
    # @param threshold int | Threshold value
    def get_spike_idxs(self, amplitudes_list, threshold = 6, len_of_sig=30):
        
        crossing_indices = {k:[] for k in range(0, len(amplitudes_list))}
        middle_idx = 15
        
        for k, stim_int in enumerate(amplitudes_list):
            
            list_copy = stim_int 
            dropped_amount = 0
            next_spike_crossing = -1
            
            while True:
                
                rng = np.arange(middle_idx-1, len(list_copy)-2)
                found = False
                
                for i in rng: 
                    if list_copy[i]>threshold: 
                        # We add indices of signal that go above threshold
                        next_spike_crossing = i
                        found = True
                        break
            
                if found==False or (next_spike_crossing + middle_idx)>=len(list_copy):
                    break
            
                # Mathematica's approach from Brian's code, may not be the most user friendly one
                crossing_indices[k].append(dropped_amount + next_spike_crossing)
                dropped_amount += next_spike_crossing + middle_idx
                list_copy = list_copy[next_spike_crossing + middle_idx:]
        
        # Deleting signals which will not make to the length of 30: 
        last_idx = list(crossing_indices.keys())[-1]
        max_pos = np.argmax(self.template)
        
        if 0 in crossing_indices and len(crossing_indices[0])>0:
            time_idx = crossing_indices[0][0]
            if time_idx - max_pos < 0:
                print(f'Ignoring spike in first segment with index of {time_idx}')
                del crossing_indices[0][0]
            
        if len(amplitudes_list[last_idx]) and len(crossing_indices[last_idx])>0:
            time_idx = crossing_indices[last_idx][-1]
            if time_idx + ( len_of_sig - max_pos ) >= len(amplitudes_list[last_idx]):
                print(f'Ignoring spike in last segment with index of {time_idx}')
                del crossing_indices[last_idx][-1]
            
        return crossing_indices
    
    ## Generate segment - track time points based on dapsys signal
    def extract_segment_idxs_times(self):
        
        j = 0
        tt_dict = {}
        for i, mp in enumerate(self.main_pulses):
            if self.track_times[j] > self.main_pulses[i].timepoint and (i==len(self.main_pulses)-1 or self.track_times[j] < self.main_pulses[i+1].timepoint):
                tt_dict[i] = self.track_times[j]
                j += 1
        return tt_dict 

    ## this function fixes the problem with dapsys csv files that use the comma not only as csv-separator but also for decimal numbers
    # @param in_path Path where the original files are placed
    # @param out_path Path where the fixed files should be written (filenames are preserved), will be created on demand
    # @param new_separator New separator character for the CSV file
    @staticmethod
    def fix_separator_decimal_issue(in_path, out_path, new_separator = ","):

        # create the output directory if necessary
        Path(out_path).mkdir(parents = True, exist_ok = True)

        # get a list of the files in the directory and load all of them sequentially
        for path in os.listdir(in_path):
            # construct the in and out paths
            in_path_full = in_path + '\\' + path
            out_path_full = out_path + '\\' + path

            # open the input and output csv files
            with open(in_path_full, 'r', newline = '\n') as in_csv_file, open(out_path_full, 'a', newline = '\n') as out_csv_file:
                csv_reader = csv.reader(in_csv_file, delimiter = ',')
                csv_writer = csv.writer(out_csv_file, delimiter = new_separator, quoting = csv.QUOTE_NONNUMERIC, escapechar = "\\")

                # enumerate over the rows to replace every second "," with a decimal point
                for i, row in enumerate(csv_reader):
                    
                    out_row = []

                    # for every second value, append the next using a decimal point
                    for idx in range(0, len(row) - 1, 2):
                        num = float(f"{row[idx]}.{row[idx + 1]}")
                        out_row.append(num)

                    # for some files, there is something like a comment that we need to append as well
                    if len(row) % 2 != 0:
                        out_row.append(f"{row[len(row) - 1]}")

                    # then, write the new row into the output csv file
                    csv_writer.writerow(out_row)