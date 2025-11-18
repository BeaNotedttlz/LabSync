"""
Module for repeated adding of input fields, output fields and combo boxes
for PySide6 applications
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/frontend/widgets/utilities.py
@note:
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QComboBox, QLineEdit

def create_output_field(
		layout,
		name: str,
		init_value: str,
		unit: str,
		row: int,
		column: int) -> QLabel:
	"""
	create output field with name, initial value and unit.

	:param layout: Layout to place the output field in
	:type layout: QGridLayout
	:param name: Name of the output field
	:type name: str
	:param init_value: Initial value of the output field
	:type init_value: str
	:param unit: Unit if the values.
	:type unit: str
	:param row: Row in the layout
	:type row: int
	:param column: Column in the layout
	:type column: int
	:return: The main label of the output field. Can be used to set new output.
	:rtype: QLabel
	"""
	# create and edit main label
	main_label = QLabel(init_value)
	main_label.setAlignment(Qt.AlignRight)
	main_label.setStyleSheet("QLabel{border:2px solid grey;}")
	main_label.setFixedHeight(22)

	# create unit and name
	secondary_label = QLabel(unit)
	name_label = QLabel(name)

	# add to layout at fixed distances
	layout.addWidget(name_label, row, column)
	layout.addWidget(main_label, row + 1, column)
	layout.addWidget(secondary_label, row + 1, column + 1)

	return main_label

def create_input_field(
		layout,
		name: str,
		init_value: str,
		unit: str,
		row: int,
		column: int) -> QLineEdit:
	"""
	create output field with name, initial value and unit.

	:param layout: Layout to place the output field in
	:type layout: QGridLayout
	:param name: Name of the output field
	:type name: str
	:param init_value: Initial value of the output field
	:type init_value: str
	:param unit: Unit if the values.
	:type unit: str
	:param row: Row in the layout
	:type row: int
	:param column: Column in the layout
	:type column: int
	:return: The main label of the output field. Can be used to retrieve information.
	:rtype: QLineEdit
	"""
	main_line = QLineEdit(init_value)
	main_line.setAlignment(Qt.AlignRight)

	unit_label = QLabel(unit)
	name_label = QLabel(name)

	layout.addWidget(name_label, row, column)
	layout.addWidget(main_line, row+1, column)
	layout.addWidget(unit_label, row+1, column+1)

	return main_line

def create_combo_box(
		layout,
		items: list,
		name:str,
		row: int,
		column: int) -> QComboBox:
	"""
	Create combo box with given items and name.

	:param layout: Layout to place the output field in
	:type layout: QGridLayout
	:param items: Items to add to the combo box.
	:type items: list
	:param name: Name of the combo box
	:type name: str
	:param row: Row in the layout
	:type row: int
	:param column: Column in the layout
	:type column: int
	:return: The combo box to retrieve and set the item.
	:rtype: QComboBox
	"""
	combo_box = QComboBox()
	combo_box.addItems(items)

	name_label = QLabel(name)

	layout.addWidget(name_label, row, column)
	layout.addWidget(combo_box, row+1, column)

	return combo_box