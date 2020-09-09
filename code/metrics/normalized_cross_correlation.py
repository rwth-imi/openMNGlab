import numpy as np
from math import sqrt
from scipy.signal import correlate

## (An approximation of) the normalized cross correlation for two discrete input signals x and y as the maximum of the cross correlation computed by scipy divided by the square root of the multiplied energy of both signals.
def normalized_cross_correlation(x, y):
    corr = correlate(x, y, 'valid')
    corr = corr / sqrt(np.sum(np.square(x)) * sum(np.square(y)))
    return max(corr)