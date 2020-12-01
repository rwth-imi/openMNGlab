import numpy as np
from collections.abc import Iterable
from pathlib import Path
import csv
import os
import pandas as pd
from tqdm import tqdm

from recordings import MNGRecording, Sweep
from fibre_tracking import ActionPotentialTemplate

from fibre_tracking.track_correlation import track_correlation, get_tc_noise_estimate, search_for_max_tc

## An AP track which means that a for number of sweeps 0 to k, we have latencies t_0, ..., t_k that belong to a latency track.
# A latency track can therefore also be written as a list of entries (i, t_i) where i is the sweep index and t_i the corresponding latency.
# This is what we are trying to achieve with this class.
class APTrack(object):

	## this attribute stores the latencies at the individual sweeps
	# they should be stored as tuples (k, t) where k is the sweep index and t is the latency at the sweep k
	_latencies = None

	## stores the color for this AP track
	color = "red"

	## stores an AP template for this track
	ap_template = None
	
	## Construct an object for an AP track in the recording
	# @param latencies A list of tuples (sweep_idx, latency) where sweep_idx is the index of the sweep (also called k in the paper) and the latency t (in seconds)
	def __init__(self, latencies):
		
		# store the latency tuples in a sorted list
		self._latencies = sorted(latencies, key = lambda latency: latency[0])
	
	## Method to construct an AP track class from some action potentials.
	# @param sweeps List of sweeps
	# @param aps List of action potentials
	@staticmethod
	def from_aps(sweeps: Iterable, aps: Iterable):
		
		# this list is meant to store the lateny tuples that are required to spawn a new AP track
		latencies = []
		
		# go over the aps to find their sweep index
		sweep_idx = 0
		for ap in aps:
			# increase the sweep index until we found the sweep in which the AP was triggered
			while sweep_idx < len(sweeps) - 1 and ap.onset > sweeps[sweep_idx].t_end:
				sweep_idx += 1
				
			# calculate latency and store both as tuples
			latency = ap.onset - sweeps[sweep_idx].t_start + (ap.duration / 2)	
			latencies.append((sweep_idx, latency))
		
		return APTrack(latencies = latencies)
		
	## TODO implement a method that, for a given track and the recording object, generates a list of Action Potential objects
	# should return a list of newly generated action potentials
	def to_aps(self, recording: MNGRecording):
		pass

	## For each sweep and each latency, the closest AP is searched and assigned as an AP that belongs to this track.
	# @param sweeps List of sweeps in this recording
	# @return List of action potentials that potentially belong to this track
	def get_nearest_existing_aps(self, threshold=False, sweeps: Iterable):

		actpots = []
		#print("self:",self._latencies)

		for (sweep_idx, latency) in self._latencies:
			# get the sweep corresponding to this sweep index
			cur_sweep = sweeps[sweep_idx]
			# check if there is actually an AP in this sweep
			if cur_sweep.action_potentials:
				# calculate the absolute distances between the projected latency track point and the APs
				dists = [abs(latency - ap.features["latency"]) for ap in cur_sweep.action_potentials]
				#Check if a valid AP according to the threshold was found
				if(not threshold or np.min(dists)<threshold):
					# add the closest AP
					ap_idx = np.argmin(dists)
					actpots.append(cur_sweep.action_potentials[ap_idx])
				else:
					print("Threshold exceeded for APs in sweep nr. " + str(sweep_idx))
			else:
				print("There are no APs in sweep nr. " + str(sweep_idx))

		return actpots

	## This method is not yet implemented but should be similar to the extend_downwards function.
	# TODO implement!
	def extend_upwards(self):
		pass
		
	## Method to extend an existing latency track in downward direction
	# @param sweeps List of sweeps in the recording
	# @param num_sweeps For how many sweeps should we extend this track
	# @param max_shift Maximum latency shift between one sweep i and the next sweep i + 1
	# @param max_slope Absolute value for the maximum slope that is considered when linearizing the track around the last sweep
	# @param radius Radius of the "window" from which the latencies for track linearization are selected
	# @param window_size Window size that is used to calculate the Root Mean Squared signal power
	# @param slope_penalty_term Penalty term that is used to weight the latencies in the next slope. 'cos' penalty term is the one proposed by Turnquist et al. See also fibre_tracking.track_correlation.search_for_max_tc for more info.
	def extend_downwards(self, sweeps, num_sweeps = 1, max_shift = 0.003, max_slope = 0.003, radius = 2, window_size = 0.001, slope_penalty_term = 'cos', verbose = False):
		
		try:
			for i in tqdm(range(num_sweeps)):
				# Get the last R (radius) latencies to fit a line
				sweep_idcs = self.sweep_idcs
				latencies = self.latencies
			
				# fit a line to the existing sweep indices (depending on the chosen radius) and latencies to get estimates for the line parameters
				if len(self._latencies) > 1:
					slope, latency_intercept = np.polyfit(x = sweep_idcs[min(-len(self._latencies), -radius - 1) : ], y = latencies [min(-len(self._latencies), -radius - 1) : ], deg = 1)
				elif len(self._latencies) == 1:
					slope = 0
					latency_intercept = latencies[0]
				else:
					raise RuntimeError("Cannot extend an empty track!")
				
				# using these parameters, predict the latency in the very next sweep
				next_sweep_idx = max(sweep_idcs) + 1
				pred_latency = slope * next_sweep_idx + latency_intercept
				
				# search for the maximum TC in a certain environment around the predicted latency
				max_tc_latency, tc = search_for_max_tc(sweeps = sweeps, sweep_idx = next_sweep_idx, latency = pred_latency, max_shift = max_shift, max_slope = max_slope, \
														slope_penalty_term = slope_penalty_term, established_slope = slope, radius = radius, window_size = window_size)
				
				self.insert_latency(sweep_idx = next_sweep_idx, latency = max_tc_latency)
				
				if verbose == True:
					print("Added AP to track: sweep " + str(next_sweep_idx) + " , latency " + str(max_tc_latency))
		except ValueError as err:
			print(err)
		except err:
			print(err)

	## Use this function to add latencies to this track!
	# @param sweep_idx Index of the sweep where you want to add the latency
	# @param latency The latency itself (in seconds)
	def insert_latency(self, sweep_idx, latency):
		
		# go through the existing latencies to insert the new one in the right place
		lst_idx = 0
		while lst_idx < len(self._latencies) and sweep_idx > self._latencies[lst_idx][0]:
			lst_idx += 1
			
		self._latencies.insert(lst_idx, (sweep_idx, latency))
		
	## Use this fct. to remove latencies from a track, e.g., if some faulty points have been added. Use only sweep_idx OR time parameter, else this will result in an error.
	# @param sweep_idx Sweep index after which the latencies should be deleted
	# @param time Timestamp after which latencies should be deleteted. If used, sweeps have also be passed!
	# @param sweeps List of sweeps, required only if deletion based on time is chosen
	def remove_behind(self, sweep_idx = None, time = None, sweeps = None):
		# check arguments for correctness
		if sweep_idx != None and time != None:
			raise ValueError("Arguments for track deletion are ambiguous. You should only pass either a sweep index or the time.")
		if time != None and sweeps == None:
			raise ValueError("If time is passed as argument for track deletion, you'll also need to pass the list of sweeps.")
		
		# if the time based criterion is used, then find the corresponding sweep index
		if time != None and sweeps != None:
			sweep_idx = 0
			# increase index until t_start exceeds the chosen timepoint
			while sweeps[sweep_idx].t_start < time:
				sweep_idx += 1

		# now, remove all the latencies behind this sweep index
		self._latencies = [(idx, latency) for (idx, latency) in self._latencies if idx <= sweep_idx]

	## Method to merge two AP tracks into a single AP track
	# Tracks must not be overlapping, i.e. share sweep indices!
	# @param track1 First track for merging
	# @param track2 Sencond track for merging
	@staticmethod
	def merge_tracks(track1, track2):
		# check if the tracks are intersecting at a certain index
		common_idcs = set(track1.sweep_idcs) & set(track2.sweep_idcs)
		if common_idcs:
			raise ValueError(f"The given tracks share a common sweep index. Therefore, the latency is not clearly defined and the tracks cannot be merged. This affects the indices {common_idcs}.")

		# append the two tracks and return a new AP track with all the latencies (sorting is implicitly done in the constructor!)
		new_latencies = track1._latencies + track2._latencies
		return APTrack(latencies = new_latencies)

	## Function to save an AP track to disk. We'll create a csv file that stores the sweep indices and the latencies
	# @param fpath Path to the file into which the AP track should be written
	def save_to_csv(self, fpath):
		# create the directory (if it does not already exist)
		Path(os.path.basename(fpath)).mkdir(parents = True, exist_ok = True)

		# open file for writing and append!
		with open(fpath, 'a', newline = '') as file:
			# create writer and write header
			writer = csv.writer(file, delimiter = ";")
			writer.writerow(["Sweep_Idx", "Latency"])

			for (sweep_idx, latency) in self._latencies:
				writer.writerow([sweep_idx, latency])

		print(f"Successfully saved AP track to {fpath}")

	## Function to load an AP track from a csv file
	# @param fpath Path to the csv file from which the AP track should be loaded
	@staticmethod
	def load_from_csv(fpath):
		# load the csv as a pandas df
		df = pd.read_csv(filepath_or_buffer = fpath, delimiter = ";", header = 0)
		# now, create a list of tuples as required by the constructor
		latencies = list(df.itertuples(index = False, name = None))
		# and return the newly created AP track
		return APTrack(latencies = latencies)

	## This function handles calls like len(track)
	def __len__(self):
		return len(self._latencies)
		
	@property
	def sweep_idcs(self):
		return [x[0] for x in self._latencies]
		
	@property
	def latencies(self):
		return [x[1] for x in self._latencies]