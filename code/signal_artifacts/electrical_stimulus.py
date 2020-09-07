import numpy as np

## This class models the regular electrical stimulus / main pulse during an MNG experiment.
# It comes from either the corresponding Spike channel or one of the Dapsys files.
# \author Fabian Schlebusch, fabian.schlebusch@rwth-aachen.de
class ElectricalStimulus:
	## Timepoint at which the electrical stimulus was induced during the recording
	timepoint = None
	## The interval between this and the next electrical stimulus.
	# This information is usually not too important but, e.g., the plotting.falling_leaf.FallingLeafPlot uses this information to draw the signal after each pulse.
	interval_raw_signal = None
	## Length of the interval, beginning from this el. stimulus, ending with the next.
	interval_length = 0
	## Saves the position of the electrical stimulus in the recording's dataframe, to make the complexity of the access constant.
	# Note: this attribute is only relevant for the spike importer atm.
	# TODO: there might be a problem if we want to plot the falling leaves plot when the file has been imported from Dapsys.
	df_index = None
	
	## Constructs an ES object with the given timestamp.
	# @param timepoint Timepoint when the electrical stimulus was fired.
	def __init__(self, timepoint, verbose = False):
		self.timepoint = timepoint
		
		if verbose == True:
			self.print_info()
	
	## Calls the constructor using the given pandas dataframe to create an ES object.
	# @param input_data A dataframe which contains only a single row with the timestamp of the electrical stimulus
	# @param df_index The index of the electrical stimulus in the original dataframe
	# @param time_column Name of the column that contains the time information
	# @return ElectricalStimulus object at the given timepoint
	def from_dataframe(input_data, df_index, time_column = "Time", verbose = False):
		es = ElectricalStimulus(timepoint = input_data[time_column], verbose = verbose)
		es.df_index = df_index
		return es
		
	## Prints info about this electrical stimulus for debugging purposes.
	def print_info(self):
		print("Found el. stimulus signal at:")
		print("Time = " + str(self.timepoint) + "s")
