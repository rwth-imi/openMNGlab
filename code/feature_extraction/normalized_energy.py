'''
	This method calculates the "normalized energy" for an action potential
	1.) sum the squared signal values and
	2.) divide by the number of values for normalization
'''
def calc_normalized_energy(actpot):
	num_values = len(actpot.raw_signal)
	
	# square the values and sum those squares up
	squared_vals = [value * value for value in actpot.raw_signal]
	total_energy = sum(squared_vals)
	
	# return the "normalized" energy
	return total_energy / num_values