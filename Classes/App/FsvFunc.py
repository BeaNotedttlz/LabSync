"""
Module for the SpectrumAnalyzer functions. This handles most of the logic outside the backend driver.
@autor: Merlin Schmidt
@date: 2025-15-10
@file: Classes/App/FsvFunc.py
@note: use at your own risk.
"""

import os
from Devices.FSV import SpectrumAnalyzer
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox
import pandas as pd
import matplotlib.pyplot as plt

class FsvFunctions(QObject):
	"""
	FsvFunctions class for handling SpectrumAnalyzer functions and logic.

	:param ip: Ip adress of the spectrum analyzer
	:type ip: str
	:param _storage: Parameter storage instance
	:type _storage: ParameterStorage
	:param _simulate: Flag for device simulation
	:type _simulate: bool
	:return: None
	:rtype: None
	"""
	# device signals
	port_status_signal = Signal(str, bool)

	def __init__(self, ip: str, _storage, _simulate) -> None:
		"""Constructor method
		"""
		super().__init__()

		# save port and storage in self
		# TODO connected variable completely useless
		self.ip = ip
		self.storage = _storage
		self.connected = False
		# create SpectrumAnalyzer backend driver
		self.FSV = SpectrumAnalyzer(
			name="FSV",
			_storage=self.storage,
			simulate=_simulate
		)

	def __post_init__(self) -> None:
		"""
		Post init method that opens the port after signals have been routed.

		:return: None
		:rtype: None
		"""
		try:
			# try to open device port
			self.FSV.open_port(ip=self.ip)
			self.connected = True
			# emit status signal to change indicator
			self.port_status_signal.emit("FsvPort", True)
		except ConnectionError:
			self.connected = False
			# if it fails send closed signal
			self.port_status_signal.emit("FsvPort", False)

	@Slot(bool)
	def manage_port(self, state: bool) -> None:
		"""
		Manage device port after initial opening. This is called by pressing the status buttons.

		:param state: Desired state of the device port
		:type state: bool
		:return: None
		:rtype: None
		"""
		if state:
			try:
				self.FSV.open_port(ip=self.ip)
				self.connected = True
				self.port_status_signal.emit("FsvPort", True)
			except ConnectionError as e:
				self.connected = False
				self.port_status_signal.emit("FsvPort", False)
				QMessageBox.information(
					None,
					"Error",
					"Could not open FSV Port!\n%s" % e
				)
				return
		else:
			self.FSV.close_port()
			self.connected = False
			self.port_status_signal.emit("FsvPort", False)

	@Slot(str, str, str, float, float, str, float, str, int, int)
	def start_measurement(
			self,
			meas_type: str,
			fig_name: str,
			save_path: str,
			center_frequency: float,
			span: float,
			sweep_type: str,
			bandwidth: float,
			unit: str,
			sweep_points: int,
			avg_count: int
	):
		"""
		This only sets the desired parameters to the spectrum analyzer.
		The '_save_data' private method will be run afterwards to collect and save data.

		:param meas_type: Measurement type for the sweep (Sweep, FFT)
		:type meas_type: str
		:param fig_name: Name of the figure of the data. If empty no data will be plotted.
		:type fig_name: str
		:param save_path: Save path of the collcted data.
		:type save_path: str
		:param center_frequency: Center frequency for the sweep window
		:type center_frequency: float
		:param span: Frequency span of the sweep window
		:type span: float
		:param sweep_type: Type of the sweep (Single, Average)
		:type sweep_type: str
		:param bandwidth: Frequency bandwidth for the sweep
		:type bandwidth: float
		:param unit: Unit for the signal Axis
		:type unit: str
		:param sweep_points: Amount of sweep points for the saved data
		:type sweep_points: int
		:param avg_count: Count of sweeps for average method
		:type avg_count: int
		:raises AttributeError: If the parameter is not supported.
				This cannot happen in normal LabSync operation.
		:return: None
		:rtype: None
		"""
		parameters = {
			"meas_type": meas_type,
			"fig_name": fig_name,
			"save_path": save_path,
			"center_frequency": center_frequency,
			"span": span,
			"sweep_type": sweep_type,
			"bandwidth": bandwidth,
			"unit": unit,
			"sweep_points": sweep_points,
			"avg_count": avg_count
		}
		for param, value in parameters.items():
			if param == "meas_type":
				self.FSV.meas_type = value
			if param == "fig_name":
				continue
			if param == "save_path":
				continue
			if not hasattr(self.FSV, param):
				raise AttributeError(f"FSV does not have parameter {param}")
			try:
				setattr(self.FSV, param, value)
			except Exception as e:
				QMessageBox.information(
					None,
					"Error",
					f"Could not set {param} to {value}!\n{e}"
				)
		# call method for saving data
		self._save_data(meas_type, save_path, fig_name)
		return None

	def _save_data(self, meas_type: str, save_path: str, fig_name: str) -> None:
		"""
		Private method to start the actual measurement and collect data.
		This is only called by the 'start_measurement' method setting the parameters.

		:param meas_type: Used measurement type of the data
		:type meas_type: str
		:param save_path: Given save path of the data
		:type save_path: str
		:param fig_name: Figure name of the data. None will be ignored
		:type fig_name: str | None
		:return: None
		:rtype: None
		"""
		if meas_type == "Single":
			# start single measurement
			trace_data, trace_points, nr_sweep_points = self.FSV.start_single_measurement()
		else:
			# start average measurement
			trace_data, trace_points, nr_sweep_points = self.FSV.start_avg_measurement()
		if trace_data is None:
			QMessageBox.information(
				None,
				"Error",
				"No data received from FSV!"
			)
			return None

		# save data to DataFrame
		df = pd.DataFrame({
			'Frequenz[Hz]': [float(f) for f in trace_points.split(",")],
			f'Power[{self.FSV.unit}]': [float(p) for p in trace_data.split(",")]
		})

		# save data to disk
		with open(os.path.join(save_path, "TraceResults.csv"),'w') as file:
			df.to_csv(
				file,
				sep=';',
				index=False,
			)

		# plot data
		if fig_name != "":
			plt.figure(figsize=[10,6])
			plt.plot(df['Frequenz[Hz]'], df[f'Power[{self.FSV.unit}]'], label='Trace Data')
			plt.xlabel('Frequenz [Hz]')
			plt.ylabel(f'Power [{self.FSV.unit}]')
			plt.title(fig_name)
			plt.grid()
			plt.savefig(os.path.join(save_path, fig_name+".png"), dpi=300)
			plt.close()
		else:
			return None






