from abc import ABC, abstractmethod
from typing import List
from signal_artifacts import ActionPotential, ElectricalStimulus

class MNGImporter(ABC):
	
	@abstractmethod
	def get_raw_signal(self) -> List[float]:
		pass
		
	@abstractmethod
	def get_raw_signal_split_by_stimuli(self) -> List[List[float]]:
		pass
		
	@abstractmethod
	def get_action_potentials(self) -> List[ActionPotential]:
		pass
	
	@abstractmethod
	def get_electrical_stimuli(self) -> List[ElectricalStimulus]:
		pass
	
	def get_extra_stimuli(self):
		pass
		
	def get_mechanical_stimuli(self, force_channel, threshold, max_gap_time):
		pass