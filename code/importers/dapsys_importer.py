# -*- coding: utf-8 -*-
"""
Created on Fri Aug 4 14:10:16 2020

@author: Radomir
"""
import os
import csv
import pandas as pd
import numpy as np

from importers.mng_importer import MNGImporter
from typing import List
from signal_artifacts import ActionPotential
from signal_artifacts import ElectricalStimulus
from fibre_tracking import ActionPotentialTemplate


class DapsysImporter(MNGImporter):
    
    template = None 
    track_times = None
    main_pulses = None 
    point_data = [] 
    
    def __init__(self, dir_path):
        '''
        Read Dapsys data which contains four files:
            Template: ActionPotentialTemplate | Average signal Dapsys generation: Cursor needs to be on a track, right mouse click -> align latency track -> align to template -> copy template to clipboard -> Ja. 
            Main pulses: List[ElectricalStimulus] | Timestamps of pulses
            Point data: list | Continuous recordings of points
            Track times: list | Timestamps of 100% sure spikes of ours
            
		Parameters
		----------
		dir_path: String | directory of the files
        '''
        
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


    def get_raw_signal(self) -> List[float]:
        '''
		Get raw signal out of excel file.
        
		Returns
		-------
		list | Seg2seg amplitudes 
		'''             
        return np.array(self.point_data)[:, 1]   
    
    
    def get_raw_signal_split_by_stimuli(self):
        '''
		Generate segment-to-segment data from point data based on main pulses.
        
        
		Returns
		-------
		amplitudes_list: list | Seg2seg amplitudes
		'''    
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
    
    
    def get_raw_timestamp_split_by_stimuli(self):
        '''
		Generate segment-to-segment data from point data based on main pulses.
        
        
		Parameters
		----------
		dir_path: String | directory of the files
        
		Returns
		-------
        times_list: list | Seg2seg timestamps
		'''    
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
    
    
    def get_electrical_stimuli(self, path_full, time_column) -> List[ElectricalStimulus]:
        '''
		Return main pulses.
        
        
		Parameters
		----------
		path_full: String | directory of the file
        
		Returns
		-------
		main_pulses: list | Electrical stimuli
		'''    
        
        stimuli_values = pd.read_csv(path_full, header=None, usecols=[0], names = [time_column])[time_column].values
        el_stimuli = []
        
        for index, value in enumerate(stimuli_values):
            el_stimuli.append( ElectricalStimulus(value) )
        
        return el_stimuli
    
    
    def get_action_potentials(self):
        '''
        For a list of 100% correct signal timestamps, return them in AP form. 
        
        Returns
        -------
        aps: List[ActionPotential] | List of correct APs. 
        '''
        
        max_pos = np.argmax(self.template.signal_template)
        main_pulse_idx, track_time_idx, time_idx = 0, 0, 0
        aps = []
        
        while main_pulse_idx < len(self.main_pulses)-1:
            
            lower_border = self.main_pulses[main_pulse_idx].timepoint
            upper_border = self.main_pulses[main_pulse_idx+1].timepoint
            
            if self.track_times[track_time_idx] > lower_border and self.track_times[track_time_idx] < upper_border:
                while self.point_data[time_idx][0] < self.track_times[track_time_idx]: 
                    time_idx += 1
                max_idx = time_idx - 15 + np.argmax(np.array(self.point_data[time_idx-15 : time_idx+15])[:, 1])
                
                onset_idx = max_idx-max_pos
                offset_idx = max_idx+(30-max_pos)
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
    
    
    def get_threshold_action_potentials(self, threshold, length_of_signal=30) -> List[ActionPotential]:
        '''
        Go through complete recordings, extract above threshold signals (manual APs)
        
        Parameters
        ----------
        spikes_crossings: dict | Template signal.
        amplitudes_list: list | Seg2seg amplitudes from get_raw_signal_split_by_stimuli() function.
        times_list: list | Seg2seg timestamps from get_raw_signal_split_by_stimuli() function.
        max_pos: int | Index for highest magnitude within 30ms (list with length of 30) template signal.
    
        Returns
        -------
        signals: List[ActionPotential] | list of Action potentials. 
        '''
        aps = []
        amplitudes_list = self.get_raw_signal_split_by_stimuli()
        times_list = self.get_raw_timestamp_split_by_stimuli()
        spikes_crossings = self.get_spike_idxs(amplitudes_list, threshold)
        max_pos = np.argmax(self.template.signal_template)
        
        print('Got spike crossings.')
        
        for segment_idx, spike_timestamps in spikes_crossings.items():
            for i, time_idx in enumerate(spike_timestamps):
                
                left_bound, ampl, tim = time_idx + ( length_of_signal - max_pos ), [], []
                
                while left_bound >= len(amplitudes_list[segment_idx]):
                    ampl.insert(0, amplitudes_list[segment_idx+1][left_bound - len(amplitudes_list[segment_idx])])
                    tim.insert(0, times_list[segment_idx+1][left_bound - len(amplitudes_list[segment_idx])])
                    left_bound -= 1
                
                while len(ampl) < length_of_signal and left_bound > 0:
                    ampl.insert(0, amplitudes_list[segment_idx][left_bound])
                    tim.insert(0, times_list[segment_idx][left_bound])
                    left_bound -= 1
                
                if len(ampl)<length_of_signal:
                    length = len(amplitudes_list[segment_idx-1])
                    rest_indices = length - (length_of_signal - len(ampl))
                    for rest_idx in range(rest_indices, length):
                        ampl.insert(0, amplitudes_list[segment_idx-1][rest_idx])
                        tim.insert(0, times_list[segment_idx-1][rest_idx])
                 
                if(len(ampl)!=30):
                    print(f'Irregular signal with {len(ampl)}! Found a bug.')
                    
                raw_signal = np.array([ampl[i] for i in range(len(ampl))])
                timestamps = np.array([tim[i] for i in range(len(tim))])
                
                ap = ActionPotential(onset = timestamps[0], 
                                     offset = timestamps[-1], 
                                     raw_signal = raw_signal)
                
                ap.prev_stimuli["regular"] = self.main_pulses[segment_idx]
                ap.features['stimulus_idx'] = segment_idx
                
                aps.append(ap)
                
        return aps
    
    
    def get_spike_idxs(self, amplitudes_list, threshold = 6, len_of_sig=30):
        '''
        For each segment, return indices that contain above threshold amplitudes.
        
    	Parameters
    	----------
    	amplitudes_list: list | Seg2seg amplitudes from get_raw_signal_split_by_stimuli() function.
        threshold: int | Threshold value.
        
        Returns
    	-------
    	crossing_indices: dict | Crossing indices for each segment
        ''' 
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
                        next_spike_crossing = i
                        found = True
                        break
            
                if found==False or (next_spike_crossing + middle_idx)>=len(list_copy):
                    break
            
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
    
    def extract_segment_idxs_times(self):
        '''
        Generate segment - track time points based on dapsys signal. 
        
        Returns
        -------
        tt_dict: dict | Segment - track time points.
        '''
        j = 0
        tt_dict = {}
        for i, mp in enumerate(self.main_pulses):
            if self.track_times[j] > self.main_pulses[i].timepoint and (i==len(self.main_pulses)-1 or self.track_times[j] < self.main_pulses[i+1].timepoint):
                tt_dict[i] = self.track_times[j]
                j += 1
        return tt_dict 