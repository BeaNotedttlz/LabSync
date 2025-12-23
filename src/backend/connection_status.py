from enum import Enum, auto

class ConnectionStatus(Enum):
	"""
	Enum for handling the connection status of the serial devices
	"""
	DISCONNECTED = auto()

	CONNECTED = auto()

	ERROR = auto()

	DISCONNECTING = auto()