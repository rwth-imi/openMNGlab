from pathlib import Path
from typing import Dict, Tuple, List
from neo.core import Block, Segment
from neo.core.dataobject import DataObject
from neo.io import NixIO, NeoHdf5IO
from neo_importers.neo_wrapper import MNGRecording, TypeID

## Allowed file extensions for loading and storing
EXTENSIONS = {'.h5', '.nix'}

## Checks if the extension of the file is allowed
#  @param file_name path object representing the path to the file
def _check_extension(file_name: Path) -> bool:
    return file_name.suffix in EXTENSIONS

## Loads a Neo block object from disk
#  @param file_name path object pointing to the file on the disk
#  @returns the Neo Block object and a dictionary mapping channel names to the unified id format
def load_block(file_name: Path) -> Tuple[Block, Dict[TypeID, Dict[str, str]]]:
    assert _check_extension(file_name)
    reader = NixIO(str(file_name), "ro")

    blocks = reader.read(lazy=False)
    block: Block = blocks[0]
    if block.name is None or len(block.name) == 0:
        block.name = str(file_name.stem)
    if block.file_origin is None:
        block.file_origin = str(file_name)

    id_map = { type_id: {} for type_id in TypeID }
    data_object: DataObject
    for segment in block.segments:
        for data_object in segment.data_children:
            if "type_id" not in data_object.annotations or "id" not in data_object.annotations:
                continue
            type_id = TypeID(data_object.annotations["type_id"])
            id_map[type_id][data_object.name] = data_object.annotations["id"]
    return block, id_map

## Loads recordings the neo Block storage from a file
#  @param file_name path object pointing to the file on the disk
#  @returns a list of MNGRecordings for each segment in the Neo block and a dictionary mapping channel names to the unified id format
def load_recordings(file_name: Path) -> Tuple[List[MNGRecording], Dict[TypeID, Dict[str, str]]]:
    block, id_map = load_block(file_name)
    result = []
    segment: Segment
    for segment in block.segments:
        name = segment.name if segment.name is not None \
          else block.name if block.name is not None \
          else file_name.stem
        result.append(MNGRecording(segment, name, str(file_name)))
    return result, id_map

## Stores a Neo Block object of our unified format on the disk
#  @params file_name Path object pointing to the file to store
#  @param block the Neo Block object to be stored
def store_block(file_name: Path, block: Block) -> None:
    assert _check_extension(file_name)
    writer = NixIO(str(file_name), "ow")
    writer.write(block)

## Stores one or more MNGRecordings as one Neo block in a file
#  @param file_name Path object pointing to the file to store
#  @recordings vararg list of MNGRecordings to store together in that file
def store_recordings(file_name: Path, *recordings: List[MNGRecording]) -> None:
    block = Block(name = file_name.stem)
    for recording in recordings:
        block.segments.append(recording.segment)
    store_block(file_name, block)