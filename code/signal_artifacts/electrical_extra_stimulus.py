import numpy as np

## This class models electrical extra stimuli as they occured in one of Roberto's experiment files.
# These extra stimuli are interposed between the regular stimuli to provoke a latency shift and usually come in groups.
# Therefore, we decided to give them attributes such as the number of pulses, the frequency of these pulses and the prepulse distance, since these appear to be important attributes. \n
# See also signal_artifacts.electrical_stimulus.ElectricalStimulus !
# \author Fabian Schlebusch, fabian.schlebusch@rwth-aachen.de
class ElectricalExtraStimulus:
	## Onset of the first stimulus in the group (in s)
	onset = None
	## Offset of the last stimulus in the group (in s)
	offset = None
	
	## Number of pulses in this extra stimulus group
	number_of_pulses = None
	## The frequency of the pulses (0 if only a single pulse)
	frequency = None
	## Distance to the next regular electrical stimulus/pulse (in s).
	prepulse_distance = None
		
	## Constructor to create an extra stimulus object from a list of electrical stimuli belonging to this group of pulses.
	# @param extra_el_stimuli List of the electrical stimuli that belong to this group of extra pulses.
	# @param regular_stimuli List of the regular electrical stimuli in the recording, i.e. the main pulses.
	def __init__(self, extra_el_stimuli, regular_stimuli, verbose = False):		
		# get on and offset
		self.onset = extra_el_stimuli[0].timepoint
		self.offset = extra_el_stimuli[-1].timepoint
		
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
		
	## Print some info about the extra stimuli burst for debugging purposes.
	def print_info(self):
		print("Created electrical extra stimulus event:")
		print("From " + str(self.onset) + "s to " + str(self.offset) + "s.")
		print("#Pulses: " + str(self.number_of_pulses))
		print("Frequency: " + str(self.frequency) + "Hz")
		print("Prepulse distance: " + str(self.prepulse_distance) + "s")
		print("")
	
	## Calculates the distance to the onset (!) of the previous electrical stimulus
	# @param stimuli_list List of the regular electrical stimuli in the current MNG recording.
	# @return Calculated prepulse distance.
	def calc_prepulse_dist(offset, stimuli_list):
		# if there are not stimuli
		# return -1 so that the feature becomes insignificant
		if not stimuli_list:
			return -1
			
		next_stimulus = ElectricalExtraStimulus.get_next_reg_stimulus(offset, stimuli_list)
		return (next_stimulus.timepoint - offset)
		
		
	## Go through the list of regular electrical pulses to find the one that is directly behind the offset of this pulse train.
	# @param stimuli_list List of the regular electrical stimuli in the recording.
	# @return The electrical stimulus following this electrical stimulus.
	def get_next_reg_stimulus(offset, stimuli_list):
		index = 0
		len_list = len(stimuli_list)
		# advance through the list until the timepoint is before a regular stimulus
		while (offset > stimuli_list[index].timepoint):
			index = index + 1
			# we don't want to exceed the list length
			if (index == len_list - 1):
				break
			
		return stimuli_list[index]