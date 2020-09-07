import numpy as np

## Models mechanical stimuli, where force is applied to the skin in order to provoke a reaction by the mechano-sensitive C-fibres on the skin.
# \author Fabian Schlebusch, fabian.schlebusch@rwth-aachen.de
class MechanicalStimulus:
	## Timestamp where the mechanical stimulation started.
	onset = None
	## Timestamp where the stimulation stopped.
	offset = None
	## Maximum amplitude of the applied force.
	amplitude = None
	
	## Constructs a mechanical stimulus object from the given information.
	# @param onset Onset of the stimulation (in s)
	# @param offset Timestamp where the stimulation stopped (in s)
	# @param raw_values Raw values from the experiment's force channel
	def __init__(self, onset, offset, raw_values, verbose = False):
		self.onset = onset
		self.offset = offset
		self.amplitude = max(raw_values)
		
		if verbose == True:
			self.print_info()
	
	## Constructs a mech stimulus object from the information contained in the provided pandas dataframe.
	# @param input_df Dataframe which contains only rows that belong to this particular force stimulus
	# @time_column Label of the column which contains the time stamps
	# @force_column Label for the column with force values
	# @return Mechanical stimulus object using the force values and time info provided by the DF
	def from_dataframe(input_df, time_column = "Time", force_column = "3 Force", verbose = False):
		onset = input_df.iloc[0][time_column]
		offset = input_df.iloc[-1][time_column]
		force_values = input_df[force_column].values
		
		return MechanicalStimulus(onset = onset, offset = offset, raw_values = force_values, verbose = verbose)
	
	## Prints information about the mechanical stimulus.
	def print_info(self):
		print("Found mechanical stimulus:")
		print("onset = " + str(self.onset) + "s offset = " + str(self.offset) + "s")
		print("amplitude = " + str(self.amplitude) + "mN")