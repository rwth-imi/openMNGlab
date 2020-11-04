import unittest
import os
import csv

from importers import DapsysImporter

# these are some parameters for the test
# the two directories must be independent from each other, i.e. not nested, else the separator fix test will fail!
ORIG_DIR_NAME = "C:\\Users\\fabia\\Desktop\\Neuro_Hiwi\\imi-neuro\\code\\test\\dapsys_test_data"
FIXED_DIR_NAME = "C:\\Users\\fabia\\Desktop\\Neuro_Hiwi\\imi-neuro\\code\\test\\dapsys_test_data_fixed"
CONTINOUS_FILE = "02.05.2019_F1b_Continuous Recording.CSV"
PULSE_FILE = "02.05.2019_F1b_Pulses.CSV"
TRACK_FILES = ["02.05.2019_F1b_Track1.CSV", "02.05.2019_F1b_Track2.CSV", "02.05.2019_F1b_Track3.CSV"]

class DapsysImporterTest(unittest.TestCase):

    def test_separator_fix(self):
        # first, remove the fixed files if they exist, to make sure that we don't append to the files
        if os.path.exists(FIXED_DIR_NAME):
            for file in os.listdir(FIXED_DIR_NAME):
                os.remove(FIXED_DIR_NAME + "\\" + file)

        # run the method to fix the separator issue
        DapsysImporter.fix_separator_decimal_issue(in_path = ORIG_DIR_NAME, out_path = FIXED_DIR_NAME)

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


    # test if a file is loaded correctly
    def test_loading(self):

        importer = DapsysImporter(in_path = FIXED_DIR_NAME)

        print(importer.get_action_potentials())