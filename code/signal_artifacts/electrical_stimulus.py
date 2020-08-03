import numpy as np

'''
	**********************************
	A class for the electrical stimuli
	**********************************
'''
class ElectricalStimulus:
	timepoint = None
	interval_raw_signal = None
	interval_length = 0
	df_index = None
	
	def __init__(self, timepoint, verbose = False):
		self.timepoint = timepoint
		
		if verbose == True:
			self.print_info()
	
	# construct ES class from pandas DF or series containing only the stimulus rows
	def from_dataframe(input_data, df_index, time_column = "Time", verbose = False):
		es = ElectricalStimulus(timepoint = input_data[time_column], verbose = verbose)
		es.df_index = df_index
		return es
		
	def print_info(self):
		print("Found el. stimulus signal at:")
		print("Time = " + str(self.timepoint) + "s")
