import time
import logging
from typing import Sequence, Set, Tuple, Union
from logging import NOTSET, DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL, LogRecord

from . import __name__ as logger_name

PROTOCOL = 5
VERBOSE = INFO - 1

ALL = "ALL"
LOG = "INFO.LOG"
PROGRESS = "INFO.PROGRESS"
EXCEPTION = "ERROR.EXCEPTION"
FATAL = "CRITICAL.FATAL"

_levelToName = {
	VERBOSE: "VERBOSE",
	PROTOCOL: "PROTOCOL",
	**logging._levelToName
}

_nameToLevel = {
	"EXCEPTION": ERROR,
	"VERBOSE": VERBOSE,
	"PROTOCOL": PROTOCOL,
	**logging._nameToLevel
}

def get_level_from_name(name: str):
	level, *_ = name.split(".", 1)
	return _nameToLevel[level]


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

_OneToThreeStrings = Union[str, Tuple[str], Tuple[str, str], Tuple[str, str, str]]

class progress(SubtypedMessage):
	class prefixed(str):
		prefix: str

		def __new__(self, prefix: str, suffix: str):
			return str.__new__(self, prefix + suffix)

		def __init__(self, prefix: str, suffix: str):
			self.prefix = prefix

	@classmethod
	def basic(cls, prefix: str):
		return (
			cls.prefixed(prefix, ": {cur}/{end} ({pc:.0f}%)"),
			"  Completed in {secs:.3f}s"
		)

	def __init__(self, msg: _OneToThreeStrings, end: int, *, level="INFO", **kwargs):
		super().__init__(msg, "PROGRESS")
		if isinstance(msg, str):
			self.msg, self.final_msg = msg, None
		else:
			lmsg = len(msg)
			self.msg = msg[0]
			self.final_msg = msg[1] if lmsg >= 2 else None
			self.final_form = msg[2] if lmsg >= 3 else "{}\n{}"

		self.current = 0
		self.percent = 0
		self.end = end
		self.kwargs = kwargs
		self.record = logger.makeRecord(
			logger_name, _nameToLevel.get(level, level),
			"(unknown file)", 0, self, [],
			None, "(unknown function)", None, None
		)
		self.created = self.time = self.record.created
		logger.handle(self.record)

	def add(self, value: int):
		self.update(self.current + value)

	def update(self, value: int):
		self.current = value
		self.percent = value * 100 / self.end
		self.time = time.time()
		logger.handle(self.record)

	def done(self):
		""" Force a done state """
		if self.end > self.current:
			self.end = self.current

	def is_complete(self):
		return self.current >= self.end

	def time_taken(self):
		return self.time - self.created

	def __str__(self):
		seconds = self.time_taken()
		if self.final_msg and self.current >= self.end:
			# Finished
			msg = self.final_form.format(self.msg, self.final_msg)
		else:
			msg = self.msg
		return msg.format(
			cur=self.current,
			pc=self.percent,
			end=self.end,
			secs=seconds,
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
