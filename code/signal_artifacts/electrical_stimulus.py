import numpy as np

'''
	**********************************
	A class for the electrical stimuli
	**********************************
'''
class ElectricalStimulus:
	timepoint = None;
	interval_raw_signal = None;
	interval_length = 0
	
	# construct ES class from pandas DF or series containing only the stimulus rows
	def __init__(self, input_data, time_column = "Time", verbose = False):
		self.timepoint = input_data[time_column]
		
		if verbose == True:
			print("Found el. stimulus signal at:")
			print("Time = " + str(self.timepoint) + "s")
			print("")
			
		return
		
	def get_timepoint(self):
		return self.timepoint
		
	def set_interval_raw_signal(self, raw_signal):
		self.interval_raw_signal = raw_signal
		
	def get_interval_raw_signal(self):
		return self.interval_raw_signal

	def set_interval_length(self, interval_length):
		self.interval_length = interval_length
	
	def get_interval_length(self):
		return self.interval_length
