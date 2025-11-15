"""
Module for Bodeplot functionality
@autor: Merlin Schmidt
@date: 2024-06-10
@file: Classes/App/Bode.py
@note: use at your own risk.
"""

import numpy as np
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Signal, Slot, QObject

from Devices.TGA import FrequencyGenerator
from Devices.FSV import SpectrumAnalyzer

class BodePlot(QObject):
	"""
	BodePlot class for collecting and saving frequency response data.
	This includes the TGA1244 and the FSV3000 devices to measure and collect frequency response data.

	:param FrequencyGernerator: Instance of the TGA1244 device
	:type FrequencyGenerator: FrequencyGenerator
	:param FSV3000: Instance of the FSV3000 device
	:type FSV3000: SpectrumAnalyzer
	:return: None:
	:rtype: None
	"""
	data_signal = Signal(list, list)

	def __init__(self, FrequencyGenerator: FrequencyGenerator, FSV3000: SpectrumAnalyzer):
		"""Constructor method
		"""
		super().__init__()
		self.FrequencyGenerator = FrequencyGenerator
		self.FSV3000 = FSV3000

	@Slot(float, float)
	def get_bode(self, min_freq: float, max_freq: float) -> None:
		"""
		Íterate through each frequency and collect frequency response data.


		:param min_freq: Start frequency for the sweep
		:type min_freq: float
		:param max_freq: Stop frequency for the sweep
		:type max_freq: float
		:return: None
		:rtype: None
		"""
		# make the interpolation between the min and max logarithmic
		log_freq = np.logspace(np.log10(min_freq), np.log10(max_freq), num=100)
		# setup spectrum analyzer
		self.FSV3000.span = 1e3
		self.FSV3000.sweep_points = 2001
		self.FSV3000.sweep_type = "SWE"
		self.FSV3000.unit = "DBM"

		# initialize data arrays
		ampl_data = np.array([], dtype=float)
		trace_points = np.array([], dtype=float)

		for i in range(len(log_freq)):
			# run for each frequency
			self.FrequencyGenerator.frequency = ((1,log_freq[i]))
			self.FSV3000.center_frequency = log_freq[i]
			self.FSV3000.bandwidth = log_freq[i]*5*10e-4

			if self.FSV3000.simulate:
				# for simulation return random data
				trace_points = log_freq
				trace_data = np.random.randn(len(trace_points))
			else:
				# otherwise collect data
				trace_data, trace_points, _ = self.FSV3000.start_single_measurement()
				trace_data = np.array(trace_data.split(","), dtype=float)
				trace_points = np.array(trace_points.split(","), dtype=float)

			# Return error if no data was collected
			if trace_data is None:
				QMessageBox.information(
					None,
					"Error",
					"No data received from FSV!"
				)
				return None
			# only save amplitude at the frequency of the sweep point
			idx = np.argmin(np.abs(trace_points - log_freq[i]))
			ampl = trace_data[idx]
			ampl_data = np.append(ampl_data, ampl)

		# emit signal with data
		self.data_signal.emit(trace_points, ampl_data)
		return None
