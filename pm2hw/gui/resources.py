import json
import urllib.request
from pathlib import Path

from .util import Semver
from ..config import resource_dir

VERSION_URL = "https://raw.githubusercontent.com/logicplace/pm2hw/master/latest.json"

latest_result = None

def graphic(fn, *, rel=resource_dir):
	assert ".." not in fn
	p: Path = rel / fn
	return p if p.exists() else ""

def check_for_updates():
	global latest_result
	from .. import __version__ as pm2hw_version
	pm2hw_semver = Semver(pm2hw_version)
 
	rsc_version = resource_dir / "version.txt"
	rsc_semver = Semver(
		rsc_version.read_text()
		if rsc_version.exists() else
		"0.0.1"
	)

	with urllib.request.urlopen(VERSION_URL) as f:
		res: dict = json.loads(f.read())
		latest_result = res

	return {
		k: new_ver
		for k, cur_ver in [
			("core", pm2hw_semver),
			("resourcePack", rsc_semver),
		]
		for new_ver in (res["components"][k]["version"],)
		if cur_ver < Semver(new_ver)
	}

def install_resource_update():
	import zipfile
	if not latest_result:
		check_for_updates()

	url = latest_result["components"]["resourcePack"]["url"]
	with urllib.request.urlopen(url) as f:
		z = zipfile.ZipFile(f, "r")
		z.extractall(resource_dir)
