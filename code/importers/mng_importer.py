from abc import ABC, abstractmethod
from typing import List
from signal_artifacts import ActionPotential, ElectricalStimulus

from numpy import ndarray

## The interface for a general MNG importer.
class MNGImporter(ABC):
	
	## Returns the raw signal values from the recording
	@abstractmethod
	def get_raw_signal(self) -> List[ndarray]:
		pass
		
	## Returns the raw signal, but split by the regular electrical stimuli
	@abstractmethod
	def get_raw_signal_split_by_stimuli(self) -> List[List[ndarray]]:
		pass
		
	## Returns a list of all action potentials in the recording
	@abstractmethod
	def get_action_potentials(self) -> List[ActionPotential]:
		pass
	
	## Returns a list of all the regular electrical stimuli in the recording
	@abstractmethod
	def get_electrical_stimuli(self) -> List[ElectricalStimulus]:
		pass
	
	## If present in the format, an importer can implement this function to return all burst of "extra stimuli"
	def get_extra_stimuli(self):
		pass
		
	## If needed, use this function to return/retrieve mechanical stimulation of the C-fibres
	def get_mechanical_stimuli(self, force_channel, threshold, max_gap_time):
		pass