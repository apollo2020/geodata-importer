import arcpy
from gdb_compare import *


base_path = arcpy.GetParameterAsText(0)
test_path = arcpy.GetParameterAsText(1)
report_path = arcpy.GetParameterAsText(2)

msg = ("Base Geodatabase: %s"
       "\nTest Geodatabase: %s"
       "\nReport Location: %s" %
       (base_path,
        test_path,
        report_path))

arcpy.AddMessage(msg)
print(msg)

msg = ("Comparing geodatabases...")
arcpy.AddMessage(msg)
print(msg)

comp = CompareGDB(base_path, test_path)

msg = ("Creating report...")
arcpy.AddMessage(msg)
print(msg)

report = comp.make_report()

msg = ("Writing report...")
arcpy.AddMessage(msg)
print(msg)

f = open(report_path, 'w')
f.write(report)
f.close()

msg = ("Cleaning up...")
arcpy.AddMessage(msg)
print(msg)

comp.cleanup()
