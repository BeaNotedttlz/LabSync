"""
Main window module for the PySide6 LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/frontend/main_window.py
@note:
"""

from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget,
							   QHBoxLayout, QSplitter, QGridLayout,
							   QMessageBox)
from PySide6.QtCore import QEvent, Signal, Slot


class MainWindow(QMainWindow):

	requestClose = Signal()


	def __ini__(self, app):
		super().__init__()

		self.app = app

		# set window title
		self.setWindowTitle("LabSync")

		# create container widget and main layout
		container = QWidget()
		self.main_layout = QHBoxLayout()

		# make splitter for the info panel and tab widget
		splitter = QSplitter(Qt.Horizontal)
		splitter.setHandleWidth(0)
		splitter.setChildrenCollapsible(False)

		# make info panel layout and widget
		info_panel_layout = QGridLayout()
		info_panel_widget = QWidget()
		info_panel_widget.setLayout(info_panel_layout)
		self.info_panel = InfoPanelWidget()
		info_panel_layout.addWidget(self.info_panel, 0, 0)

		# add info panel and tab widget to splitter
		splitter.addWidget(info_panel_widget)
		self.tab_panel = self._setup_tabs()
		splitter.addWidget(self.tab_panel)

		# set splitter parameters to adjust size rations
		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 4)

		# add splitter to main layout and set central widget
		self.main_layout.addWidget(splitter)
		container.setLayout(self.main_layout)
		self.setCentralWidget(container)

	def closeEvent(self, event) -> None:
		"""
		closeEvent handler to manage port closing on application exit.

		:param event: The event at window close.
		:type event: QCloseEvent
		:return: None
		:rtype: None
		"""
		# Make QMessageBox to ask for confirmation
		response = QMessageBox.question(
			self,
			"Close LabSync?",
			"Do you want to close LabSync and close all ports?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No
		)
		if response == QMessageBox.StandardButton.Yes:
			# close ports and application
			self.requestClose.emit()
			event.accept()
		else:
			# ignore event otherwise
			event.ignore()




