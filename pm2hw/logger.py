# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
import logging
import configparser
from typing import Sequence, Set
from logging import NOTSET, DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL, LogRecord, _levelToName, _nameToLevel

from . import __name__ as logger_name
from .locales import _

PROTOCOL = 5
VERBOSE = INFO - 1

ALL = "ALL"
LOG = "INFO.LOG"
PROGRESS = "INFO.PROGRESS"
EXCEPTION = "ERROR.EXCEPTION"
FATAL = "CRITICAL.FATAL"

_levelToName.update({
	VERBOSE: "VERBOSE",
	PROTOCOL: "PROTOCOL",
})

_nameToLevel.update({
	"EXCEPTION": ERROR,
	"VERBOSE": VERBOSE,
	"PROTOCOL": PROTOCOL,
})

def get_level_from_name(name: str):
	level, *_ = name.split(".", 1)
	return _nameToLevel[level]


view = "cli"
logger = logging.getLogger(logger_name)

class SubtypedMessage:
	def __init__(self, msg: str, subtype: str):
		self._msg = msg
		self._subtype = subtype.upper()

	@property
	def subtype(self):
		return self._subtype

	def __str__(self):
		return str(self._msg)

class Formatter(logging.Formatter):
	default_time_format = "%H:%M:%S"
	default_msec_format = "%s.%03d"
	default_shortlevelname = {
		f"{INFO}.LOG": "   ",
		f"{INFO}.PROGRESS": "   ",
	}
	default_shortlevelname_format = "{0[0]}: "

	def __init__(self, fmt=None, datefmt=None) -> None:
		super().__init__(fmt, datefmt, "{", True)

	def format(self, record: LogRecord):
		if isinstance(record.msg, SubtypedMessage):
			levelname = record.msg.subtype
			lookup = f"{record.levelno}.{levelname}"
		else:
			levelname = record.levelname
			lookup = str(record.levelno)
		record.shortlevelname = self.default_shortlevelname.get(
			lookup,
			self.default_shortlevelname_format.format(levelname)
		)
		return super().format(record)

class MonospacePrefixFormatter(Formatter):
	def formatMessage(self, record: LogRecord):
		beginning = self._style.format(record)
		if "\n" in record.message:
			# TODO: regard character widths (narrow/wide)
			prefix = " " * len(beginning)
			lines = record.message.splitlines(keepends=True)
			return beginning + prefix.join(lines)
		return beginning + record.message

class Handler(logging.Handler):
	def __init__(self, level, *, handler=None, raw_handler=None) -> None:
		super().__init__(level)
		self._handler = raw_handler or handler or (lambda r: None)
		self._raw = bool(raw_handler)

	def set_handler(self, handler):
		self._handler = handler

	def handle(self, record: LogRecord) -> bool:
		return super().handle(record)

	def emit(self, record):
		self._handler(record if self._raw else self.format(record))

	add_filter = logging.Handler.addFilter

	def add_subtype_filter(self, level: int, allow: Sequence[str] = (), reject: Sequence[str] = ()):
		def filterer(record: LogRecord):
			if record.levelno == level:
				subtype = record.msg.subtype if isinstance(record.msg, SubtypedMessage) else ""
				if allow:
					return subtype in allow
				if reject:
					return subtype not in reject
			return True
		self.addFilter(filterer)

	set_formatter = logging.Handler.setFormatter

class PiecewiseFilter(logging.Filter):
	def __init__(self, name):
		super().__init__(name)
		self.enabled: Set[str] = set()
		self.disabled: Set[str] = set()
		self.default_enabled = True

	def filter(self, record: LogRecord):
		if not super().filter(record):
			# Name check failed
			return False
		lookup = (
			f"{record.levelname}.{record.msg.subtype}"
			if isinstance(record.msg, SubtypedMessage) else
			record.levelname
		)
		res = (
			lookup not in self.disabled
			if self.default_enabled else
			lookup in self.enabled
		)
		return res

	def _xable(self, args):
		what = {_levelToName.get(a, str(a)).upper() for a in args}
		has_all = "ALL" in what
		if has_all:
			what.remove("ALL")
		return what, has_all

	def enable(self, *args, update_logger=False):
		what, had_all = self._xable(args)
		if had_all:
			self.default_enabled = True
		self.enabled.update(what)
		self.disabled -= what
		if update_logger:
			self.set_level_to_min()

	def disable(self, *args: str, update_logger=False):
		what, had_all = self._xable(args)
		if had_all:
			self.default_enabled = False
		self.disabled.update(what)
		self.enabled -= what
		if update_logger:
			self.set_level_to_min()

	def set_level_to_min(self):
		if self.name:
			level = min(map(get_level_from_name, self.enabled))
			logger = logging.getLogger(self.name)
			logger.setLevel(level)

