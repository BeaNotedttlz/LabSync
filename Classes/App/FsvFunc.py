import os

from Devices.RhodeSchwarz import SpectrumAnalyzer
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox
import pandas as pd
import matplotlib.pyplot as plt


class FsvFunctions(QObject):
	port_status_signal = Signal(str, bool)

	def __init__(self, ip: str, _storage) -> None:
		super().__init__()
		self.ip = ip
		self.storage = _storage
		self.connected = False
		self.FSV = SpectrumAnalyzer(
			name="FSV",
			_storage=self.storage,
			simulate=True
		)

	def __post_init__(self) -> None:
		try:
			self.FSV.open_port(ip=self.ip)
			self.connected = True
			self.port_status_signal.emit("FsvPort", True)
		except ConnectionError:
			self.connected = False
			self.port_status_signal.emit("FsvPort", False)

	@Slot(bool)
	def manage_port(self, state: bool) -> None:
		if state:
			try:
				self.FSV.open_port(ip=self.ip)
				self.connected = True
				self.port_status_signal.emit("FsvPort", True)
			except ConnectionError as e:
				self.connected = False
				self.port_status_signal.emit("FSVPort", False)
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
				continue
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
		self._save_data(meas_type, save_path, fig_name)

	def _save_data(self, meas_type: str, save_path: str, fig_name: str) -> None:
		if meas_type == "Single":
			trace_data, trace_points, nr_sweep_points = self.FSV.start_single_measurement()
		else:
			trace_data, trace_points, nr_sweep_points = self.FSV.start_avg_measurement()
		if trace_data is None:
			QMessageBox.information(
				None,
				"Error",
				"No data received from FSV!"
			)
			return

		df = pd.DataFrame({
			'Frequenz[Hz]': [float(f) for f in trace_points.split(",")],
			f'Power[{self.FSV.unit}]': [float(p) for p in trace_data.split(",")]
		})

		with open(os.path.join(save_path, "TraceResults.csv"),'w') as file:
			df.to_csv(
				file,
				sep=';',
				index=False,
			)

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
			return






