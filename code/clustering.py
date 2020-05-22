# this is the custom metric that we use for DBSCAN clustering
# it should prioritize the time over the signal energy
# we assume that x[0] is the time
# and x[1] is the normalized energy
def actionPotDistance(x, y):
	energy_importance = 0.0005

	time_diff = abs(x[0] - y[0])
	energy_diff = abs(x[1] - y[1])

	return time_diff + energy_importance * energy_diff