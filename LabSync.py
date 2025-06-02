from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer
import sys
from LabSyncapp import MainWindow

if __name__ == "__main__":
	app = QApplication(sys.argv)
	app.setWindowIcon(QIcon("/img/hqe_logo.png"))

	window = MainWindow(app)

	# Timer for continous calling of functions #
	timer = QTimer()
	timer.timeout.connect(window.loop_functions)
	#timer.start(400)

	# show Main window and execute loop #
	window.show()
	sys.exit(app.exec())
