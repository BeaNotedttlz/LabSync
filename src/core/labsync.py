# python
#! /usr/bin/env python3
import os
import sys

# ensure project root is on sys.path so `src` package imports work when running the script directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
	sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.core.labsync_app import LabSync

def main() -> None:
	app = QApplication(sys.argv)
	cwd = os.path.dirname(os.path.abspath(__file__))
	file_dir = os.path.join(os.path.dirname(os.path.dirname(cwd)), "assets")

	icon_path = os.path.join(file_dir, "hqe_logo.png.png")
	if os.path.exists(icon_path):
		app.setWindowIcon(QIcon(icon_path))

	# keep a reference to the LabSync instance so it isn't garbage-collected
	# This will break the threads and finally the entire application
	app.lab_sync = LabSync(app, file_dir)

	sys.exit(app.exec())

if __name__ == "__main__":
	main()