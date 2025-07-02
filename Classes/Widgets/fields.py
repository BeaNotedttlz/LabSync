from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QComboBox, QLineEdit


def _create_output_field(
		layout,
		name: str,
		init_value: str,
		unit: str,
		row: int,
		column: int) -> QLabel:
	main_label = QLabel(init_value)
	main_label.setAlignment(Qt.AlignRight)
	main_label.setStyleSheet("QLabel{border:2px solid grey;}")
	main_label.setFixedHeight(22)

	secondary_label = QLabel(unit)
	name_label = QLabel(name)

	layout.addWidget(name_label, row, column)
	layout.addWidget(main_label, row + 1, column)
	layout.addWidget(secondary_label, row + 1, column + 1)

	return main_label

def _create_input_field(
		layout,
		name: str,
		init_value: str,
		unit: str,
		row: int,
		column: int) -> QLineEdit:
	main_line = QLineEdit(init_value)
	main_line.setAlignment(Qt.AlignRight)

	unit_label = QLabel(unit)
	name_label = QLabel(name)

	layout.addWidget(name_label, row, column)
	layout.addWidget(main_line, row+1, column)
	layout.addWidget(unit_label, row+1, column+1)

	return main_line

# Function for creating combobox widgets #
def _create_combo_box(
		layout,
		items: list,
		name:str,
		row: int,
		column: int) -> QComboBox:
	combo_box = QComboBox()
	combo_box.addItems(items)

	name_label = QLabel(name)

	layout.addWidget(name_label, row, column)
	layout.addWidget(combo_box, row+1, column)

	return combo_box
