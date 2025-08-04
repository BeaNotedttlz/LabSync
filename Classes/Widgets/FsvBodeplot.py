import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QFileDialog
from matplotlib.ticker import LogLocator, ScalarFormatter

from Classes.Widgets.fields import _create_input_field
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class BodePlotWindow(QDialog):
    start_signal = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bode Plot")
        self.setGeometry(1000, 100, 760, 600)

        self.main_layout = QVBoxLayout()
        self.input_layout = QGridLayout()
        self.button_layout = QHBoxLayout()

        self.min_frequency = _create_input_field(
            self.input_layout, "Minimum Frequency (Hz)", "0.1", "Hz", 0, 0
        )
        self.max_frequency = _create_input_field(
            self.input_layout, "Maximum Frequency (Hz)", "1000.0", "Hz", 0, 1
        )

        self.start_button = QPushButton("Start")
        self.save_data_button = QPushButton("Save Data")
        self.save_plot_button = QPushButton("Save Plot")

        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.save_data_button)
        self.button_layout.addWidget(self.save_plot_button)

        self.figure = Figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)

        self.main_layout.addLayout(self.input_layout, stretch=1)
        self.main_layout.addLayout(self.button_layout, stretch=1)
        self.main_layout.addWidget(self.canvas, stretch=4)

        self.setLayout(self.main_layout)

        self.start_button.clicked.connect(self.start)
        self.save_data_button.clicked.connect(self.save_data)
        self.save_plot_button.clicked.connect(self.save_plot)

        self.freqs = None
        self.magnitude = None
        self.phase = None

    def start(self):
        min_freq = float(self.min_frequency.text().replace(",", "."))
        max_freq = float(self.max_frequency.text().replace(",", "."))
        self.start_signal.emit(min_freq, max_freq)

    def plot_bode(self, freqs: np.ndarray, magnitude: np.ndarray):
        self.freqs = freqs
        self.magnitude = magnitude

        self.figure.clear()
        ax = self.figure.add_subplot(1, 1, 1)
        ax.semilogx(freqs, magnitude)
        ax.set_ylabel("Magnitude (dBm)")
        ax.set_xlabel("Frequency (Hz)")
        ax.grid(True, which="both")

        self.canvas.draw()

    def save_data(self):
        if self.freqs is None or self.magnitude is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "CSV Files (*.csv)")
        if path:
            df = pd.DataFrame({
                "Frequency (Hz)": self.freqs,
                "Magnitude (dBm)": self.magnitude
            })
            df.to_csv(path+".csv", index=False, sep=',')
            # data = np.column_stack((self.freqs, self.magnitude))
            # np.savetxt(path, data, delimiter=",", header="Frequency,Magnitude", comments="")

    def save_plot(self):
        if self.freqs is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Plot", "", "PNG Files (*.png);;All Files (*)")
        if path:
            self.figure.savefig(path, dpi=300, bbox_inches='tight')