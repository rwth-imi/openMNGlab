import numpy as np

class ActionPotential:
	onset = None
	offset = None
	dist_to_prev_stimulus = None
	total_energy = None
	
	# construct an AP class from a pandas dataframe containing only the rows for the AP
	def __init__(self, input_df):
		print(input_df)
		return


class EletricalStimulus:
	timepoint = None;
	
	# construct ES class from pandas DF containing only the stimulus rows
	def __init__(self, input_df):
		return


