from qgis.core import (
    QgsProject, QgsVectorLayer, QgsField, QgsFeature,
    QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField, QgsProcessingParameterFeatureSink
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QAction
from .needed_schools_dialog import NeededSchoolsDialog

class NeededSchools:
    LAYER_SCHOOLS_INPUT = 'LAYER_SCHOOLS_INPUT'
    LAYER_CITY_INPUT = 'LAYER_CITY_INPUT'
    FIELD_POPULATION = 'FIELD_POPULATION'
    LAYER_OUTPUT = 'LAYER_OUTPUT'
    FIELD_SCHOOLS_REQUIRED = 'FIELD_SCHOOLS_REQUIRED'
    SCHOOL_CAPACITY = 1000  # Define how many people each school serves, e.g., 1000 people per school

    def __init__(self, iface):
        """
        Initializes the plugin with the QGIS interface instance.
        :param iface: The QGIS interface instance
        """
        self.iface = iface
        self.output_layer = None
        self.dialog = NeededSchoolsDialog()

    def name(self):
        return 'needed_schools'

    def displayName(self):
        return 'Calculate Required Schools'

    def initGui(self):
        """
        Initializes the plugin's GUI elements.
        """
        self.action = QAction('Needed Schools', self.iface.mainWindow())
        self.action.triggered.connect(self.run)

        # Add the action to the QGIS interface (e.g., to the Plugins menu)
        self.iface.addPluginToMenu('&Needed Schools', self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        """
        Removes the plugin's GUI elements.
        """
        self.iface.removePluginMenu('&Needed Schools', self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """
        Called when the plugin's action is triggered.
        """
        self.dialog.exec_()

    def initAlgorithm(self, config=None):
        """
        Initializes the algorithm parameters.
        """
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.LAYER_SCHOOLS_INPUT, 'Schools Layer', types=[QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.LAYER_CITY_INPUT, 'City Layer', types=[QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_POPULATION, 'Population Field', parentLayerParameterName=self.LAYER_CITY_INPUT))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.LAYER_OUTPUT, 'Output Layer', type=QgsProcessing.TypeVectorPolygon))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Main processing method where the algorithm logic happens.
        """
        input_schools_layer = self.parameterAsSource(parameters, self.LAYER_SCHOOLS_INPUT, context)
        input_city_layer = self.parameterAsSource(parameters, self.LAYER_CITY_INPUT, context)
        population_field_name = self.parameterAsString(parameters, self.FIELD_POPULATION, context)
        output_layer_name = self.parameterAsSink(parameters, self.LAYER_OUTPUT, context)

        self.calculate_required_schools(input_city_layer, input_schools_layer, population_field_name)

        return {self.LAYER_OUTPUT: output_layer_name}

    def calculate_required_schools(self, city_layer, schools_layer, population_field_name):
        """
        Calculates the required number of schools for each city area based on population.
        """
        required_schools_field_name = self.FIELD_SCHOOLS_REQUIRED
        school_capacity = self.SCHOOL_CAPACITY

        if not city_layer.isEditable():
            city_layer.startEditing()

        if required_schools_field_name not in [field.name() for field in city_layer.fields()]:
            city_layer.dataProvider().addAttributes([QgsField(required_schools_field_name, QVariant.Int)])
            city_layer.updateFields()

        for feature in city_layer.getFeatures():
            feature_id = feature.id()
            population = feature[population_field_name]
            required_schools = population // school_capacity

            city_layer.changeAttributeValue(feature_id, city_layer.fields().indexFromName(required_schools_field_name), required_schools)

        city_layer.commitChanges()
        self.output_layer = city_layer

# Register your plugin
def classFactory(iface):
    return NeededSchools(iface)
