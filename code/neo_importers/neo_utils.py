from typing import Iterable, List, Tuple, Dict

from quantities import Quantity
from neo.core import Segment, AnalogSignal, IrregularlySampledSignal, SpikeTrain
from neo.core.dataobject import DataObject
import numpy as np
from neo_importers.neo_wrapper import TypeID

from math import ceil

## Concatinates two quantity numpy arrays and preserves the units
#  @param a the first array
#  @param b the second array
def quantity_concat(a: Quantity, b: Quantity) -> Quantity:
    return np.concatenate([a, b.rescale(a.units)]) * a.units

## Stores the original channel names in the annotations so after creating new ones in the unified format, they can be traced back
#  @param objects iterable container containing all channels
def store_original_names(objects: Iterable[DataObject]) -> None:
    for obj in objects:
        obj.annotate(original_name=obj.name)

## Ensures names are unique by numbering ambiguous names
#  @param objects iterable container containing all channels
def make_names_unique(objects: Iterable[DataObject]) -> None:
    objects_by_name: Dict[str, List[DataObject]] = {obj.name: [o for o in objects if o.name == obj.name] for obj in objects}
    for obj_list in objects_by_name.values():
        if len(obj_list) > 1:
            for i, obj in enumerate(obj_list):
                obj.name = f"{obj.name}_{i}"

## Removes empty named channels by setting their name to UNNAMED
#  @param objects iterable container containing all channels
def remove_empty_names(objects: Iterable[DataObject]) -> None:
    for obj in objects:
        if obj.name is None or not obj.name:
            obj.name = "UNNAMED"

## Removes all array_annotations
#  @param objects iterable container containing all channels
def remove_array_annotations(objects: Iterable[DataObject]) -> None:
    for obj in objects:
        obj.array_annotations.clear()

## Deletes all channels not following our unified format
#  @param segment the segment containing the channels
def prune_segment(segment: Segment) -> None:
    segment.analogsignals = [a for a in segment.analogsignals if "type_id" in a.annotations]
    segment.epochs = [ep for ep in segment.epochs if "type_id" in ep.annotations]
    segment.events = [ev for ev in segment.events if "type_id" in ev.annotations]
    segment.irregularlysampledsignals = [i for i in segment.irregularlysampledsignals if "type_id" in i.annotations]
    segment.spiketrains = [st for st in segment.spiketrains if "type_id" in st.annotations]
    segment.imagesequences = [i for i in segment.imagesequences if "type_id" in i.annotations]

## Detects spikes in an analog signal where the amplitude exceeds a given threshold
#  @param channel the analoge channel
#  @param threshold the threshold to detect spikes
#  @param signal_channel_index the channel index for multidimensional channels (default 0)
#  @returns a list of start:stop datapoint indices of spikes within the analog signal
def find_spikes(channel: AnalogSignal, threshold: Quantity, signal_channel_index: int=0) -> List[Tuple[int, int]]:
    result: List[Tuple[int, int]] = []
    start_index: int = None
    assert channel.shape[1] > signal_channel_index
    for i, amp_lst in enumerate(channel):
        amp: Quantity = amp_lst[signal_channel_index]
        if start_index is None and amp >= threshold:
            start_index = i
        elif start_index is not None and amp < threshold:
            result.append((start_index, i))
            start_index = None
    return result

# TODO maybe interpolation would be nice at some points (especially if the signal indeed is irregularly sampled)
def convert_irregularly_sampled_signal_to_analog_signal(irregular_sig: IrregularlySampledSignal, sampling_rate: Quantity(10000, "Hz")) -> AnalogSignal:
    
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
    result: AnalogSignal = AnalogSignal(regular_sig, 
                                        t_start = irregular_sig.times[0], 
                                        sampling_rate = sampling_rate,
                                        name = "Analog Signal", 
                                        file_origin = irregular_sig.file_origin)
    return result

## Converts an index for a datapoint in an analog channel, to the time of that datapoint
#  @param channel the signal channel from which the index is
#  @param the index of the datapoint
#  @returns the time that datapoint occured at
def channel_index_to_time(channel: AnalogSignal, index: int) -> Quantity:
    result = channel.t_start + index * channel.sampling_period
    # ensure unit compatibility
    result.units = channel.sampling_period.units
    return result

## Creates a new spiketrain from a raw channel where a spike is detected by the amplitude being higher than a threshold
#  @param channel the signal channel to filter spikes from
#  @param threshold the threshold to indicate spikes
#  @returns a spiketrain with a unique name containing the spikes where the amplitude exceeded the threshold
def spiketrain_from_raw(channel: AnalogSignal, threshold: Quantity) -> SpikeTrain:
    assert channel.signal.shape[1] == 1
    spikes = find_spikes(channel, threshold)
    signal = channel.signal.squeeze()
    times = np.array([channel_index_to_time(channel, start) for start, _ in spikes]) * channel.sampling_period.units
    waveforms = np.array([[signal[start:stop]] for start, stop in spikes]) * channel.units
    name = f"{channel.name}#{threshold}"
    result = SpikeTrain(name=name, times=times, units=channel.units, t_start=channel.t_start, t_stop=channel.t_stop,
                        waveforms=waveforms, sampling_rate=channel.sampling_rate, sort=True)
    result.annotate(from_channel=channel.name, threshold=threshold)
    return result

## Get the maximum amplitude of each spike as quantity numpy array
#  @param channel the spiketrain channel
#  @returns a quantity numpy array containing the maximum amplitudes of each spike
def spike_amplitudes(channel: SpikeTrain) -> Quantity:
    # there is probably a numpy version of this
    return np.array([max(wave[0]) for wave in channel.waveforms]) * channel.units
