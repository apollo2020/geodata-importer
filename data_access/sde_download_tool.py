import arcpy
from sde_download import *


# root_path = r'C:\Users\mangoldd\Desktop\test\city_data'
root_path = arcpy.GetParameterAsText(0)

msg = ("Root Directory: %s" % root_path) 
arcpy.AddMessage(msg)
print(msg)

msg = ("Initializing importer...") 
arcpy.AddMessage(msg)
print(msg)

importer = CityDataImporter(root_path)

msg = ("Staging import geodatabases...") 
arcpy.AddMessage(msg)
print(msg)

importer.stage()

msg = ("Comparing geodatabase schemas...") 
arcpy.AddMessage(msg)
print(msg)

importer.compare()

msg = ("Updating import geodatabases...") 
arcpy.AddMessage(msg)
print(msg)

importer.update()

msg = ("Deleting geometric networks...") 
arcpy.AddMessage(msg)
print(msg)

importer.delete_networks()
