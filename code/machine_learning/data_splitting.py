'''
	This function aims at working around the issue that we might get too good results from just picking APs randomly.
	Instead, we extract segments from the MNG recording, one for training and the other for testing.
	E.g., with 3 intervals and 0.2 test percentage, you get a testing set that contains 3 "groups" of subsequent APs that make up 20 percent of the recording in total.
	All other APs are just used for training
'''

import random as rnd
from math import ceil

def timebased_train_test_split(actpots, test_percentage = 0.2, num_test_intervals = 3):
	# calculate the number of APs per interval
	aps_per_intv = ceil(test_percentage * len(actpots) / num_test_intervals)

	rnd.seed()
	
	test_intvs = []
	
	for intv_idx in range(0, num_test_intervals):
		# get a random index and check if we are overlapping with any of the other intervals
		# or if we are "overshooting" behind the end of the recording
		intv_start_idx = rnd.randrange(0, len(actpots))
		intv_end_idx = intv_start_idx + aps_per_intv
	
		# generate candidates while the interval is going behind the end of the recording
		# and also if the candidate interval is overlapping with another interval
		while (intv_end_idx > len(actpots) or True in [intervals_overlapping((intv_start_idx, intv_end_idx), intv) for intv in test_intvs]):
			intv_start_idx = rnd.randrange(0, len(actpots))
			intv_end_idx = intv_start_idx + aps_per_intv
		
		test_intvs.append((intv_start_idx, intv_end_idx))
			
	# after we have the indices, write the APs into a test set
	test_aps = []
	for test_intv in test_intvs:
		test_aps.extend(actpots[test_intv[0] : test_intv[1]])
		
	# the training APs are then just all the APs that are not already in the test set
	train_aps = [ap for ap in actpots if not ap in test_aps]
		
	return train_aps, test_aps
	
'''
	Given to tuples (t1, t2) and (t3, t4) defining to intervals,
	check if the intervals are overlapping
'''
def intervals_overlapping(intv1, intv2):
	return (intv1[0] >= intv2[0] and intv1[0] <= intv2[1]) or (intv1[1] >= intv2[0] and intv1[0] <= intv2[1]) or (intv2[0] >= intv1[0] and intv2[0] <= intv1[1]) or (intv2[1] >= intv1[0] and intv2[0] <= intv1[1])