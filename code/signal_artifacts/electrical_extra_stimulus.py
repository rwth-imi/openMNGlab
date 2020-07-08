import numpy as np

'''
	**********************************
	This class models the extra electrical stimuli that are created in an experiment such as Robertos C-fibre experiment.
	That means, they are a train of spikes with...
	- a well-defined number of pulses,
	- frequency and 
	- distance to the next regular electrical stimulation of the fibre.
	**********************************
'''
class ElectricalExtraStimulus:
	onset = None
	offset = None
	
	# these are the parameters of this specific stimulation event
	number_of_pulses = None
	frequency = None
	prepulse_distance = None
		
	# construct ES class from pandas DF or series containing only the stimulus rows
	def __init__(self, extra_el_stimuli, regular_stimuli, verbose = False):		
		# get on and offset
		self.onset = extra_el_stimuli[0].get_timepoint()
		self.offset = extra_el_stimuli[-1].get_timepoint()
		
		# get number of pulses
		self.number_of_pulses = len(extra_el_stimuli)
		
		# calculate the frequency (if possible)
		# if something is wrong, set the frequency to 0
		if self.onset == self.offset or self.number_of_pulses < 2:
			self.frequency = 0
		else:
			self.frequency = self.number_of_pulses / (self.offset - self.onset)
			
		# calculate the distance to the next electrical stimulus
		self.prepulse_distance = ElectricalExtraStimulus.calc_prepulse_dist(self.offset, stimuli_list = regular_stimuli)
		
		if verbose == True:
			self.print_info()
		
	def print_info(self):
		print("Created electrical extra stimulus event:")
		print("From " + str(self.onset) + "s to " + str(self.offset) + "s.")
		print("#Pulses: " + str(self.number_of_pulses))
		print("Frequency: " + str(self.frequency) + "Hz")
		print("Prepulse distance: " + str(self.prepulse_distance) + "s")
		print("")
	
	# calculate the distance to the onset (!) of the previous electrical stimulus
	def calc_prepulse_dist(offset, stimuli_list):
		# if there are not stimuli
		# return -1 so that the feature becomes insignificant
		if not stimuli_list:
			return -1
			
		next_stimulus = ElectricalExtraStimulus.get_next_reg_stimulus(offset, stimuli_list)
		return (next_stimulus.get_timepoint() - offset)
		
		
	# go through the list of regular electrical pulses
	# to find the one that is directly behind the offset of this pulse train,
	# i.e., this electrical extra stimulus
	def get_next_reg_stimulus(offset, stimuli_list):
		index = 0
		len_list = len(stimuli_list)
		# advance through the list until the timepoint is before a regular stimulus
		while (offset > stimuli_list[index].get_timepoint()):
			index = index + 1
			# we don't want to exceed the list length
			if (index == len_list - 1):
				break
			
		return stimuli_list[index]
	
	'''
		****************************
		From here, it's only getters
		****************************
	'''
	def get_onset(self):
		return self.onset
	
	def get_offset(self):
		return self.offset
	
	def get_num_pulses(self):
		return self.number_of_pulses
	
	def get_frequency(self):
		return self.frequency

	def get_prepulse_dist(self):
		return self.prepulse_distance