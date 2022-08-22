from pathlib import Path

__version__ = "0.1"

def graphic(fn):
	me = Path(__file__).absolute().parent
	assert ".." not in fn
	p: Path = me / fn
	return p if p.exists() else ""
