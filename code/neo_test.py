from importers import NeoImporter
import neo

# CED Spike2 files 
fname = "../data/10.6.15_F2.smr"

# create a reader
reader = neo.io.Spike2IO(filename = fname)

# read the block
bl = reader.read(lazy=False)[0]
print(bl)
# access to segments
for seg in bl.segments:
    print(seg)