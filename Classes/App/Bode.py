import numpy as np
from PyQt5.QtWidgets import QMessageBox
from PySide6.QtCore import Signal, Slot, QObject

from Devices.TGA import FrequencyGenerator
from Devices.RhodeSchwarz import SpectrumAnalyzer

class BodePlot(QObject):
	data_signal = Signal(list, list)

	def __init__(self, FrequencyGenerator: FrequencyGenerator, FSV3000: SpectrumAnalyzer):
		super().__init__()
		self.FrequencyGenerator = FrequencyGenerator
		self.FSV3000 = FSV3000

	@Slot(float, float)
	def get_bode(self, min_freq: float, max_freq: float):
		log_freq = np.logspace(np.log10(min_freq), np.log10(max_freq), num=100)
		self.FSV3000.span = 1e3
		self.FSV3000.sweep_points = 2001
		self.FSV3000.sweep_type = "SWE"
		self.FSV3000.unit = "DBM"

		ampl_data = np.array([], dtype=float)
		trace_points = np.array([], dtype=float)

		for i in range(len(log_freq)):
			self.FrequencyGenerator.frequency = ((1,log_freq[i]))
			self.FSV3000.center_frequency = log_freq[i]
			self.FSV3000.bandwidth = log_freq[i]*5*10e-4

			if self.FSV3000.simulate:
				trace_points = log_freq
				trace_data = np.random.randn(len(trace_points))
			else:
				trace_data, trace_points, _ = self.FSV3000.start_single_measurement()
				trace_data = np.array(trace_data.split(","), dtype=float)
				trace_points = np.array(trace_points.split(","), dtype=float)

			if trace_data is None:
				QMessageBox.information(
					None,
					"Error",
					"No data received from FSV!"
				)
				return
			idx = np.argmin(np.abs(trace_points - log_freq[i]))
			ampl = trace_data[idx]
			ampl_data = np.append(ampl_data, ampl)


		self.data_signal.emit(trace_points, ampl_data)

