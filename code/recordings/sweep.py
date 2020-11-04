from signal_artifacts import *
from typing import Dict, List

## Models a single sweep in an MNG recording, i.e., one segment/epoch/interval.
# A sweep is the time interval between two electrical stimuli.
class Sweep:
	
	## Electrical stimulus in the beginning of this sweep
	el_stimulus = None
	## Raw signal during this sweep
	raw_signal = None
	## List of APs in this sweep
	action_potentials = None
	## Starting time
	t_start = None
	## End time
	t_end = None
	
	## Constructs a new sweep object
	# @param stimulus Electrical stimulus in the beginning of this sweep
	# @param actpots Action potentials that follow this stimulus
	# @param raw_signal Raw signal for this sweep
	# @param t_start Start time of the sweep
	# @param t_end Analogous: end time
	def __init__(self, stimulus, actpots, raw_signal, t_start, t_end):
		self.el_stimulus = stimulus
		self.action_potentials = actpots
		
		self.raw_signal = raw_signal
		
		self.t_start = t_start
		self.t_end = t_end
		
	@property
	def duration(self):
		return self.t_end - self.t_start