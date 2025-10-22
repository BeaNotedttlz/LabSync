'''
Class for custom Exception to raise in certain Situations
'''

class ParameterNotSetError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)
	def __str__(self) -> str:
		return self.message

class DeviceParameterError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)
	def __str__(self) -> str:
		return self.message

class ParameterOutOfRangeError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)
	def __str__(self) -> str:
		return self.message

class UIParameterError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)

	def __str__(self) -> str:
		return self.message