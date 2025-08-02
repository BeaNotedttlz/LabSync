from PySide6.QtCore import QObject, Signal, Slot

class SignalHandler(QObject):
	def __init__(self) -> None:
		super().__init__()

	def route(self, sender, signal_name, receiver, slot) -> None:
		signal = getattr(sender, signal_name)
		slot = getattr(receiver, slot)
		signal.connect(slot)
		return None
