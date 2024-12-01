from PyQt5.QtWidgets import QDialog
from .needed_schools_dialog_ui import Ui_neededSchoolsDialog
from qgis.core import QgsProject
from qgis import processing
import csv
import os

class NeededSchoolsDialog(QDialog, Ui_neededSchoolsDialog):
    def __init__(self, parent=None):
        """Initialize the QDialog and set up the UI."""
        super().__init__(parent)
        self.setupUi(self)

        # Populate combo boxes with available layers
        self.populate_layer_comboboxes()

        # Connect the city layer combo box to update population field combo box
        self.comboBox_cityLayer.currentIndexChanged.connect(self.update_population_fields)

        # Connect the execute button to calculate the required schools
        self.button_execute.clicked.connect(self.compute_needed_schools)

    def populate_layer_comboboxes(self):
        """Populate the combo boxes with available layers."""
        # Retrieve the list of layer names from the current QGIS project
        layers_list = [layer.name() for layer in QgsProject.instance().mapLayers().values()]

        # Clear existing items in the combo boxes
        self.comboBox_cityLayer.clear()
        self.comboBox_schoolsLayer.clear()

        # Add placeholder text to combo boxes
        self.comboBox_cityLayer.addItem("Choose a city layer")
        self.comboBox_schoolsLayer.addItem("Choose schools layer")

        # Add available layer names to each combo box
        self.comboBox_cityLayer.addItems(layers_list)
        self.comboBox_schoolsLayer.addItems(layers_list)

    def update_population_fields(self):
        """Populate the population fields combo box based on the selected city layer."""
        # Clear the population field combo box
        self.comboBox_populationField.clear()
        self.comboBox_populationField.addItem("Choose a population field")

        # Get the selected city layer name
        selected_city_layer = self.comboBox_cityLayer.currentText()
        print(f"Chosen City Layer: {selected_city_layer}")  # Debug statement

        # If a valid city layer is selected, populate the population fields
        if selected_city_layer != "Choose a city layer":
            city_layer = QgsProject.instance().mapLayersByName(selected_city_layer)[0]
            population_fields = [field.name() for field in city_layer.fields()]
            print(f"Population Fields: {population_fields}")  # Debug statement
            self.comboBox_populationField.addItems(population_fields)

    def compute_needed_schools(self):
        """Calculate the needed number of schools based on the population and people per school."""
        # Retrieve the selected layers
        selected_city_layer = self.comboBox_cityLayer.currentText()
        selected_schools_layer = self.comboBox_schoolsLayer.currentText()

        # Check if valid layers are selected
        if selected_city_layer == "Choose a city layer" or selected_schools_layer == "Choose schools layer":
            self.display_error("Please choose both the city and schools layers.")
            return

        # Get the city layer and schools layer
        city_layer = QgsProject.instance().mapLayersByName(selected_city_layer)[0]
        schools_layer = QgsProject.instance().mapLayersByName(selected_schools_layer)[0]

        # Get the population field selected
        selected_population_field = self.comboBox_populationField.currentText()
        print(f"Chosen Population Field: {selected_population_field}")  # Debug statement

        if selected_population_field == "Choose a population field":
            self.display_error("Please choose a population field.")
            return

        # Get the number of people per school
        people_per_school_value = int(self.lineEdit_peoplePerSchool.text())

        # Perform "Count Points in Polygon" to calculate available schools
        count_result = processing.run("native:countpointsinpolygon", {
            'POLYGONS': city_layer,
            'POINTS': schools_layer,
            'FIELD': 'available_schools',  # Name for the count field
            'OUTPUT': 'memory:'  # Temporary output
        })

        # Get the output layer with counted points
        counted_points_layer = count_result['OUTPUT']

        # Calculate the needed number of schools and write to CSV
        csv_output_filename = os.path.join(os.path.expanduser('~'), 'schools_needed.csv')
        with open(csv_output_filename, 'w', newline='') as csvfile:
            fieldnames = ['Region', 'Schools Needed', 'Current Schools', 'Additional Schools']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for feature in counted_points_layer.getFeatures():
                region_name = feature['ADM3_EN']  # Use the correct field name for area
                population_count = feature[selected_population_field]
                schools_needed = round(population_count / people_per_school_value)
                current_schools = round(feature['available_schools'])
                additional_schools = max(0, round(schools_needed - current_schools))
                writer.writerow({'Region': region_name, 'Schools Needed': schools_needed, 'Current Schools': current_schools, 'Additional Schools': additional_schools})

        self.display_info(f"Needed schools calculation completed. Output saved to {csv_output_filename}")

    def display_error(self, message):
        """Show error message to the user."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Error", message)

    def display_info(self, message):
        """Show informational message to the user."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Information", message)
