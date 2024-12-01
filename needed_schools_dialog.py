from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QFont
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling
import psycopg2
from psycopg2 import sql
from .needed_schools_dialog_ui import Ui_neededSchoolsDialog

class NeededSchoolsDialog(QDialog, Ui_neededSchoolsDialog):
    def __init__(self, parent=None):
        """Initialize the QDialog and set up the UI."""
        super().__init__(parent)
        self.setupUi(self)

        # Populate combo boxes with available tables from the database
        self.populate_table_comboboxes()

        # Connect the city layer combo box to update population field combo box
        self.comboBox_cityLayer.currentIndexChanged.connect(self.update_population_fields)

        # Connect the execute button to calculate the required schools
        self.button_execute.clicked.connect(self.determine_needed_schools)

    def connect_to_database(self):
        """Establish a connection to the PostgreSQL database."""
        return psycopg2.connect(database="analysis", user="postgres", password="Munthali56@", host="localhost", port="5432")

    def populate_table_comboboxes(self):
        """Populate the combo boxes with available tables from the database."""
        try:
            connection = self.connect_to_database()
            cursor = connection.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            table_names = [row[0] for row in cursor.fetchall()]

            # Clear existing items in the combo boxes
            self.comboBox_cityLayer.clear()
            self.comboBox_schoolsLayer.clear()

            # Add placeholder text to combo boxes
            self.comboBox_cityLayer.addItem("Select a population layer")
            self.comboBox_schoolsLayer.addItem("Select school (point) layer")

            # Add available table names to each combo box
            self.comboBox_cityLayer.addItems(table_names)
            self.comboBox_schoolsLayer.addItems(table_names)

            cursor.close()
            connection.close()
        except (Exception, psycopg2.DatabaseError) as error:
            self.display_error(f"Error connecting to the database: {error}")

    def update_population_fields(self):
        """Populate the population fields combo box based on the selected population layer."""
        try:
            self.comboBox_populationField.clear()
            self.comboBox_populationField.addItem("Select a population field")

            population_layer_name = self.comboBox_cityLayer.currentText()
            print(f"Selected Population Layer: {population_layer_name}")  # Debug statement

            if population_layer_name != "Select a population layer":
                connection = self.connect_to_database()
                cursor = connection.cursor()
                cursor.execute(sql.SQL("SELECT column_name FROM information_schema.columns WHERE table_name = %s"), [population_layer_name])
                field_names = [row[0] for row in cursor.fetchall()]
                print(f"Available Fields: {field_names}")  # Debug statement
                self.comboBox_populationField.addItems(field_names)

                cursor.close()
                connection.close()
        except (Exception, psycopg2.DatabaseError) as error:
            self.display_error(f"Error retrieving population fields: {error}")

    def determine_needed_schools(self):
        """Calculate the required number of schools based on the population and students per school, and generate a QGIS layer with labels."""
        try:
            population_layer_name = self.comboBox_cityLayer.currentText()
            schools_layer_name = self.comboBox_schoolsLayer.currentText()
            
            if population_layer_name == "Select a population layer" or schools_layer_name == "Select school (point) layer":
                self.display_error("Please select both the population and school (point) layers.")
                return
            
            connection = self.connect_to_database()
            cursor = connection.cursor()
            
            population_field = self.comboBox_populationField.currentText()
            print(f"Selected Population Field: {population_field}")  # Debug statement

            if population_field == "Select a population field":
                self.display_error("Please select a population field.")
                return
            
            max_students_per_school = int(self.lineEdit_peoplePerSchool.text())

            cursor.execute(sql.SQL("SELECT adm3_en, {population_field}, ST_AsText(geom) AS geom FROM {population_layer}").format(
                population_field=sql.Identifier(population_field),
                population_layer=sql.Identifier(population_layer_name)
            ))

            city_features = cursor.fetchall()

            results_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Needed Schools", "memory")
            provider = results_layer.dataProvider()

            provider.addAttributes([
                QgsField("Location_Name", QVariant.String),
                QgsField("Expected_Schools", QVariant.Int),
                QgsField("current_number_of_schools", QVariant.Int),
                QgsField("Schools_that_are_supposed_to_be_built", QVariant.Int),
                QgsField("Label", QVariant.String)
            ])
            results_layer.updateFields()

            features = []

            for feature in city_features:
                area_name = feature[0]
                population = feature[1]
                geom_wkt = feature[2]
                geom = QgsGeometry.fromWkt(geom_wkt)  # Convert WKT to QgsGeometry

                required_schools = round(population / max_students_per_school)
                cursor.execute(sql.SQL("""
                    SELECT COUNT(*) FROM {schools_layer}
                    WHERE ST_Within(ST_Transform(geom, 4326), ST_GeomFromText(%s, 4326))
                """).format(
                    schools_layer=sql.Identifier(schools_layer_name)
                ), [geom_wkt])
                current_number_of_schools = cursor.fetchone()[0]
                schools_that_are_supposed_to_be_built = max(0, round(required_schools - current_number_of_schools))

                label_text = f"{area_name} = {schools_that_are_supposed_to_be_built}"

                feat = QgsFeature()
                feat.setGeometry(geom)
                feat.setAttributes([area_name, required_schools, current_number_of_schools, schools_that_are_supposed_to_be_built, label_text])
                features.append(feat)

            provider.addFeatures(features)

            cursor.close()
            connection.close()

            # Configure labeling
            label_settings = QgsPalLayerSettings()
            label_settings.fieldName = "Label"
            label_settings.placement = QgsPalLayerSettings.AroundPoint
            label_settings.enabled = True

            text_format = QgsTextFormat()
            text_format.setFont(QFont("Arial", 10))
            text_format.setSize(10)
            label_settings.setFormat(text_format)

            results_layer.setLabelsEnabled(True)
            results_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
            results_layer.triggerRepaint()

            QgsProject.instance().addMapLayer(results_layer)
            self.display_info("Required schools calculation completed and results layer with labels added to the QGIS project.")

        except (Exception, psycopg2.DatabaseError) as error:
            self.display_error(f"Error during calculation: {error}")

    def display_error(self, message):
        """Show an error message to the user."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Error", message)

    def display_info(self, message):
        """Show an informational message to the user."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Information", message)
