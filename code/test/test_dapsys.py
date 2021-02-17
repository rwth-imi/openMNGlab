import unittest
import os
import csv
from math import floor, ceil

from neo_importers.neo_dapsys_importer import _fix_separator_decimal_matching, import_dapsys_csv_files

# these are some parameters for the test
# the two directories must be independent from each other, i.e. not nested, else the separator fix test will fail!
ORIG_DIR_NAME = ".\\test\\dapsys_test_data\\"
FIXED_DIR_NAME = ".\\test\\dapsys_test_data_fixed\\"
CONTINOUS_FILE = "test_data.csv"
PULSE_FILE = "02.05.2019_F1b_Pulses.CSV"
TRACK_FILES = ["02.05.2019_F1b_Track1.CSV", "02.05.2019_F1b_Track2.CSV", "02.05.2019_F1b_Track3.CSV"]
SAMPLING_RATE = 10000
T_MIN = 11.679126 
T_MAX = 1399.99994
NUM_STIMULI = 310

class DapsysImporterTest(unittest.TestCase):

    # this test checks whether the DapsysImporter is able to fix the problem on german systems, where Dapsys uses the comma as both, the decimal point and the csv-separator
    def test_separator_fix(self):
        # first, remove the fixed files if they exist, to make sure that we don't append to the files
        if os.path.exists(FIXED_DIR_NAME):
            for file in os.listdir(FIXED_DIR_NAME):
                os.remove(FIXED_DIR_NAME + "\\" + file)

        # run the method to fix the separator issue
        _fix_separator_decimal_matching(in_path = ORIG_DIR_NAME, out_path = FIXED_DIR_NAME)

        # get the files/directories from the original and the fixed directory
        orig_paths = [ORIG_DIR_NAME + "\\" + fname for fname in sorted(os.listdir(ORIG_DIR_NAME))]
        fixed_paths = [FIXED_DIR_NAME + "\\" + fname for fname in sorted(os.listdir(FIXED_DIR_NAME))]

        # assert that we have the same number of files
        self.assertTrue(len(orig_paths) == len(fixed_paths))

        # check for every file if we translated it correctly
        for orig, fix in zip(orig_paths, fixed_paths):
            with open(orig, 'r') as f_orig, open(fix, 'r') as f_fixed:
                orig_reader = csv.reader(f_orig, delimiter = ',')
                fixed_reader = csv.reader(f_fixed, delimiter = ',')

                orig_line = next(orig_reader)
                fixed_line = next(fixed_reader)

                # check if we get half the number of columns
                # don't forget to account for the "comment" that is appended in some lines
                if (len(orig_line) % 2 == 0 and len(fixed_line) % 2 == 0):
                    self.assertEqual(len(orig_line) / 2, len(fixed_line))
                else:
                    self.assertEqual((len(orig_line) - 1) / 2, len(fixed_line) - 1)

                self.assertEqual(len([x for x in enumerate(orig_reader)]), len([x for x in enumerate(fixed_reader)]))

    # Check if the new dapsys neo importer can read files
    def test_loading(self):
        import_dapsys_csv_files(directory = FIXED_DIR_NAME)
        self.assertTrue(True)

    # # test if a file is loaded correctly
    # def test_loading(self):

    #     print("test")

    #     # TODO apparently, the template file for APs is missing. We'll need to add this if we want to actually test the importer.
    #     importer = DapsysImporter(dir_path = FIXED_DIR_NAME, sampling_rate = SAMPLING_RATE)
        
    #     # now, check if all the electrical stimuli have been loaded
    #     self.assertEqual(len(importer.electrical_stimuli), NUM_STIMULI)

    #     # these values are hard-coded for the start and end times of our test data
    #     num_samples = ceil(T_MAX * SAMPLING_RATE)
    #     self.assertEqual(num_samples, len(importer.raw_signal))

    #     # check if all tracks have been loaded
    #     self.assertEqual(len(importer.ap_tracks), 2)