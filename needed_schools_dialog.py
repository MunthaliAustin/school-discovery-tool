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
        self.comboBox_cityLayer.currentIndexChanged.connect(self.populate_population_fields)

        # Connect the execute button to calculate the required schools
        self.button_execute.clicked.connect(self.calculate_required_schools)

    def populate_layer_comboboxes(self):
        """Populate the combo boxes with available layers."""
        # Retrieve the list of layer names from the current QGIS project
        layer_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]

        # Clear existing items in the combo boxes
        self.comboBox_cityLayer.clear()
        self.comboBox_schoolsLayer.clear()

        # Add placeholder text to combo boxes
        self.comboBox_cityLayer.addItem("Select a city layer")
        self.comboBox_schoolsLayer.addItem("Select schools layer")

        # Add available layer names to each combo box
        self.comboBox_cityLayer.addItems(layer_names)
        self.comboBox_schoolsLayer.addItems(layer_names)

    def populate_population_fields(self):
        """Populate the population fields combo box based on the selected city layer."""
        # Clear the population field combo box
        self.comboBox_populationField.clear()
        self.comboBox_populationField.addItem("Select a population field")

        # Get the selected city layer name
        city_layer_name = self.comboBox_cityLayer.currentText()
        print(f"Selected City Layer: {city_layer_name}")  # Debug statement

        # If a valid city layer is selected, populate the population fields
        if city_layer_name != "Select a city layer":
            city_layer = QgsProject.instance().mapLayersByName(city_layer_name)[0]
            field_names = [field.name() for field in city_layer.fields()]
            print(f"Available Fields: {field_names}")  # Debug statement
            self.comboBox_populationField.addItems(field_names)

    def calculate_required_schools(self):
        """Calculate the required number of schools based on the population and people per school."""
        # Retrieve the selected layers
        city_layer_name = self.comboBox_cityLayer.currentText()
        schools_layer_name = self.comboBox_schoolsLayer.currentText()
        
        # Check if valid layers are selected
        if city_layer_name == "Select a city layer" or schools_layer_name == "Select schools layer":
            self.show_error("Please select both the city and schools layers.")
            return
        
        # Get the city layer and schools layer
        city_layer = QgsProject.instance().mapLayersByName(city_layer_name)[0]
        schools_layer = QgsProject.instance().mapLayersByName(schools_layer_name)[0]

        # Get the population field selected
        population_field = self.comboBox_populationField.currentText()
        print(f"Selected Population Field: {population_field}")  # Debug statement

        if population_field == "Select a population field":
            self.show_error("Please select a population field.")
            return
        
        # Get the number of people per school
        people_per_school = self.spinBox_peoplePerSchool.value()

        # Perform "Count Points in Polygon" to calculate available schools
        count_result = processing.run("native:countpointsinpolygon", {
            'POLYGONS': city_layer,
            'POINTS': schools_layer,
            'FIELD': 'available_schools',  # Name for the count field
            'OUTPUT': 'memory:'  # Temporary output
        })

        # Get the output layer with counted points
        counted_layer = count_result['OUTPUT']

        # Calculate the required number of schools and write to CSV
        csv_filename = os.path.join(os.path.expanduser('~'), 'required_schools.csv')
        with open(csv_filename, 'w', newline='') as csvfile:
            fieldnames = ['Area', 'Required Schools', 'Available Schools', 'Schools to Add']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for feature in counted_layer.getFeatures():
                area_name = feature['ADM3_EN']  # Use the correct field name for area
                population = feature[population_field]
                required_schools = round(population / people_per_school)
                available_schools = round(feature['available_schools'])
                schools_to_add = max(0, round(required_schools - available_schools))
                writer.writerow({'Area': area_name, 'Required Schools': required_schools, 'Available Schools': available_schools, 'Schools to Add': schools_to_add})

        self.show_info(f"Required schools calculation completed. Output saved to {csv_filename}")

    def show_error(self, message):
        """Show error message to the user."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Error", message)

    def show_info(self, message):
        """Show informational message to the user."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Information", message)
