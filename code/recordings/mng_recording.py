from signal_artifacts import *
from typing import Dict, List

'''
	This is a class to model a complete MNG recording.
	It encapsulates all lists of events that happen during the recording in a single class.
'''
class MNGRecording:

	# collect all the events that take place during the recording
	el_stimuli = None
	mech_stimuli = None
	ex_el_stimuli = None
	actpots = None
	raw_signal = None

	def __init__(self):
		pass
		
	# construct a recording object from the given importer, using the channel names passed as dictionaries/lists
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
			
		recording.actpots = importer.get_action_potentials(max_gap_time = max_ap_gap_time, ap_marker_channels = ap_channels, el_stimuli = recording.el_stimuli, mech_stimuli = recording.mech_stimuli)
		
		recording.raw_signal = importer.get_raw_signal_split_by_stimuli(el_stimuli = recording.el_stimuli, verbose = False)
		
		return recording