print("importing Python packages...")
import os
import arcpy
import time
import gdb_compare
import fme_transform
from tempfile import gettempdir

# ----- CLASS DEFINITIONS -----


class CityDataImporter():

    def __init__(self, root_dir=None):
        
        self.root_dir = root_dir
        self.paths = {}
        self.contents = {}
        self.required_dirs = ['staging',
                              'current',
                              'archive',
                              'reports',
                              'simple',
                              'sdeconn',
                              'import']
        
        self.import_cities = ['BEAVERTON',
                              'CORNELIUS',
                              'FORESTGROVE',
                              'HILLSBORO',
                              'SHERWOOD',
                              'TIGARD',
                              'TUALATIN']
        
        self.setup()

    def setup(self):

        os.chdir(self.root_dir)
        self.config_paths()
        self.make_sdeconn()
        self.update_contents()

    def today(self):
        
        return time.strftime("%Y_%m_%d", time.localtime())

    def config_paths(self):

        paths = {}

        # check local directory structure
        # need_dirs = ['staging', 'current', 'archive', 'reports', 'simple']
        have_dirs = [d for d in os.listdir(self.root_dir) if os.path.isdir(d)]
        make_dirs = list(set(self.required_dirs) - set(have_dirs))

        # make missing directories
        if len(make_dirs) > 0:
            print("creating missing directories...")
            for d in make_dirs:
                os.mkdir(d)

        # make path variables                
        for d in self.required_dirs:
            paths[d] = os.path.join(self.root_dir, d)

        self.paths = paths

        return True

    def make_sdeconn(self):

        self.update_contents()

        # list existing sde connection files
        sde_files = [os.path.join(self.paths['sdeconn'], f)
                     for f in os.listdir(self.paths['sdeconn'])
                     if os.path.splitext(f)[-1] == '.sde']

        # delete existing sde connection files
        if len(sde_files) > 0:
            
            print("deleting old sde connection file(s)...")
            for f in sde_files:
                os.remove(f)

        # new sde connection parameters
        out_conn_path = self.paths['sdeconn']
        out_conn_name = "%s_GISBUG_TEMP.sde" % self.today()
        database_platform = "SQL_SERVER"
        instance = "washsde.co.washington.or.us,5157"
        account_authentication = "DATABASE_AUTH"
        username = "cws"
        password = "cwsgis"
        save_user_pass = "SAVE_USERNAME"
        database = "gisbug"
        schema = "#"
        version_type = "TRANSACTIONAL"
        version = "sde.Default"
        
        # create new sde connection file
        print("creating new sde connection file...")
        
        arcpy.env.overwriteOutput = True
        
        arcpy.CreateDatabaseConnection_management(out_conn_path,
                                                  out_conn_name,
                                                  database_platform,
                                                  instance,
                                                  account_authentication,
                                                  username,
                                                  password,
                                                  save_user_pass,
                                                  database,
                                                  schema,
                                                  version_type,
                                                  version)
        
        arcpy.env.overwriteOutput = False

        return True

    def update_contents(self):

        contents = {}
        for k, v in self.paths.iteritems():
            contents[k] = os.listdir(v)

        self.contents = contents
        return True

    def get_gdb_paths(self, directory=None):

        temp_env = arcpy.env.workspace
        arcpy.env.workspace = directory
        gdb_paths = arcpy.ListWorkspaces("", "FileGDB")
        arcpy.env.workspace = temp_env
        return gdb_paths
        

    def stage(self):

        self.update_contents()

        sde_conn_file = os.path.join(self.paths['sdeconn'], self.contents['sdeconn'][0])        

        arcpy.env.overwriteOutput = False

        staging_gdb_count = len(self.get_gdb_paths(self.paths['staging']))

        if staging_gdb_count > 0:

            # delete existing staging geodatabases
            print("removing old staging data...")
            
            for gdb_path in self.get_gdb_paths(self.paths['staging']):
                arcpy.Delete_management(gdb_path)

        # get list of city sewer dataset names
        arcpy.env.workspace = sde_conn_file
        print("finding city sewer data on server...")
        import_datasets = [ds for ds in arcpy.ListDatasets()
                           if ds.split('.')[1] in self.import_cities
                           and 'sewer' in ds.split('.')[-1].lower()]

        # get list of names for cities with sewer data in gisbug database
        have_cities = list(set([ds_name.split('.')[1] for ds_name in import_datasets]))        

        # make and populate a staging file geodatabase for each available city
        print("copying data from server to staging...")
        
        for city_name in have_cities:
            
            out_gdb_name = "%s_%s" % (self.today(), city_name)
            print("  creating staging geodatabase: %s..." % out_gdb_name)
            arcpy.CreateFileGDB_management(self.paths['staging'], out_gdb_name, "CURRENT")
            city_ds_names = [ds_name for ds_name in import_datasets
                             if city_name in ds_name]
            
            for ds_name in city_ds_names:
                
                out_data = os.path.join(self.paths['staging'],
                                        "%s.gdb" % out_gdb_name,
                                        ds_name.split('.')[-1])
                print("    importing feature dataset: %s..." % ds_name)
                arcpy.Copy_management(ds_name, out_data)
                self.update_contents()
                
        arcpy.env.workspace = self.root_dir

    # compare schemas of staging geodatabases to current geodatabases
    def compare(self):

        self.update_contents()

        arcpy.env.overwriteOutput = False
        
        print("comparing geodatabase schemas...")
        
        for city in self.import_cities:
            
            from_path = None
            to_path = None

            staging_gdb_paths = self.get_gdb_paths(self.paths['staging'])

            current_gdb_paths = self.get_gdb_paths(self.paths['current'])
            
            staging_matches = [gdb_path for gdb_path in staging_gdb_paths
                               if city in gdb_path]
            
            if len(staging_matches) > 0:
                
                from_path = staging_matches[0]
                
            current_matches = [gdb_path for gdb_path in current_gdb_paths
                               if city in gdb_path]
            
            if len(current_matches) > 0:
                
                to_path = current_matches[0]
                
            if from_path and to_path:
                
                print("  comparing geodatabases for: %s" % city)
                comp = gdb_compare.CompareGDB(to_path, from_path)
                report = comp.make_report()
                comp.cleanup()
                print("    writing comparison report...")
                write_path = os.path.join(self.paths['reports'],
                                    "%s_%s_SCHEMA_COMPARISON.txt" % (self.today(), city))
                f = open(write_path, 'w')
                f.write(report)
                f.close()
                
            if to_path and not from_path:
                
                print("  no staging geodatabase for: %s" % city)
                
            if from_path and not to_path:
                
                print("  no current geodatabase for: %s" % city)

    # archive current and simple geodatabases and replace with staged data
    def update(self):

        self.update_contents()

        arcpy.env.overwriteOutput = True

        staged_gdb_count = len(self.get_gdb_paths(self.paths['staging']))

        if staged_gdb_count > 0:

            # move file geodatabases from current directory to archive directory
            print("moving geodatabases from current to archive...")
        
            for gdb_path in self.get_gdb_paths(self.paths['current']):
                gdb_name = os.path.split(gdb_path)[-1]
                print("  moving geodatabase: %s..." % gdb_name)
                arcpy.Copy_management(gdb_path, os.path.join(self.paths['archive'], gdb_name))
                arcpy.Delete_management(gdb_path)            

            # move file geodatabases from staging directory to current directory
            print("moving geodatabases from staging to current...")
          
            for gdb_path in self.get_gdb_paths(self.paths['staging']):
                gdb_name = os.path.split(gdb_path)[-1]
                print("  moving geodatabase: %s..." % gdb_name)
                arcpy.Copy_management(gdb_path, os.path.join(self.paths['current'], gdb_name))
                arcpy.Delete_management(gdb_path)

        else:

            print("No staging geodatabases for update.")

        arcpy.env.overwriteOutput = False

    def delete_networks(self):

        self.update_contents()

        arcpy.env.overwriteOutput = False

        print("searching current geodatabases for geometric networks...")

        for gdb_path in self.get_gdb_paths(self.paths['current']):
            gdb_name = os.path.split(gdb_path)[-1]
            arcpy.env.workspace = gdb_path
            print("  searching geodatabase: %s" % gdb_name)
            for ds in arcpy.ListDatasets():
                arcpy.env.workspace = os.path.join(gdb_path, ds)
                for geom_ds in arcpy.ListDatasets('', 'GeometricNetwork'):
                    print("    deleting geometric network: %s" % geom_ds)
                    arcpy.Delete_management(geom_ds)
                    
        arcpy.env.workspace = self.root_dir


    # MAY NEED MORE WORK IN fme_transform.py
    # works if only transform_to_simple is called
    # if all functions are callled in sequence, data interop tool is not bound to CityDataImporter instance
    def transform_to_simple(self):

        self.update_contents()

        arcpy.env.overwriteOutput = True

        current_gdb_count = len(self.get_gdb_paths(self.paths['current']))

        if current_gdb_count > 0:

            # move file geodatabases from simple directory to archive directory
            print("moving geodatabases from simple to archive...")
        
            for gdb_path in self.get_gdb_paths(self.paths['simple']):
                gdb_name = os.path.split(gdb_path)[-1]
                print("  moving geodatabase: %s..." % gdb_name)
                arcpy.Copy_management(gdb_path, os.path.join(self.paths['archive'], gdb_name))
                arcpy.Delete_management(gdb_path)
                
            trans = fme_transform.Transformer()

            # transform file geodatabases in current directory and write to simple directory
            print("transforming current geodatabases and writing to simple...")

            for gdb_path in self.get_gdb_paths(self.paths['current']):
                gdb_name = os.path.split(gdb_path)[-1]
                gdb_city = os.path.splitext(gdb_name)[0].split('_')[-1]
                simple_gdb_name = "%s_%s_SIMPLE" % (self.today(), gdb_city.upper())
                print("  transforming geodatabase: %s..." % gdb_name)
                trans.city_to_simple(gdb_city, gdb_path,
                                     os.path.join(self.paths['simple'], simple_gdb_name))

        else:

            print("No current geodatabases to transform.")

        arcpy.env.overwriteOutput = False
        

# ----- EXECUTION BLOCK -----

"""
root_dir = r'C:\Users\mangoldd\Desktop\test\city_data'

importer = CityDataImporter(root_dir)
importer.stage()
importer.compare()
importer.update()
importer.delete_networks()
"""
