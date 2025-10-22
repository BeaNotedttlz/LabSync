#! /usr/bin/env python

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer
import sys, os
from LabSyncApp import MainWindow


def main() -> None:
	app = QApplication(sys.argv)
	current_file_dir = os.path.dirname(os.path.abspath(__file__))
	file_dir = os.path.join(os.path.dirname(current_file_dir), "files")
	app.setWindowIcon(QIcon(os.path.join(file_dir,"img", "hqe_logo.png")))
	simulate_devices = True

	window = MainWindow(app, simulate_devices, file_dir)

	# Timer for continous calling of functions #
	timer = QTimer()
	timer.timeout.connect(window.loop_calls)
	timer.start(2000)

	# show Main window and execute loop #
	window.show()
	sys.exit(app.exec())

if __name__ == "__main__":
	# run main funcion #
	main()
