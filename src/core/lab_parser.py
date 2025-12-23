"""
Module for storing device parameters dynamically on runtime. This will then be used to save and load a preset.
This acts as a parser for the custom .lab file format used by LabSync.
This allows for human readable storage of parameters as well as easy editing syntax.
However the .toml format could be considered in the future for more complex structures.
@author: Merlin Schmidt
@date: 2025-02-12
@file: src/core/storage.py
@note:
"""

import re
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

class LabFileParser:
	"""
	Handles reading/writing of the custom lab file format.
	Format:
	[DeviceName]
	Parameter = Value
	Parameter[Index] = Value
	with # as the comment indicator to ignore those lines
	"""

	@staticmethod
	def parse_value_string(val_str) -> bool | int | float | str:
		"""
		Helper to cast string to Types (bool -> int -> float -> str)
		:param val_str: String to parse
		:type val_str: str
		:return: The data and respective type
		:rtype: bool | int | float | str
		"""
		val_str = val_str.strip()

		# check for boolean values
		# return True for "TRUE", "ON"
		if val_str.upper() in ("TRUE", "ON"): return True
		# return False for "FALSE", "OFF"
		if val_str.upper() in ("FALSE", "OFF"): return False

		# check for integer values
		try:
			return int(val_str)
		except ValueError:
			pass

		# check for float values
		try:
			return float(val_str)
		except ValueError:
			pass

		# string (remove quotes if present)
		return val_str.strip('"').strip("'")

	@staticmethod
	def load(filepath) -> Tuple[Dict[Tuple[str, str], Any], Exception | None]:
		"""
		Get the .lab file and parse it into the respective dictionary.
		:param filepath: Filepath to the .lab file
		:type filepath: str
		:return: The cache dictionary
		:rtype: dict
		"""
		data: Dict[Tuple[str, str], Any] = {}
		current_device = "Global"

		# Regex: Matches "Parameter" or "Parameter[Index]"
		# Group 1: Parameter Name, Group 2: Index (optional) Group 3: Value
		line_pattern = re.compile(r"^(\w+)(?:\[(\d+)])?\s*=\s*(.*)$")
		section_pattern = re.compile(r"^\[(.*)]$")

		try:
			with open(filepath, 'r', encoding='utf-8') as f:
				lines = f.readlines()
				f.close()

			for line in lines:
				line = line.strip()
				if not line or line.startswith('#'): continue

				sec_match = section_pattern.match(line)
				if sec_match:
					current_device = sec_match.group(1).strip()
					continue

				match = line_pattern.match(line)
				if match:
					parameter = match.group(1)
					index = match.group(2)
					value_str = match.group(3).split('#')[0].strip()

					value = LabFileParser.parse_value_string(value_str)

					key = (current_device, parameter)

					if index:
						idx = int(index)
						if key not in data: data[key] = {}
						if not isinstance(data[key], dict): data[key] = {}
						data[key][idx] = value
					else:
						data[key] = value
			return data, None
		except FileNotFoundError as e:
			return {}, e

	@staticmethod
	def save(filepath: str, data: Dict[Tuple[str, str], Any]) -> Tuple[bool, Exception | None]:
		"""
		Save the current cache dictionary into a .lab file.
		:param filepath: Filepath to save the .lab file
		:type filepath: str
		:param data: Data from the cache
		:type data: Dict[Tuple[str, str], Any]
		:return: If the saving process was successful and error message if any
		:rtype: Tuple[bool, str]
		"""
		organized = {}
		for (device, parameter), value in data.items():
			if device not in organized: organized[device] = {}
			organized[device][parameter] = value

		try:
			with open(filepath, 'w', encoding='utf-8') as f:
				f.write('# Lab Instrument configuration file\n')
				save_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				f.write(f"# Saved on {save_time}\n\n")

				for device, params in organized.items():
					f.write(f"[{device}]\n")


					for param, value in params.items():
						if isinstance(value, dict):
							for idx in sorted(value.keys()):
								f.write(f"\t{param}[{idx}] = {value[idx]}\n")

						else:
							f.write(f"\t{param} = {value}\n")
					f.write("\n")

				f.close()
				return True, None
		except Exception as e:
			return False, e

