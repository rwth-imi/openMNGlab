import numpy as np

'''
	**********************************
	A class for the APs
	**********************************
'''
class ActionPotential:
	onset = None
	offset = None
	dist_to_prev_el_stimulus = None
	dist_to_prev_mech_stimulus = None
	norm_energy = None
	
	# construct an AP class from a pandas dataframe containing only the rows for the AP
	def __init__(self, input_df, el_stimuli, mech_stimuli, time_column = "Time", signal_column = "1 Signal", verbose = False):
		# get on- and offset (in seconds) for this AP
		self.onset = input_df.iloc[0][time_column]
		self.offset = input_df.iloc[-1][time_column]
	
		# calculated the sum-squares energy of the AP signal
		self.norm_energy = ActionPotential.calculateNormalizedEnergy(signal_values = input_df[signal_column].values)
		
		# calculate the distance to the previous electrical and mechanical stimuli
		self.dist_to_prev_el_stimulus = ActionPotential.calculateDistToPrevElStimulus(ap_onset = self.onset, stimuli_list = el_stimuli)
		self.dist_to_prev_mech_stimulus = ActionPotential.calculateDistToPrevMechStimulus(ap_onset = self.onset, stimuli_list = mech_stimuli)
		
		if verbose == True:
			print("Found action potential with:")
			print("onset = " + str(self.onset) + "s offset = " + str(self.offset) + "s")
			print("normalized energy = " + str(self.norm_energy))
			print("dist. to prev. el. stimulus = " + str(self.dist_to_prev_el_stimulus) + "s")
			print("dist. to prev. mech. stimulus = " + str(self.dist_to_prev_mech_stimulus) + "s")
			print("")
			
		return
	
	# calculate the distance to the onset (!) of the previous electrical stimulus
	def calculateDistToPrevMechStimulus(ap_onset, stimuli_list):
		# if there is no mechanical stimulus:
		# return -1 so that the feature becomes insignificant
		if not stimuli_list:
			return -1
			
		prev_stimulus = ActionPotential.getPreviousMechanicalStimulus(ap_onset, stimuli_list)
		return (ap_onset - prev_stimulus.getOnset())
		
		
	# go through the (ascending) list of mech. stimuli to find the previous stimulus
	# this is, according to the onset. 
	# If the AP is behind the stimulus onset, the stimulus is returned
	def getPreviousMechanicalStimulus(ap_onset, stimuli_list):
		index = 0
		
		len_list = len(stimuli_list)
		while (ap_onset > stimuli_list[index + 1].getOnset()):
			index = index + 1
			# we don't want to exceed the list length
			if (index == len_list - 1):
				break
			
		return stimuli_list[index]
			
	
	# calculate distance to prev. eletrical stimulus
	def calculateDistToPrevElStimulus(ap_onset, stimuli_list):
		prev_stimulus = ActionPotential.getPreviousElectricalStimulus(ap_onset, stimuli_list)
		return (ap_onset - prev_stimulus.getTimepoint())
		
	# go through the (ascending) list of el. stimuli to find the previous stimulus
	# this is, according to the timestamp
	def getPreviousElectricalStimulus(ap_onset, stimuli_list):
		index = 0
		
		len_list = len(stimuli_list)
		while(ap_onset > stimuli_list[index + 1].getTimepoint()):
			index = index + 1
			# we don't want to exceed the list length
			if (index == len_list - 1):
				break
			
		return stimuli_list[index]
	
	# calculate a crude approximation of the "signal energy":
	# 1.) sum the squared signal values and
	# 2.) divide by the number of values for normalization
	def calculateNormalizedEnergy(signal_values):
		num_values = len(signal_values)
		
		# square the values and sum those squares up
		squared_vals = [value * value for value in signal_values]
		total_energy = sum(squared_vals)
		
		# return the "normalized" energy
		return total_energy / num_values
		
	def getDistanceToPreviousElectricalStimulus(self):
		return self.dist_to_prev_el_stimulus
		
	def getDistanceToPreviousMechanicalStimulus(self):
		return self.dist_to_prev_mech_stimulus
		
	def getNormalizedEnergy(self):
		return self.norm_energy