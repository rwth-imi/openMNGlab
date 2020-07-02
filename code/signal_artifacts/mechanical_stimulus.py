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
	
	def __init__(self, input_df, time_column = "Time", force_column = "3 Force", verbose = False):
		self.onset = input_df.iloc[0][time_column]
		self.offset = input_df.iloc[-1][time_column]
		
		force_values = input_df[force_column].values
		self.amplitude = max(force_values)
		
		if verbose == True:
			print("Found mechanical stimulus:")
			print("onset = " + str(self.onset) + "s offset = " + str(self.offset) + "s")
			# print("values = " + str(force_values))
			print("amplitude = " + str(self.amplitude) + "mN")
			
		return
		
	def get_onset(self):
		return self.onset
		
	def get_offset(self):
		return self.offset
		
	def get_amplitude(self):
		return self.amplitude