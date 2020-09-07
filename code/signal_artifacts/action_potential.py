import numpy as np
from termcolor import colored

## @package signal_artifacts
# This module contains the different signal_artifacts and corresponding events that might occur during an recordings.mng_recording.MNGRecording.

## A single action potential (AP) in a recording.
class ActionPotential:
	## The onset of this AP (in seconds).
	onset = None
	## The offset of this AP (in seconds).
	offset = None
	## The implied duration of this AP.
	duration = None
	
	## The raw signal values that have been extracted from the recording.
	raw_signal = None
	
	## A dictionary(!!!) where the features as imputed by the feature extraction can be saved.
	# usage: e.g., my_ap.features["latency"] = calculate_latency(...)
	features = None
	
	## Some algorithms use this variable to store the "imputed" fibre index.
	# e.g., fibre_tracking.dbscan_clustering.DBSCANClustering writes its prediction into this variable.
	# In the future, this variable will probably be kicked out in favour of a C-fibre object that bundles information in a more "real-life entity".
	implied_fibre_index = None
	
	## The index of the spike channel from which this action potential was extracted.
	# See importers.spike_importer.SpikeImporter for further info.
	channel_index = None
	
	## The last stimulus of each kind (i.e., regular electrical, mechanical, ...) is tracked in this dictionary.
	# We agreed on some nomenclature to store these stimuli in the dict without causing too many conflicts:
	# "regular": the previous regular electrical stimulus
	# "mechanical": the previous mechanical stimulus
	# "extra_electrical": the previous electrical extra stimulus
	prev_stimuli = None
	
	## If a stimulus event triggers an AP, keep a reference from the AP to the stimulus event.
	# e.g., force events may be causing multiple APs, then keep a reference from the AP to the event which caused it.
	triggered_by = None
	
	## This is the max. time for which we assume that there is a causal link between a stimulus and a triggered AP.
	# some algorithms use this constant to make a link between the two objects.
	CAUSAL_DIST = 0.010
	
	## Constructs an AP object
	# @param onset Onset of the AP (s)
	# @param offset Offset of the AP (s)
	# @param raw_signal The raw values from the MNG recording for this particular AP
	# @param verbose Check True if the AP class should print some info about itself upon creation.
	def __init__(self, onset, offset, raw_signal, verbose = False):
		# set some fundamental attributes of the AP
		self.onset = onset
		self.offset = offset
		self.duration = (offset - onset)
		self.raw_signal = raw_signal
		self.features = dict()
		self.prev_stimuli = dict()
	
		if verbose == True:
			self.print_info()

	## Construct an AP class from a pandas dataframe which contains only the rows for this AP
	# @param input_df The pandas dataframe object
	# @param time_column Name of the column which contains the time stamps
	# @param signal_column Name of the column which contains the signal values
	# @param channel_index Index of the channel from which the AP was extracted
	def from_dataframe(input_df, time_column = "Time", signal_column = "1 Signal", channel_index = 0, verbose = False):
		# get on- and offset (in seconds) for this AP
		onset = input_df.iloc[0][time_column]
		offset = input_df.iloc[-1][time_column]
		
		ap = ActionPotential(onset = onset, offset = offset, raw_signal = input_df[signal_column].values, verbose = verbose)
		
		# set the channel index, e.g. for different marker shapes in a scatter plot
		ap.channel_index = channel_index

		return ap
				
	## Prints info about this action potential, e.g., for debugging purposes
	def print_info(self):
		print("Found action potential with:")
		print("onset = " + str(self.onset) + "s offset = " + str(self.offset) + "s")