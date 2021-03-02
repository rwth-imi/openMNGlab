from datetime import datetime
import unittest
import os
from pathlib import Path

from neo.core import Segment

import neo_importers.neo_spike_importer as spike_importer
from neo_importers.recording_io import load_block, store_block, load_recordings, store_recordings
from neo_importers.neo_wrapper import MNGRecording

# PARAMETERS FOR THIS TEST
SPIKE2_FILE_NAME = Path(".")/"tests"/"resources"/"spike2"/"20_05_13_U1a_pulse_Latenz.smr"

class HDF5IOTest(unittest.TestCase):

    def _load_recording(self, filename):
        self.assertTrue(os.path.exists(filename))
        self.block, self.id_map = spike_importer.import_spike_file(filename, 
                                              stimuli_event_channels={"DigMark"},
                                              action_potential_channels={"nw-1#2"}
                                             )
        self.recording = MNGRecording(segment = self.block.segments[0], \
            name = "Test Recording", file_name = filename)

    def setUp(self) -> None:
        self._load_recording(filename = SPIKE2_FILE_NAME)
        return super().setUp()

    def test_block_save_and_load(self):
        # save, load and cleanup
        fname = Path(".")/"tests"/"resources"/("tmp_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".h5")
        store_block(fname, self.block)
        block2, id_map2 = load_block(fname)
        if os.path.exists(fname):
            os.remove(fname)

        seg: Segment = self.block.segments[0]
        seg2: Segment = block2.segments[0]

        self.assertEquals(len(seg.data_children), len(seg2.data_children))
        self.assertEquals(len(seg.spiketrains), len(seg2.spiketrains))
        self.assertEquals(len(seg.analogsignals), len(seg2.analogsignals))
        self.assertEquals(len(seg.events), len(seg2.events))
        self.assertEquals(self.id_map, id_map2)

    def test_recordings_save_and_load(self):
        # save, load and cleanup
        fname = Path(".")/"tests"/"resources"/("tmp_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".h5")
        store_recordings(fname, self.recording)
        (recording2,), id_map2 = load_recordings(fname)
        if os.path.exists(fname):
            os.remove(fname)

        self.assertEquals(len(self.recording.segment.data_children), len(recording2.segment.data_children))
        self.assertEquals(self.id_map, id_map2)
        self.assertEquals(len(self.recording.raw_data_channels), len(recording2.raw_data_channels))
        self.assertEquals(len(self.recording.electrical_stimulus_channels), len(recording2.electrical_stimulus_channels))
        self.assertEquals(len(self.recording.action_potential_channels), len(recording2.action_potential_channels))