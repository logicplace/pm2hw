import json
import urllib.request
from pathlib import Path

from pm2hw.gui.util import Semver
from pm2hw.config import resource_dir, save as save_config

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
	from pm2hw import __version__ as pm2hw_version
	pm2hw_semver = Semver(pm2hw_version)
 
	rsc_semver = get_current_resource_version()

	with urllib.request.urlopen(VERSION_URL) as f:
		res: dict = json.loads(f.read())
		latest_result = res

	return {
		k: {"current": cur_ver, "latest": new_ver}
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

def prompt_update(show_none=True):
	import sys
	from tkinter import messagebox
	
	from pm2hw.logger import log, exception
	from pm2hw.locales import delayed_gettext as _

	log(_("log.update.intro"))
	res = check_for_updates()
	if "resourcePack" in res:
		log(_("log.update.resourcePack.found"))
		if messagebox.askyesno(
			_("help.update.resourcePack.title"),
			_("help.update.resourcePack.message").format(**res["resourcePack"]),
		):
			try:
				install_resource_update()
			except Exception as err:
				log(_("log.update.resourcePack.failed"))
				exception(err.args[0], err)
			else:
				log(_("log.update.resourcePack.success"))

	if "core" in res:
		log(_("log.update.core.found"))
		if getattr(sys, "frozen", False):
			base = Path(sys.executable).parent
			if messagebox.askyesno(
				_("help.update.core.title"),
				_("help.update.core.message.ask").format(**res["core"]),
			):
				import os, shutil

				try:
					url = latest_result["components"]["core"]["windows"]
					with urllib.request.urlopen(url) as f:
						with (base / "update.zip").open("wb") as out:
							out.write(f)

					update_script = base / "update.ps1"
					with update_script.open("wt") as out:
						escaped = str(base).replace("'", "''")
						out.write(
							f"Expand-Archive 'update.zip' '{escaped}' -Force\n"
							".\pm2hww.exe"
						)
				except Exception as err:
					log(_("log.update.core.failed"))
					exception(err.args[0], err)
				else:
					log(_("log.update.core.success"))

				# Find PowerShell exe
				powershell = shutil.which("powershell")

				from pm2hw import root
				root.destroy()
				save_config()

				# Switch to update process
				os.execl(powershell, '-File', str(update_script))
		else:
			messagebox.showinfo(
				_("help.update.core.title"),
				_("help.update.core.message.show").format(**res["core"])
			)

	if not res:
		log(_("log.update.no-update.found"))
		if show_none:
			messagebox.showinfo(
				_("help.update.no-update.title"),
				_("help.update.no-update.message")
			)
