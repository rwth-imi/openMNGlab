from signal_artifacts import *
from typing import Dict, List

## A class for microneurography recordings
class MNGRecording:

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

	## Constructor for the recorindg
	def __init__(self):
		pass
		
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