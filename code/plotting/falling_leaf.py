import matplotlib.pyplot as plt

'''
	**********************************
	Produces a falling leaf plot
	**********************************
'''
class FallingLeafPlot:
	
	def __init__(self, width = 10, height = 15):
		self.width = width
		self.height = height
	
	def plot(self, regular_stimuli, action_potentials, raw_signal = None):
		fig = plt.figure(figsize = (self.width, self.height))
	
		# plot the regular stimuli for reference
		for regstim in regular_stimuli:
			plt.scatter(x = 0, y = regstim.getTimepoint(), marker = "*", color = "k")
			
		# then, the actpots that presumably belong to this track
		for actpot in action_potentials:
			prev_stimulus = actpot.getPreviousRegElectricalStimulus()
			plt.scatter(x = actpot.getDistanceToPreviousRegularElectricalStimulus(), y = prev_stimulus.getTimepoint(), marker = "x", color = "r")
	
		plt.xlabel("Response Latency (s)")
		plt.ylabel("Time (s)"
		plt.margins(x = 0.1)
	
		# invert the y-axis so that 0 is on top and the time increases downwards
		plt.gca().invert_yaxis()
		
		plt.show()
	
		self.fig = fig
	
	# TODO implement saving of the plot
	def save_to_file(self, filename):
		return None