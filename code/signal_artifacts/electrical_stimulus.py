import numpy as np

'''
	**********************************
	A class for the electrical stimuli
	**********************************
'''
class ElectricalStimulus:
	timepoint = None;
	
	# construct ES class from pandas DF or series containing only the stimulus rows
	def __init__(self, input_data, time_column = "Time", verbose = False):
		self.timepoint = input_data[time_column]
		
		if verbose == True:
			print("Found el. stimulus signal at:")
			print("Time = " + str(self.timepoint) + "s")
			print("")
			
		return
		
	def getTimepoint(self):
		return self.timepoint


