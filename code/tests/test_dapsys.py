import unittest
import os
import csv
from pathlib import Path
from tests.helpers import download_files

from neo.core.block import Block
from neo.core.segment import Segment

from neo_importers.neo_dapsys_importer import _fix_separator_decimal_matching, import_dapsys_csv_files, _do_files_need_fixing, check_and_fix_dapsys_files
from neo_importers.neo_wrapper import MNGRecording

ORIG_DIR_NAME = Path("..")/"resources"/"test"/"dapsys"/"dapsys_crossing_tracks_0_1400"
FIXED_DIR_NAME = Path("..")/"resources"/"test"/"dapsys"/"dapsys_crossing_tracks_0_1400_fixed"

FILENAMES = ["06_11_19_F3B_AF_Continuous Recording.csv", 
             "06_11_19_F3B_AF_All Responses.csv", 
             "06_11_19_F3B_AF_Pulses.csv", 
             "06_11_19_F3B_AF_Track2.CSV", 
             "06_11_19_F3B_AF_Track5.CSV",
             "template_Track2.csv",
             "template_Track5.csv"]
FILE_URLS = ["https://gin.g-node.org/fschlebusch/openMNGlab-testdata/raw/383db037d8e21ee9b3bdb1ebb8048f1f035eaa75/dapsys/06_11_19_F3B_AF_Continuous%20Recording.CSV",
             "https://gin.g-node.org/fschlebusch/openMNGlab-testdata/raw/383db037d8e21ee9b3bdb1ebb8048f1f035eaa75/dapsys/06_11_19_F3B_AF_All%20Responses.CSV",
             "https://gin.g-node.org/fschlebusch/openMNGlab-testdata/raw/383db037d8e21ee9b3bdb1ebb8048f1f035eaa75/dapsys/06_11_19_F3B_AF_Pulses.CSV",
             "https://gin.g-node.org/fschlebusch/openMNGlab-testdata/raw/383db037d8e21ee9b3bdb1ebb8048f1f035eaa75/dapsys/06_11_19_F3B_AF_Track2.CSV",
             "https://gin.g-node.org/fschlebusch/openMNGlab-testdata/raw/383db037d8e21ee9b3bdb1ebb8048f1f035eaa75/dapsys/06_11_19_F3B_AF_Track5.CSV",
             "https://gin.g-node.org/fschlebusch/openMNGlab-testdata/raw/383db037d8e21ee9b3bdb1ebb8048f1f035eaa75/dapsys/template_Track2.csv",
             "https://gin.g-node.org/fschlebusch/openMNGlab-testdata/raw/383db037d8e21ee9b3bdb1ebb8048f1f035eaa75/dapsys/template_Track5.csv"]

SAMPLING_RATE = 10000
T_MIN = 11.679126 
T_MAX = 1399.99994
NUM_STIMULI = 310

class DapsysImporterTest(unittest.TestCase):

    def setUp(self) -> None:
        download_files(FILE_URLS, FILENAMES, ORIG_DIR_NAME)
        check_and_fix_dapsys_files(ORIG_DIR_NAME, FIXED_DIR_NAME)
        return super().setUp()

    # checks whether dapsys importer can detect that files need to be fixed due to comma separator issues
    def test_files_need_fix(self):
        self.assertTrue(_do_files_need_fixing(ORIG_DIR_NAME))
        self.assertFalse(_do_files_need_fixing(FIXED_DIR_NAME))

    # this test checks whether the DapsysImporter is able to fix the problem on german systems, where Dapsys uses the comma as both, the decimal point and the csv-separator
    def test_separator_fix(self):
        # first, remove the fixed files if they exist, to make sure that we don't append to the files
        if os.path.exists(FIXED_DIR_NAME):
            for file in os.listdir(FIXED_DIR_NAME):
                os.remove(os.path.join(FIXED_DIR_NAME, file))

        # run the method to fix the separator issue
        _fix_separator_decimal_matching(in_path = ORIG_DIR_NAME, out_path = FIXED_DIR_NAME)

        # get the files/directories from the original and the fixed directory
        orig_paths = [os.path.join(ORIG_DIR_NAME, fname) for fname in sorted(os.listdir(ORIG_DIR_NAME))]
        fixed_paths = [os.path.join(FIXED_DIR_NAME, fname) for fname in sorted(os.listdir(FIXED_DIR_NAME))]

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
        block: Block
        block, id_map, ap_tracks = import_dapsys_csv_files(directory = FIXED_DIR_NAME)
        self.assertEquals(len(block.segments), 1)
        seg: Segment = block.segments[0]
        self.assertGreater(len(seg.analogsignals), 0)
        self.assertGreater(len(seg.events), 0)
        self.assertGreater(len(seg.spiketrains), 0)
        recording: MNGRecording = MNGRecording(seg)
        self.assertTrue(recording.action_potential_channels)
        self.assertTrue(recording.electrical_stimulus_channels)
        self.assertTrue(recording.raw_data_channels)