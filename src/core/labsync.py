# python
#! /usr/bin/env python3
import os
import sys

# ensure project root is on sys.path so `src` package imports work when running the script directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from src.core.labsync_app import LabSync

def main() -> None:
    app = QApplication(sys.argv)
    cwd = os.path.dirname(os.path.abspath(__file__))
    file_dir = os.path.join(os.path.dirname(cwd), "assets")

    # keep a reference to the LabSync instance so it isn't garbage-collected
    lab = LabSync(app, file_dir)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()