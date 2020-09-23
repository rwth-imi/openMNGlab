from feature_extraction.feature_extractor import FeatureExtractor

from signal_artifacts import ActionPotential

## This extractor calculates the "normalized energy" for an action potential.
class NormalizedSignalEnergy(FeatureExtractor):

	def get_feature_name(self):
		return "energy"

	## Calculates the normalized signal energy for the given AP.
	# 1.) sum the squared signal values and
	# 2.) divide by the number of values for normalization
	# @param actpot The AP for which the normalized energy is calculated.
	def get_feature_value(self, actpot):
		num_values = len(actpot.raw_signal)
		
		# square the values and sum those squares up
		squared_vals = [value * value for value in actpot.raw_signal]
		total_energy = sum(squared_vals)
		
		# return the "normalized" energy
		return total_energy / num_values