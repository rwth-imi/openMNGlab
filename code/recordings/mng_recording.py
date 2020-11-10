from signal_artifacts import *
from typing import Dict, List
from recordings.sweep import Sweep
from math import floor

## A class for microneurography recordings
class MNGRecording:

	## Sweeps, i.e. the interval from one eletrical stimulus to the next
	sweeps = None
	## Keep a list of all AP tracks in the recording
	ap_tracks = None
	## List of regular electrical stimuli. See signal_artifacts.electrical_stimulus.ElectricalStimulus
	el_stimuli = None
	## List of mechanical stimuli. See signal_artifacts.mechanical_stimulus.MechanicalStimulus
	mech_stimuli = None
	## List of extra electrical stimuli. See signal_artifacts.electrical_extra_stimulus.ElectricalExtraStimulus
	ex_el_stimuli = None
	## List of action potentials. See signal_artifacts.action_potential.ActionPotential
	actpots = None
	## List of raw signal values in this recording
	raw_signal = None
	## The sampling rate of this recording
	sampling_rate = None
	## The starting time of this recording
	t_start = None
	## The end time of this recording
	t_end = None

	## Constructor for the recording
	# @param el_stimuli List of the electrical stimuli aka main pulses in the recording
	# @param mech_stimuli List of mechanical stimulation events
	# @param extra_el_stimuli List of "extra" stimuli bursts as in Roberto's experiment
	# @param actpots List of action potentials in this recording
	def __init__(self, raw_signal, el_stimuli, actpots, t_start, t_end, sampling_rate = 20000, mech_stimuli = None, extra_el_stimuli = None):
		# assign simple attributes about the recording
		self.t_start, self.t_end = t_start, t_end
		self.sampling_rate = sampling_rate

		# now, assign the signal and signal artifacts
		self.raw_signal = raw_signal
		self.actpots = actpots
		self.el_stimuli = el_stimuli

		# the optional other kinds of fibre stimulation
		self.mech_stimuli = mech_stimuli
		self.ex_el_stimuli = extra_el_stimuli
		
	## Construct a recording object from the given importer, using the channel names passed as dictionaries/lists
	# @param importer Spike/Dapsys importer from which the information should be extracted
	# @stimulus_channels Dictionary with keys "regular_electrical", "force", "extra_electrical" and channel names as values
	# @ap_channels List of column names for channels with contain APs
	# @force_threshold Force threshold passed on to the importer for extraction of force stimulus events
	# @max_ap_gap_time Max gap time between two values s.t. they belong to the same AP, is passed on to the importer
	# TODO: this will certainly not work with the Dapsys importer!!!
	def from_importer(importer, stimulus_channels: Dict[str, str], ap_channels: List[str], force_threshold = 0.5, max_ap_gap_time = 0.05):
		
		recording = MNGRecording()
		
		if "regular_electrical" in stimulus_channels:
			recording.el_stimuli = importer.get_electrical_stimuli(regular_stimulus_channel = stimulus_channels["regular_electrical"])
		else:
			# we need to set a default value here, in case that extra stimuli events are given but no regular stimulation channel was specified
			recording.el_stimuli = []
			
		if "force" in stimulus_channels:
			recording.mech_stimuli = importer.get_mechanical_stimuli(force_channel = stimulus_channels["force"], threshold = force_threshold, max_gap_time = 0.005)
			
		if "extra_electrical" in stimulus_channels:
			recording.ex_el_stimuli = importer.get_extra_stimuli(extra_stimulus_channel = stimulus_channels["extra_electrical"], regular_el_stimuli = recording.el_stimuli)
			
		recording.actpots = importer.get_action_potentials(max_gap_time = max_ap_gap_time, ap_marker_channels = ap_channels)
		
		recording.raw_signal = importer.get_raw_signal_split_by_stimuli(el_stimuli = recording.el_stimuli, verbose = False)
		
		recording.t_start, recording.t_end = importer.get_time_range()
		recording.sampling_rate = importer.sampling_rate
		
		return recording
		
	## Finds the previous electrical stimulus by going through the sorted list of regular electrical stimuli.
	# @param actpot The AP
	def get_prev_el_stimulus(actpot, el_stimuli):
		index = 0

		len_list = len(el_stimuli)
		while(actpot.onset > el_stimuli[index + 1].timepoint):
			index = index + 1
			# we don't want to exceed the list length
			if (index == len_list - 1):
				break
			
		return el_stimuli[index]
		
	## For certain analysis, e.g., for AP tracking using track correlation, we need to split the recording into recordings.Sweep objects.
	def split_into_sweeps(self):
		sweeps = []
		# iterate over all the electrical stimuli to extract their following sweeps/intervals
		for idx, el_stim in enumerate(self.el_stimuli):
		
			raw_signal = self.raw_signal[idx]
			
			# if this is not the last stimulus, take the interval towards the next one
			if (idx + 1 < len(self.el_stimuli)):
				next_stim = self.el_stimuli[idx + 1]
				actpots = [ap for ap in self.actpots if ap.onset > el_stim.timepoint and ap.onset < next_stim.timepoint]
				t_end = next_stim.timepoint
			# if this is the last stimulus, take the recording until the end
			else:
				actpots = [ap for ap in self.actpots if ap.onset > el_stim.timepoint]
				t_end = self.t_end
			
			sweep = Sweep(stimulus = el_stim, actpots = actpots, raw_signal = raw_signal, t_start = el_stim.timepoint, t_end = t_end)
			# append this sweep to the existing list of sweeps
			sweeps.append(sweep)
			
		self.sweeps = sweeps
		return sweeps