from math import sqrt

## This function calculates the root mean square for a time series of signal values. See also: https://en.wikipedia.org/wiki/Root_mean_square
# @param signal The time series of input signal values
def root_mean_square_power(signal):
	n = len(signal)
	squared_signal = [x * x for x in signal]
	
	return sqrt(sum(squared_signal) / n)