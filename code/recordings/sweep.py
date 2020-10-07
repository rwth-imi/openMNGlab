from signal_artifacts import *
from typing import Dict, List

## Models a single sweep in an MNG recording, i.e., one segment/epoch/interval.
# A sweep is the time interval between two electrical stimuli.
class Sweep:
	
	# TODO: Add comments
	
	el_stimulus = None
	raw_signal = None
	action_potentials = None
	
	t_start = None
	t_end = None
	
	def __init__(self, stimulus, actpots, raw_signal, t_start, t_end):
		self.el_stimulus = stimulus
		self.action_potentials = actpots
		
		self.raw_signal = raw_signal
		
		self.t_start = t_start
		self.t_end = t_end