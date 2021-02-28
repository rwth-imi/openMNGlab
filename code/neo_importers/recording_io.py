from pathlib import Path
from typing import Dict, Tuple, List
from neo.core import Block, Segment
from neo.core.dataobject import DataObject
from neo.io import NixIO, NeoHdf5IO
from neo_importers.neo_wrapper import MNGRecording, TypeID

EXTENSIONS = {'.h5', '.nix'}

def _check_extension(file_name: Path) -> bool:
    return file_name.suffix in EXTENSIONS

def load_block(file_name: Path) -> Tuple[Block, Dict[TypeID, Dict[str, str]]]:
    assert _check_extension(file_name)
    reader = NixIO(str(file_name), "ro")
    blocks = reader.read(lazy=False)
    block: Block = blocks[0]
    id_map = { type_id: {} for type_id in TypeID }
    data_object: DataObject
    for segment in block.segments:
        for data_object in segment.data_children:
            if "type_id" not in data_object.annotations or "id" not in data_object.annotations:
                continue
            type_id = TypeID(data_object.annotations["type_id"])
            id_map[type_id][data_object.name] = data_object.annotations["id"]
    return block, id_map

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


def store_block(file_name: Path, block: Block) -> None:
    assert _check_extension(file_name)
    writer = NixIO(str(file_name), "ow")
    writer.write(block)

def store_recordings(file_name: Path, *recordings: List[MNGRecording]) -> None:
    block = Block(name = file_name.stem)
    for recording in recordings:
        block.segments.append(recording.segment)
    store_block(file_name, block)