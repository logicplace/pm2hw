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

def get_current_resource_version():
	rsc_version = resource_dir / "version.txt"
	return Semver(
		rsc_version.read_text()
		if rsc_version.exists() else
		"0.0.1"
	)

def check_for_updates():
	global latest_result
	from .. import __version__ as pm2hw_version
	pm2hw_semver = Semver(pm2hw_version)
 
	rsc_semver = get_current_resource_version()

	# urllib.request.urlopen(VERSION_URL)
	with open("latest.json") as f:
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
	import io, zipfile
	if not latest_result:
		check_for_updates()

	rp = latest_result["components"]["resourcePack"]
	if get_current_resource_version() < Semver(rp["version"]):
		with urllib.request.urlopen(rp["url"]) as f:
			z = zipfile.ZipFile(io.BytesIO(f.read()), "r")
			z.extractall(resource_dir)
