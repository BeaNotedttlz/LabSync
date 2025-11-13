#! /usr/bin/env python

"""
Main module for LabSync application.
@author: Merlin Schmidt
@date: 2024-06-10
@file: LabSync.py
@note: Use at your own risk.
"""

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer
import sys, os
from LabSyncApp import MainWindow
from utils import FilesUtils


def main() -> None:
	"""
	Starts the LabSync application.

	:return: None
	"""

	# create application and define file paths
	app = QApplication(sys.argv)
	current_file_dir = os.path.dirname(os.path.abspath(__file__))
	file_dir = os.path.join(os.path.dirname(current_file_dir), "files")
	# Set window icon
	app.setWindowIcon(QIcon(os.path.join(file_dir,"img", "hqe_logo.png")))

	# Create file utility object and get debug mode settings
	file_util = FilesUtils(file_dir)
	simulate = file_util.read_settings("debug_mode")

	# If debug mode is activated, ask user if they want to deactivate it
	if simulate:
		resp = QMessageBox.information(
			None,
			"Debug Mode",
			"Debug Mode is activated! Deactivate?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No
		)
		if resp == QMessageBox.StandardButton.Yes:
			simulate = False
			file_util.edit_settings("debug_mode", simulate)
		else:
			pass

	# Create main window
	window = MainWindow(app, file_util, file_dir, _simulate=simulate)

	# Timer for continuous calling of functions
	timer = QTimer()
	timer.timeout.connect(window.loop_calls)
	timer.start(2000)

	# show Main window and execute loop #
	window.show()
	sys.exit(app.exec())

if __name__ == "__main__":
	# run main function #
	main()
