from typing import List
import requests
import traceback
from tqdm import tqdm
from pathlib import Path
import os

def download_files(file_urls: List[str], filenames: List[str], dest_dir: Path, overwrite_existing_files: bool = False):
    assert len(file_urls) == len(filenames)
    try:
        if dest_dir.exists() == False:
            dest_dir.mkdir(parents = True)
        for url, fname in tqdm(zip(file_urls, filenames), total = len(file_urls), desc = "Downloading test files"):
            fpath: Path = Path(os.path.join(dest_dir, fname))
            # don't download existing files again
            if not fpath.exists() or overwrite_existing_files:
                req = requests.get(url, allow_redirects = True)
                open(fpath, 'wb').write(req.content)
    except:
        traceback.print_exc()
