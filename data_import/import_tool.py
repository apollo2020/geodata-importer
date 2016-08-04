
# --- import modules ---

from tools import *
from config import gen_config, oper_config, class_config

# --- get general configuration import variables ---

shp_attr_token = gen_config['shp_attr_token']
oid_attr_token = gen_config['oid_attr_token']
sde_prefix = gen_config['sde_prefix']
log_dir = gen_config['log_dir']
oper_status = oper_config['status']  # oper_order
oper_results = oper_config['results']  # result_map

# --- get input variables from geoprocessing tool ---

city_name = "'%s'" % arcpy.GetParameterAsText(0)
src_dbpath = arcpy.GetParameterAsText(1)
tgt_dbpath = arcpy.GetParameterAsText(2)

# --- begin import process ---

msg = ("Import City: %s"
       "\nSource Database: %s"
       "\nTarget Database: %s"
       "\nLog Location: %s" %
       (city_name,
        src_dbpath,
        tgt_dbpath,
        log_dir))

arcpy.AddMessage(msg)
print(msg)

# --- build list of classes available for import ---

src_featclasses = []
for dataset in class_config.keys():
    arcpy.env.workspace = os.path.join(src_dbpath, dataset)
    featclasses = arcpy.ListFeatureClasses()
    if featclasses:
        src_featclasses += featclasses

# --- import each available class if 'active' is True in config file ---

for ds_name, class_info in class_config.iteritems():
    work_sort = sorted([(attrs['work_order'], class_name)
                       for class_name, attrs in class_info.iteritems()])
    for work_order, class_name in work_sort:
        config_info = class_info[class_name]
        if class_name in src_featclasses:
            if config_info['active'] is True:
                
                msg = "Importing Class: %s" % class_name
                arcpy.AddMessage(msg)
                print(msg)

                # --- get class-specific configuration import variables ---

                msg = "  Configuring Import Variables"
                arcpy.AddMessage(msg)
                print(msg)
                
                src_classpath = os.path.join(src_dbpath, ds_name, class_name)
                tgt_classpath = os.path.join(tgt_dbpath, sde_prefix + ds_name, sde_prefix + class_name)
                match_angle = config_info['match_angle']
                match_dist = config_info['match_dist']
                grid_size = match_dist * 3.0
                match_attr = config_info['match_attr']
                match_type = config_info['match_type']
                juris_field = config_info['juris_field']
                maint_field = config_info['maint_field']
                update_fields = config_info['update_fields']
                insert_fields = update_fields + [juris_field, maint_field]
                class_operations = config_info['operations']

                # --- update where clauses with class-specific information ---
                
                for oper, attr in class_operations.iteritems():
                    for attr_name, value in attr.iteritems():
                        if attr_name == 'where_clause':
                            class_operations[oper][attr_name] = (
                                value
                                .replace('<cityname>', city_name)
                                .replace('<jurisfield>', juris_field)
                                .replace('<maintfield>', maint_field)
                                )

                # --- read data from source feature class ---

                msg = "  Reading Source Features"
                arcpy.AddMessage(msg)
                print(msg)
                
                src_reader = Reader(src_classpath)
                src_reader.read([oid_attr_token, match_attr, shp_attr_token])

                oper_sort = sorted([(attrs['order'], oper_name)
                                    for oper_name, attrs in oper_config['status'].iteritems()
                                    if attrs['enabled'] is True])
                
                for oper_order, oper_name in oper_sort:

                    if class_operations[oper_name]['state'] is True:

                        # --- read data from target feature class ---

                        msg = "  Reading Target Features"
                        arcpy.AddMessage(msg)
                        print(msg)
                        
                        tgt_reader = Reader(tgt_classpath)
                        tgt_reader.read([oid_attr_token, match_attr, shp_attr_token],
                                        expand_extent(src_reader.extent, grid_size),
                                        class_operations[oper_name]['where_clause'])
                        
                        # --- match source and target records ---

                        msg = "  Matching Features"
                        arcpy.AddMessage(msg)
                        print(msg)
                        matcher = Matcher(src_reader,
                                          tgt_reader,
                                          match_attr,
                                          match_dist,
                                          match_angle,
                                          grid_size)
                        matcher.find_matches()

                        writer = Writer(matcher, tgt_classpath)

                        if oper_name == 'delete':
                            
                            # --- delete unmatched target records ---
                            
                            msg = "  Deleting Target Features"
                            arcpy.AddMessage(msg)
                            print(msg)
                            result = writer.delete(match_type)
                            msg = oper_config['results'][result].upper()
                            arcpy.AddMessage(msg)
                            print(msg)

                        elif oper_name == 'update':
                            
                            # --- update matched target records ---
                            
                            msg = "  Updating Target Features"
                            arcpy.AddMessage(msg)
                            print(msg)
                            result = writer.update(update_fields, match_type)
                            msg = oper_config['results'][result].upper()
                            arcpy.AddMessage(msg)
                            print(msg)

                        elif oper_name == 'insert':
                            
                            # --- insert unmatched source records into target feature class ---
                            
                            msg = "  Inserting Target Features"
                            arcpy.AddMessage(msg)
                            print(msg)
                            result = writer.insert(insert_fields, match_type)
                            msg = oper_config['results'][result].upper()
                            arcpy.AddMessage(msg)
                            print(msg)

                        else:
                            msg = "  Operation %s is not recognized." % oper_name
                            arcpy.AddMessage(msg)
                            print(msg)
                            
                    else:
                        msg = "  Operation %s not enabled in config file." % oper_name
                        arcpy.AddMessage(msg)
                        print(msg)
                
            else:
                msg = "Class '%s' not set to active in config file." % class_name
                arcpy.AddMessage(msg)
                print(msg)
                
        else:
            msg = "Class '%s' not found in source database." % class_name
            arcpy.AddMessage(msg)
            print(msg)
