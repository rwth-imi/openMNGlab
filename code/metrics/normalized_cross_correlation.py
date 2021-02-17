from typing import Union
from neo.core.analogsignal import AnalogSignal
from neo.core.irregularlysampledsignal import IrregularlySampledSignal
import numpy as np
from math import sqrt
from scipy.signal import correlate
from quantities import Quantity

## (An approximation of) the normalized cross correlation for two discrete input signals x and y as the maximum of the cross correlation computed by scipy divided by the square root of the multiplied energy of both signals.
def normalized_cross_correlation(x: Union[Quantity, np.ndarray], y: Union[Quantity, np.ndarray]):

    if isinstance(x, Quantity) != isinstance(y, Quantity):
        raise ValueError("Please pass two quantities or two plain arrays. Don't mix these types.")
    
    corr = correlate(x, y, 'valid')

    # handle the unit of quantities during normalization
    if isinstance(x, Quantity):
        corr = corr / sqrt(np.sum(np.square(x.magnitude)) * sum(np.square(y.magnitude)))
        corr = corr[0]
    else:
        corr = corr / sqrt(np.sum(np.square(x)) * sum(np.square(y)))

    return max(corr)

# TODO add comment
def sliding_window_normalized_cross_correlation(signal: Union[Quantity, np.ndarray], template: Union[Quantity, np.ndarray]):
    if len(template) > len(signal):
        raise ValueError("Template is longer than the signal!")

    # slide the template over the window
    correlations = []
    for start_idx in range(0, len(signal) - len(template)):
        correlations.append(normalized_cross_correlation(signal[start_idx : start_idx + len(template)], template))

    return correlations