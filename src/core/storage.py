# python
from typing import Any, Dict
from PySide6.QtCore import QObject, Signal

class InstrumentCache(QObject):
	"""
	Class for caching instrument parameters and respective values.
	Stores values internally with keys as (device, parameter) tuples but
	serializes to a nested dict for JSON compatibility.
	"""
	# TODO This signal can be used to update the UI from loading cached values
	# However this will double update if values are set normally!
	valueChanged = Signal(tuple)

	def __init__(self) -> None:
		super().__init__()
		self._cache: Dict[tuple, Any] = {}

	def get_value(self, device: str, parameter: str) -> Any | None:
		key = (device, parameter)
		return self._cache.get(key)

	def set_value(self, device: str, parameter: str, value: Any) -> None:
		key = (device, parameter)
		if key in self._cache:
			if self._cache[key] != value:
				self._cache[key] = value
		else:
			self._cache[key] = value

	def save_cache(self) -> Dict[str, Dict[str, Any]]:
		"""
		Return a JSON-serializable nested dictionary:
		{ device_id: { parameter: value, ... }, ... }
		"""
		out: Dict[str, Dict[str, Any]] = {}
		for (device, parameter), value in self._cache.items():
			out.setdefault(device, {})[parameter] = value
		return out

	def load_preset(self, cache: Any) -> None:
		"""
		Load a preset into the internal cache. Accepts multiple shapes for
		compatibility:
		 - nested dict: { device: { parameter: value } }
		 - list of entries: [ { "device": "...", "parameter": "...", "value": ... }, ... ]
		 - legacy dict with stringified tuple keys: "{('device','param'): value, ...}" or "device:param"
		Values are set via set_value so change signals fire.
		"""
		# Nested dict format: { device: { parameter: value } }
		if isinstance(cache, dict):
			# check for nested-dict shape
			if all(isinstance(k, str) and isinstance(v, dict) for k, v in cache.items()):
				for device, params in cache.items():
					if isinstance(params, dict):
						for parameter, value in params.items():
							self.set_value(device, parameter, value)
				return

			# fallback: dict with tuple-like or custom string keys
			parsed_any = False
			for key, value in cache.items():
				if isinstance(key, tuple) and len(key) == 2:
					self.set_value(key[0], key[1], value)
					parsed_any = True
					continue
				if isinstance(key, str):
					s = key.strip()
					# pattern: (device, parameter) or 'device','parameter'
					if s.startswith("(") and s.endswith(")"):
						inner = s[1:-1]
						parts = inner.split(",", 1)
						if len(parts) == 2:
							dev = parts[0].strip().strip('\'" ')
							param = parts[1].strip().strip('\'" ')
							self.set_value(dev, param, value)
							parsed_any = True
							continue
					# pattern: device:parameter
					if ":" in s:
						dev, param = s.split(":", 1)
						self.set_value(dev.strip(), param.strip(), value)
						parsed_any = True
						continue
			if parsed_any:
				return

		# List of entry dicts format
		if isinstance(cache, list):
			for entry in cache:
				if not isinstance(entry, dict):
					continue
				dev = entry.get("device")
				param = entry.get("parameter")
				val = entry.get("value")
				if dev is not None and param is not None:
					self.set_value(dev, param, val)
			return

		# If nothing matched, do nothing
		return