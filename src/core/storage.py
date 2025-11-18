

from typing import Any, Dict
class InstrumentCache:

	def __init__(self) -> None:
		self._cache: Dict[tuple, Any] = {}

	def set_value(self, device: str, parameter: str,
				  value: Any, force: bool=False) -> None:
		key = (device, parameter)
		if key not in self._cache:
			raise KeyError(f"Parameter {parameter} for {device} not found in cache.")
		cached_value = self._cache[key]
		is_same = (cached_value == value)

		if is_same and force:
			self._cache[key] = value
			return None
		else:
			pass
		self._cache[key] = value
		return None

	def get_value(self, device: str, parameter: str) -> Any:
		key = (device, parameter)
		if key not in self._cache:
			raise KeyError(f"Parameter {parameter} for {device} not found in cache.")
		return self._cache[key]

	def save_preset(self) -> Dict[tuple, Any]:
		return self._cache.copy()

	def load_preset(self, preset: Dict[tuple, Any]) -> None:
		self._cache = preset.copy()
		return None

