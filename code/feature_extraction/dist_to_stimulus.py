## Calculate distance of an action potential to prev. eletrical stimulus
# @param actpot AP
# @param stimuli_list List of regular electrical stimuli
def calc_dist_to_prev_reg_el_stimulus(actpot, stimuli_list):
	# if there is no electrical stimulus:
	# return -1 so that the feature becomes insignificant
	if not stimuli_list:
		return -1, None

	prev_stimulus = find_prev_reg_el_stimulus(actpot, stimuli_list)
	dist = actpot.onset - prev_stimulus.timepoint
	return dist, prev_stimulus
	
## Finds the previous electrical stimulus by going through a sorted list of regular electrical stimuli.
# @param actpot The AP
# @param stimuli_list List of electrical stimuli, sorted in ascending order by time
def find_prev_reg_el_stimulus(actpot, stimuli_list):		
	index = 0
	
	len_list = len(stimuli_list)
	while(actpot.onset > stimuli_list[index + 1].timepoint):
		index = index + 1
		# we don't want to exceed the list length
		if (index == len_list - 1):
			break
		
	return stimuli_list[index]

'''
# calculate the distance to the onset (!) of the previous mechanical stimulus
def calculate_dist_to_prev_mech_stimulus(actpot, stimuli_list):
	# if there is no mechanical stimulus:
	# return -1 so that the feature becomes insignificant
	if not stimuli_list:
		return -1, False, None
		
	prev_stimulus = ActionPotential.find_prev_stimulus(actpot.onset, stimuli_list)
	
	# calculate the distance and check if this AP lies within the time the mechanical pressure is applied
	dist = actpot.onset - prev_stimulus.get_onset()
	lies_within = True if actpot.onset < prev_stimulus.get_offset() else False
	
	return dist, lies_within, prev_stimulus

# calculate the distance to the offset (!) of the previous electrical stimulus
def calculate_dist_to_prev_el_extra_stimulus(actpot, stimuli_list):
	# if there is no mechanical stimulus:
	# return -1 so that the feature becomes insignificant
	if not stimuli_list:
		return -1, False, None
		
	prev_stimulus = ActionPotential.find_prev_stimulus(actpot.onset, stimuli_list)
	
	# calculate the distance and check if this AP lies within the time the mechanical pressure is applied
	dist = actpot.onset - prev_stimulus.get_offset()
	lies_within = True if actpot.onset < prev_stimulus.get_offset() else False
	
	return dist, lies_within, prev_stimulus
	
# go through the (ascending) list of mech. stimuli to find the previous stimulus
# this is, according to the onset. 
# If the AP is behind the stimulus onset, the stimulus is returned
def find_prev_stimulus(actpot, stimuli_list):
	index = 0
	
	len_list = len(stimuli_list)
	while (actpot.onset > stimuli_list[index + 1].get_onset()):
		index = index + 1
		# we don't want to exceed the list length
		if (index == len_list - 1):
			break
		
	return stimuli_list[index]
'''