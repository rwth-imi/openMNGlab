import numpy as np

'''
	**********************************
	A class for the mechanical stimuli
	**********************************
'''
class MechanicalStimulus:
	onset = None
	offset = None
	amplitude = None
	
	def __init__(self, onset, offset, raw_values, verbose = False):
		self.onset = onset
		self.offset = offset
		self.amplitude = max(raw_values)
		
		if verbose == True:
			self.print_info()
	
	# calls the constructor on information coming from a dataframe
	# used e.g., by the spike importer
	def from_dataframe(input_df, time_column = "Time", force_column = "3 Force", verbose = False):
		onset = input_df.iloc[0][time_column]
		offset = input_df.iloc[-1][time_column]
		force_values = input_df[force_column].values
		
		return MechanicalStimulus(onset = onset, offset = offset, raw_values = force_values, verbose = verbose)
	
	def print_info(self):
		print("Found mechanical stimulus:")
		print("onset = " + str(self.onset) + "s offset = " + str(self.offset) + "s")
		print("amplitude = " + str(self.amplitude) + "mN")
	
	def get_onset(self):
		return self.onset
		
	def get_offset(self):
		return self.offset
		
	def get_amplitude(self):
		return self.amplitude