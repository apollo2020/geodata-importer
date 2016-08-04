import arcpy

# ----- CLASS DEFINITIONS -----


class Transformer():
    """Transform datasets using data interoperability tools."""


    def __init__(self):
        """Set toolbox (.tbx) location and city import tool lookup dictionary."""

        self.tools_path = r'\\fileserv\USA\GIS\CityDataImport\tools\fme\DataInteropLatest.tbx'
        self.tools_dict = {'BEAVERTON':'BeavertonToSimpleSewer_DataInteropLatest',
                           'FORESTGROVE':'ForestGroveToSimpleSewer_DataInteropLatest',
                           'HILLSBORO':'HillsboroToSimpleSewer_DataInteropLatest',
                           'SHERWOOD':'SherwoodToSimpleSewer_DataInteropLatest',
                           'TIGARD':'TigardToSimpleSewer_DataInteropLatest',
                           'TUALATIN':'TualatinToSimpleSewer_DataInteropLatest',
                           'CWS':'CwsToSimpleSewer_DataInteropLatest'}
        self.setup()
        
    def setup(self):
        """configure arcpy to use custom data interoperability tools."""

        print("checking out data interoperability extension...")
        arcpy.CheckOutExtension("DataInteroperability")
        print("importing city transformation tools...")
        arcpy.ImportToolbox(self.tools_path)

    def city_to_simple(self, city_name, source_dataset, dest_dataset):
        """Transform data from city-provided schema to SimpleSewer schema.

        Appropriate tool function name retrieved from class-level lookup dict using city name.

        Parameters source_dataset and dest_dataset are file-geodatabse (.gdb) paths

        Existing dest_dataset with matching name will be overwritten.
        """

        dest_dataset = dest_dataset.replace('.gdb', '')
        toolname = self.tools_dict[city_name.upper()]
        toolfunc = arcpy.__dict__[toolname]
        toolfunc(source_dataset, dest_dataset)
