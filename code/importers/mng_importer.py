from abc import ABC, abstractmethod

class MNGImporter(ABC):
	
	@abstractmethod
	def get_raw_signal(self):
		pass
		
	@abstractmethod
	def get_raw_signal_split_by_stimuli(self):
		pass
		
	@abstractmethod
	def get_action_potentials(self):
		pass
	
	@abstractmethod
	def get_electrical_stimuli(self):
		pass
	
	def get_extra_stimuli(self):
		pass
		
	def get_mechanical_stimuli(self, force_channel, threshold, max_gap_time):
		pass