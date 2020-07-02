# this is the custom metric that we use for DBSCAN clustering
# it should prioritize the time over the signal energy
# we assume that x[0] is the time
# and x[1] is the normalized energy
def time_dist_to_stimulus(x, y):
	time_diff = abs(x[0] - y[0])
	
	return time_diff

def time_dist_and_energy(x, y, energy_importance = 10e-7):
	time_diff = abs(x[0] - y[0])
	energy_diff = abs(x[1] - y[1])

	return time_diff + energy_importance * energy_diff
	
def actionpot_dist_el_stim_mech_stim(x, y):
	mech_factor = 0.002

	el_diff = abs(x[0] - y[0])
	mech_diff = abs(x[1] - y[1])

	return max(mech_factor * mech_diff, el_diff)