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
	
	# the channel index to distinguish e.g. between different spike templates
	channel_index = None
	
	dist_to_prev_reg_el_stimulus = None
	prev_el_stimulus = None
	
	norm_energy = None
	
	# AP might be caused by mechanical stimulation
	# if it lies within on- and offset of the mechanical stimulus
	dist_to_prev_mech_stimulus = None
	belonging_to_mechanical_stimulus = False
	prev_mech_stimulus = None
	
	# here, the AP might also be caused by the extra pulse!
	# so, pick a range of e.g., 10ms for which the stimulus is registered as 
	# immediately caused by a stimulus in a train of extra stimulus pulses
	dist_to_prev_el_extra_stimulus = None
	pulse_causal_distance = 0.010 
	belonging_to_extra_stimulus = False
	prev_el_extra_stimulus = None
	
	def __init__(self, onset, offset, raw_signal, el_stimuli = [], mech_stimuli = [], el_extra_stimuli = [], verbose = False):
		# set onset and offset of the AP
		self.onset = onset
		self.offset = offset
		
		# calculated the sum-squares energy of the AP signal
		self.norm_energy = ActionPotential.calc_normalized_energy(signal_values = raw_signal)
		
		# calculate the distance to the previous electrical and mechanical stimuli
		self.dist_to_prev_reg_el_stimulus, self.prev_el_stimulus = ActionPotential.calc_dist_to_prev_reg_el_stimulus(ap_onset = self.onset, stimuli_list = el_stimuli)
		
		# get distance to onset of previous mechanical stimulus and check if the AP might be caused by it
		self.dist_to_prev_mech_stimulus, self.belonging_to_mechanical_stimulus, self.prev_mech_stimulus = ActionPotential.calculate_dist_to_prev_mech_stimulus(ap_onset = self.onset, stimuli_list = mech_stimuli)
		
		# get distance to offset of previous electrical extra stimulus and check if the AP might be caused by it
		self.dist_to_prev_el_extra_stimulus, self.belonging_to_extra_stimulus, self.prev_el_extra_stimulus = ActionPotential.calculate_dist_to_prev_el_extra_stimulus(ap_onset = self.onset, stimuli_list = el_extra_stimuli)
		
		if verbose == True:
			self.print_info()

	# construct an AP class from a pandas dataframe containing only the rows for the AP
	def from_dataframe(input_df, el_stimuli = [], mech_stimuli = [], el_extra_stimuli = [], time_column = "Time", signal_column = "1 Signal", channel_index = 0, verbose = False):
		# get on- and offset (in seconds) for this AP
		onset = input_df.iloc[0][time_column]
		offset = input_df.iloc[-1][time_column]
		
		ap = ActionPotential(onset = onset, offset = offset, raw_signal = input_df[signal_column].values, el_stimuli = el_stimuli, mech_stimuli = mech_stimuli, el_extra_stimuli = el_extra_stimuli, verbose = verbose)
		
		# set the channel index, e.g. for different marker shapes in a scatter plot
		ap.channel_index = channel_index

		return ap
		
	def print_info(self):
		print("Found action potential with:")
		print("onset = " + str(self.onset) + "s offset = " + str(self.offset) + "s")
		print("normalized energy = " + str(self.norm_energy))
		print("dist. to prev. el. stimulus = " + str(self.dist_to_prev_reg_el_stimulus) + "s")
		print("dist. to prev. mech. stimulus = " + str(self.dist_to_prev_mech_stimulus) + "s")
		if self.belonging_to_mechanical_stimulus == True:
			print(colored("WARNING: the AP might be caused by this mechanical stimulus!", 'red'))
		print("dist. to prev. el. extra stimulus = " + str(self.dist_to_prev_el_extra_stimulus) + "s")
		if self.belonging_to_extra_stimulus == True:
			print(colored("WARNING: the AP might be caused by this electrical extra stimulus!", 'red'))
	
	# calculate the distance to the onset (!) of the previous mechanical stimulus
	def calculate_dist_to_prev_mech_stimulus(ap_onset, stimuli_list):
		# if there is no mechanical stimulus:
		# return -1 so that the feature becomes insignificant
		if not stimuli_list:
			return -1, False, None
			
		prev_stimulus = ActionPotential.find_prev_stimulus(ap_onset, stimuli_list)
		
		# calculate the distance and check if this AP lies within the time the mechanical pressure is applied
		dist = ap_onset - prev_stimulus.get_onset()
		lies_within = True if ap_onset < prev_stimulus.get_offset() else False
		
		return dist, lies_within, prev_stimulus
	
	# calculate the distance to the offset (!) of the previous electrical stimulus
	def calculate_dist_to_prev_el_extra_stimulus(ap_onset, stimuli_list):
		# if there is no mechanical stimulus:
		# return -1 so that the feature becomes insignificant
		if not stimuli_list:
			return -1, False, None
			
		prev_stimulus = ActionPotential.find_prev_stimulus(ap_onset, stimuli_list)
		
		# calculate the distance and check if this AP lies within the time the mechanical pressure is applied
		dist = ap_onset - prev_stimulus.get_offset()
		lies_within = True if ap_onset < prev_stimulus.get_offset() else False
		
		return dist, lies_within, prev_stimulus
		
	# go through the (ascending) list of mech. stimuli to find the previous stimulus
	# this is, according to the onset. 
	# If the AP is behind the stimulus onset, the stimulus is returned
	def find_prev_stimulus(ap_onset, stimuli_list):
		index = 0
		
		len_list = len(stimuli_list)
		while (ap_onset > stimuli_list[index + 1].get_onset()):
			index = index + 1
			# we don't want to exceed the list length
			if (index == len_list - 1):
				break
			
		return stimuli_list[index]
			
	
	# calculate distance to prev. eletrical stimulus
	def calc_dist_to_prev_reg_el_stimulus(ap_onset, stimuli_list):
		# if there is no electrical stimulus:
		# return -1 so that the feature becomes insignificant
		if not stimuli_list:
			return -1, None
	
		prev_stimulus = ActionPotential.find_prev_reg_el_stimulus(ap_onset, stimuli_list)
		dist = ap_onset - prev_stimulus.get_timepoint()
		return dist, prev_stimulus
		
	# go through the (ascending) list of el. stimuli to find the previous stimulus
	# this is, according to the timestamp
	def find_prev_reg_el_stimulus(ap_onset, stimuli_list):		
		index = 0
		
		len_list = len(stimuli_list)
		while(ap_onset > stimuli_list[index + 1].get_timepoint()):
			index = index + 1
			# we don't want to exceed the list length
			if (index == len_list - 1):
				break
			
		return stimuli_list[index]
			
	# calculate a crude approximation of the "signal energy":
	# 1.) sum the squared signal values and
	# 2.) divide by the number of values for normalization
	def calc_normalized_energy(signal_values):
		num_values = len(signal_values)
		
		# square the values and sum those squares up
		squared_vals = [value * value for value in signal_values]
		total_energy = sum(squared_vals)
		
		# return the "normalized" energy
		return total_energy / num_values
		
	# only getters from here on	
	def get_prev_reg_el_stimulus(self):
		return self.prev_el_stimulus
		
	def get_dist_to_prev_reg_el_stimulus(self):
		return self.dist_to_prev_reg_el_stimulus
		
	def get_dist_to_prev_mechl_stimulus(self):
		return self.dist_to_prev_mech_stimulus
		
	def get_dist_to_prev_el_extra_stimulus(self):
		return self.dist_to_prev_el_extra_stimulus
		
	def get_normalized_energy(self):
		return self.norm_energy
		
	def get_channel_index(self):
		return self.channel_index
		
	def get_onset(self):
		return self.onset
	
	def get_offset(self):
		return self.offset