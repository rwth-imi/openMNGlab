from typing import Iterable, List, Tuple, Dict

from quantities import Quantity
from neo.core import Segment, AnalogSignal, IrregularlySampledSignal
from neo.core.dataobject import DataObject
import numpy as np
from neo_importers.neo_wrapper import TypeID

from math import ceil

def store_original_names(objects: Iterable[DataObject]) -> None:
    for obj in objects:
        obj.annotate(original_name=obj.name)

def make_names_unique(objects: Iterable[DataObject]) -> None:
    objects_by_name: Dict[str, List[DataObject]] = {obj.name: [o for o in objects if o.name == obj.name] for obj in objects}
    for obj_list in objects_by_name.values():
        if len(obj_list) > 1:
            for i, obj in enumerate(obj_list):
                obj.name = f"{obj.name}_{i}"

def quantity_concat(a: Quantity, b: Quantity) -> Quantity:
    return np.concatenate([a, b.rescale(a.units)]) * a.units

def remove_empty_names(objects: Iterable[DataObject]) -> None:
    for obj in objects:
        if obj.name is None or not obj.name:
            obj.name = "UNNAMED"

def remove_array_annotations(objects: Iterable[DataObject]) -> None:
    for obj in objects:
        obj.array_annotations.clear()

# deletes all unnecessary channels
def prune_segment(segment: Segment) -> None:
    segment.analogsignals = [a for a in segment.analogsignals if "type_id" in a.annotations]
    segment.epochs = [ep for ep in segment.epochs if "type_id" in ep.annotations]
    segment.events = [ev for ev in segment.events if "type_id" in ev.annotations]
    segment.irregularlysampledsignals = [i for i in segment.irregularlysampledsignals if "type_id" in i.annotations]
    segment.spiketrains = [st for st in segment.spiketrains if "type_id" in st.annotations]
    segment.imagesequences = [i for i in segment.imagesequences if "type_id" in i.annotations]

# returns the start:stop tuples for when the amplitude is larger than the signal
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
