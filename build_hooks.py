import os
from typing import TYPE_CHECKING

from whey import builder
from whey.mixin import BuilderMixin

if TYPE_CHECKING:
	from domdf_python_tools.paths import PathPlus


class GettextMixin:
	def build_messages(self: BuilderMixin):
		from babel.messages.mofile import write_mo
		from babel.messages.pofile import read_po

		locales = self.pkgdir / "locales"
		if self.verbose:
			print("  Building messages")

		for po in locales.glob("*/LC_MESSAGES/pm2hw.po"):
			with po.open("rt", encoding="UTF-8") as f:
				catalog = read_po(f, po.parts[-3], po.stem)

			mo = self.build_dir / po.relative_to(self.project_dir).with_suffix(".mo")
			mo.parent.maybe_make(parents=True)
			with mo.open("wb") as f:
				write_mo(f, catalog)
			self.report_written(mo)

			if self.verbose:
				print("    Wrote language file:", mo)


class ExeBuilder(GettextMixin, builder.AbstractBuilder):
	@property
	def default_build_dir(self) -> "PathPlus":
		"""
		Provides a default for the ``build_dir`` argument.
		"""

		return self.project_dir / "build" / "exe"

	def create_exe(self):
		import sys
		from cx_Freeze import setup, Executable

		build_exe_options = {
			"build_exe": str(self.out_dir),
			"excludes": ["appdirs"],
		}

		# base="Win32GUI" should be used only for Windows GUI app
		base = "Console"

		sys.argv[1:] = ["build"]

		setup(
			name = self.config["name"],
			version = str(self.config["version"]),
			description = self.config["description"],
			options = {"build_exe": build_exe_options},
			executables = [Executable("main.py", base=base)]
		)

	def build_exe(self) -> str:
		"""
		Build the Windows EXE distribution.

		:return: The filename of the created EXE.
		"""

		self.clear_build_dir()

		self.build_messages()

		return self.create_exe()

	build = build_exe


class PyInstallerBuilder(GettextMixin, builder.AbstractBuilder):
	# TODO: understand these systems better

	@property
	def default_build_dir(self) -> "PathPlus":
		"""
		Provides a default for the ``build_dir`` argument.
		"""

		return self.project_dir / "build" / "exe"

	def write_spec(self):
		import PyInstaller.building.makespec
		name = self.config["name"]
		self.spec_file = PyInstaller.building.makespec.main(
			["main.py"],
			name=name,
			excludes=["appdirs"],
			datas=[(str(self.build_dir / name / "locales"), "pm2hw/locales")],
			collect_all=[],
			collect_data=[],
			collect_binaries=[],
			collect_submodules=[],
			copy_metadata=[],
			recursive_copy_metadata=[],
		)

	def create_exe(self):
		import PyInstaller.building.build_main

		PyInstaller.building.build_main.main(
			None,
			self.spec_file,
			False,
			workpath=str(self.build_dir.absolute()),
			distpath=str(self.out_dir.absolute()),
		)

	def build_exe(self) -> str:
		"""
		Build the Windows EXE distribution.

		:return: The filename of the created EXE.
		"""

		self.clear_build_dir()

		self.build_messages()
		self.write_spec()

		return self.create_exe()

	build = build_exe


# class SDistBuilder(GettextMixin, builder.SDistBuilder):
# 	def call_additional_hooks(self):
# 		self.build_messages()


# class WheelBuilder(GettextMixin, builder.WheelBuilder):
# 	def call_additional_hooks(self):
# 		self.build_messages()
