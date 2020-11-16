from feature_extraction.feature_extractor import FeatureExtractor

from signal_artifacts import ActionPotential, ElectricalStimulus
from recordings import MNGRecording

## Calculate distance of an action potential to prev. eletrical stimulus
class ResponseLatency(FeatureExtractor):

	## keeps a list of the regular stimuli
	regular_el_stimuli = None

	## Constructs this feature extractor.
	# @param regular_el_stimuli The list of regular electrical stimuli, so that the response latency can be calculated.
	def __init__(self, regular_el_stimuli):
		self.regular_el_stimuli = regular_el_stimuli

	def get_feature_name(self):
		return "latency"

	## Calculate distance of an action potential to prev. eletrical stimulus
	# @param actpot AP
	def get_feature_value(self, actpot):
		prev_stimulus = MNGRecording.get_prev_stimulus(actpot, self.regular_el_stimuli)
		
		if prev_stimulus == None:
			return -1
		else:
			dist = actpot.onset - prev_stimulus.timepoint
			return dist
	