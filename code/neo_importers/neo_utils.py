from enum import Enum

class TypeID(Enum):
    RAW_DATA = "rd" # analogsignal channel
    ACTION_POTENTIAL = "ap" # spiketrain channel
    ELECTRICAL_STIMULUS = "es" # event channel
    ELECTRICAL_EXTRA_STIMULUS = "ex" # epoch channel
    MECHANICAL_STIMULUS = "ms" #spiketrain channel
