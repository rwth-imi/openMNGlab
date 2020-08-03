import numpy as np
from termcolor import colored

'''
	**********************************
	A class for the APs
	**********************************
'''
class ActionPotential:
	# the time of on- and offset
	onset = None
	offset = None
	duration = None
	
	# save the raw signal values
	raw_signal = None
	
	# features
	features = None
	
	# the result from clustering/fibre tracking
	implied_fibre_index = None
	
	# spike channel index
	channel_index = None
	
	# info about the electrical stimuli
	prev_stimuli = None
	
	# information about whether the AP was triggered by any stimulation event
	triggered_by = None
	CAUSAL_DIST = 0.010
	
	# constructor for the AP class
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

	# construct an AP class from a pandas dataframe containing only the rows for the AP
	def from_dataframe(input_df, time_column = "Time", signal_column = "1 Signal", channel_index = 0, verbose = False):
		# get on- and offset (in seconds) for this AP
		onset = input_df.iloc[0][time_column]
		offset = input_df.iloc[-1][time_column]
		
		ap = ActionPotential(onset = onset, offset = offset, raw_signal = input_df[signal_column].values, verbose = verbose)
		
		# set the channel index, e.g. for different marker shapes in a scatter plot
		ap.channel_index = channel_index

		return ap
				
	def print_info(self):
		print("Found action potential with:")
		print("onset = " + str(self.onset) + "s offset = " + str(self.offset) + "s")