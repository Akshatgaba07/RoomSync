"""OPTIONAL auxiliary data: IPIP Big Five (OpenPsychometrics, ~1M responses to the 50-item IPIP-FFM).
NOT downloaded in the shipped project (the build sandbox could not reach openpsychometrics.org / Kaggle).
It has NO roommate or pair labels and cannot be joined to the Bennett survey, so the shipped engine does not use it.
Run:  python datasets/external/fetch_big5.py"""
import io, urllib.request, zipfile
from pathlib import Path
URL = "https://openpsychometrics.org/_rawdata/IPIP-FFM-data-8Nov2018.zip"
out = Path(__file__).parent / "big5"; out.mkdir(exist_ok=True)
with urllib.request.urlopen(URL, timeout=60) as r:
    zipfile.ZipFile(io.BytesIO(r.read())).extractall(out)
print("saved to", out, "- check the dataset's terms on openpsychometrics.org before redistributing")
