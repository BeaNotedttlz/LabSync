from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer
import sys, os
from LabSyncApp import MainWindow
from utils import FilesUtils

if __name__ == "__main__":
	app = QApplication(sys.argv)
	app.setWindowIcon(QIcon(os.path.join("img", "hqe_logo.png")))
	file = FilesUtils()

	settings = file.ensure_hidden_settings()

	window = MainWindow(app, settings["simulate_devices"])

	# Timer for continous calling of functions #
	timer = QTimer()
	timer.timeout.connect(window.loop_calls)
	timer.start(2000)

	# show Main window and execute loop #
	window.show()
	sys.exit(app.exec())
