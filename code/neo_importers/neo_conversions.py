from neo.core import AnalogSignal, IrregularlySampledSignal
from quantities.quantity import Quantity
import numpy as np
from math import ceil

# TODO maybe interpolation would be nice at some points (especially if the signal indeed is irregularly sampled)
def fill_irregularly_sampled_signal_with_zeros(irregular_sig: IrregularlySampledSignal, sampling_rate: Quantity(10000, "Hz")) -> AnalogSignal:
    
    # allocate array for the regular signal
    num_regular_samples = ceil(Quantity(irregular_sig.duration * sampling_rate).magnitude)
    regular_sig = Quantity(np.zeros(num_regular_samples, dtype = np.float64), irregular_sig.dimensionality)

    # calculate the indices of the samples
    idcs: Quantity = (irregular_sig.times - irregular_sig.times[0]) * sampling_rate
    idcs = idcs.magnitude
    to_int = np.vectorize(np.int)
    idcs = to_int(idcs)

    # conversion step
    regular_sig[idcs] = irregular_sig[:].ravel()
    result: AnalogSignal = AnalogSignal(regular_sig, t_start = irregular_sig.times[0], sampling_rate = sampling_rate)

    return result