logger_filter = PiecewiseFilter(logger_name)
logger.addFilter(logger_filter)
enable = logger_filter.enable
disable = logger_filter.disable
add_filter = logger.addFilter
remove_filter = logger.removeFilter
add_handler = logger.addHandler
remove_handler = logger.removeHandler
set_level = logger.setLevel
get_effective_level = logger.getEffectiveLevel
is_enabled_for = logger.isEnabledFor

nice_formatter = MonospacePrefixFormatter("[{asctime}] {shortlevelname}")

def add_log_only_handler():
	handler = Handler(logging.INFO)
	handler.set_formatter(nice_formatter)
	handler.add_filter(lambda record: record.levelno == logging.INFO)
	add_handler(handler)
	return handler


def protocol(msg, data=None, **kwargs):
	if is_enabled_for(PROTOCOL):
		if data:
			msg = " ".join((msg, *(f"{b:02x}" for b in data)))
		else:
			msg = msg.format(**kwargs)
		logger.log(PROTOCOL, msg)

def debug(msg, **kwargs):
	logger.debug(msg.format(**kwargs))

def verbose(msg, **kwargs):
	logger.log(VERBOSE, msg.format(**kwargs))

def info(msg, **kwargs):
	logger.info(msg.format(**kwargs))

def log(msg, **kwargs):
	logger.info(SubtypedMessage(msg.format(**kwargs), "LOG"))

class ProgressConfig(configparser.ConfigParser):
	is_loaded = False

	def __init__(self):
		super().__init__(
			interpolation=configparser.ExtendedInterpolation(),
		)

	def load(self, cfg: str, force=False):
		if force or not self.is_loaded:
			self.read_string(str(cfg))
			self.is_loaded = True

	def get_message(self, mode: str):
		self.load(_("log.progress"))
		return ProgressMessage(self[mode])

class ProgressMessage:
	def __init__(self, section):
		self.section = section

	def format_as(self, progress: "progress", view: str):
		fmt: str
		if progress.current == 0:
			fmt = self.section.get(f"{view}.initial")
		elif progress.is_complete():
			fmt = self.section.get(f"{view}.final")
		else:
			fmt = self.section.get(f"{view}.medial")

		return fmt.format(
			*(
				self.section.get(f"message.{i}")
				for i in range(int(self.section.get("count")))
			),
			suffix=self.section.get("suffix"),
			completed=self.section.get("completed"),
		)

class progress(SubtypedMessage):
	config = ProgressConfig()

	def __init__(self, msg: ProgressMessage, end: int, *, level="INFO", **kwargs):
		super().__init__(msg, "PROGRESS")
		self.msg = msg

		self.current = 0
		self.percent = 0
		self.end = end
		self.kwargs = kwargs
		self.record = logger.makeRecord(
			logger_name, _nameToLevel.get(level, level),
			"(unknown file)", 0, self, [],
			None, "(unknown function)", None, None
		)
		self.updated = self.created = self.record.created
		logger.handle(self.record)

	def add(self, value: int):
		self.update(self.current + value)

	def update(self, value: int):
		self.current = value
		self.percent = value * 100 / self.end
		self.updated = time.time()
		logger.handle(self.record)

	def done(self):
		""" Force a done state """
		if self.end > self.current:
			self.end = self.current

	def is_complete(self):
		return self.current >= self.end

	def time_taken(self):
		return self.updated - self.created

	def __str__(self):
		msg = self.msg.format_as(self, view)
		return msg.format(
			cur=self.current,
			pc=self.percent,
			end=self.end,
			secs=self.time_taken(),
			**self.kwargs
		)

def warn(msg, **kwargs):
	logger.warn(msg.format(**kwargs))

warning = warn

def error(msg, **kwargs):
	logger.error(msg.format(**kwargs))

def critical(msg, **kwargs):
	logger.critical(msg.format(**kwargs))

def fatal(msg, **kwargs):
	logger.fatal(SubtypedMessage(msg.format(**kwargs), "FATAL"))

def exception(msg, exc_info=True, **kwargs):
	logger.exception(SubtypedMessage(msg.format(**kwargs), "EXCEPTION"), exc_info=exc_info)
