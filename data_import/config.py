
# --- general import configuration ---

"""
DEFINITIONS

point_match_dist...point match threshold (if multiple features within threshold, nearest feature matches)
line_match_dist....line match threshold (if multiple features within threshold, nearest feature matches)
match_angle........maximum angle difference allowed between matching features
match_attr_name....name of field for attribute matching (case-insensitive for matching purposes)
match_type.........one of 'attr', 'geom', 'comb' (attribute-only, geometry-only, combined: attr AND geom)
shp_attr_token.....ESRI-defined geometry attribute token
oid_attr_token.....ESRI-defined unique table id attribute token (OBJECTID or FID)
sde_prefix.........object name prefix used in target ArcSDE geodatabase
log_dir............location of logs written out by the import tool
"""

gen_config = {
    'point_match_dist': 30.0,
    'line_match_dist': 30.0,
    'match_angle': 45.0,
    'match_attr_name': 'cityid',
    'match_type': 'geom',
    'shp_attr_token': 'SHAPE@',
    'oid_attr_token': 'OID@',
    #  'sde_prefix': '',
    'sde_prefix': 'sde_rm.GIS.',
    'log_dir': 'logs'
    }

# --- edit operation specific import configurations ---

"""
DEFINITIONS

enabled............True: parent operation performed; False: parent operation not performed
order..............order in which operation will be performed (relative to other enabled operations)
results............operation return codes and corresponding messages to log
"""

oper_config = {
    'status': {
        'delete': {
            'enabled': False,
            'order': 1
            },
        'update': {
            'enabled': True,
            'order': 2
            },
        'insert': {
            'enabled': False,
            'order': 3
            }
        },
    'results': {
        0: "  operation aborted and errors logged",
        1: "  operation completed without errors",
        2: "  operation completed and errors logged"
        }
    }

# --- feature class specific import configurations ---

"""
DEFINITIONS

active.............class imported if True otherwise ignored
work_order.........order in which class will be processed within dataset
match_angle........inherited from general configuration
match_dist.........inherited from general configuration for appropriate geometry type(point or line)
match_attr.........inherited from general configuration
match_type.........inherited from general configuration
juris_field........jurisdiction field name (varies among classes)
maint_field........maintainer field name (varies among classes)
operations.........operation-specific configuration attributes
    state..........operation performed if True otherwise skipped
    where_clause...SQL selection WHERE clause applied to target table prior to matching and operation
update_fields......fields modified by update operation ([juris_field, maint_field] appended for insert operation)

"""

class_config = {
    'Sanitary': {  # --- begin sanitary ---
        'GravityMains': {
            'active': True,
            'work_order': 0,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['line_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {  # operation specific configurations
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    },
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"  # applied to tgt reader
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    }
                },
            'update_fields': [
                'CITY_DOWNSTREAM_FACILITY_ID',
                'CITY_PROJECT_NUMBER',
                'CITY_UPSTREAM_FACILITY_ID',
                'CITYID',
                'DateBuilt',
                'DIAMETER',
                'DOWNSTREAM_ELEVATION',
                'DRAWING_SOURCE',
                'GRAVITYTYPE',
                'MATERIAL',
                'RECORDED_LENGTH',
                'REMARKS',
                'SLOPE',
                'UPSTREAM_ELEVATION',
                gen_config['shp_attr_token']
            ]
        },
        'SaniCleanouts': {
            'active': True,
            'work_order': 2,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'Jurisdiction',
            'maint_field': 'FoMaint',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'BottomElevation',
                'CityId',
                'CleanoutDiameter',
                'DateBuilt',
                'Depth',
                'DrawingSource',
                'Material',
                'Remarks',
                'RimElevation'  # ,
                # gen_config['shp_attr_token']
            ]
        },
        'SaniFittings': {
            'active': True,
            'work_order': 3,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'CITY_PROJECT_NUMBER',
                'CITYID',
                'DateBuilt',
                'DRAWING_SOURCE',
                'FITTINGTYPE',
                'REMARKS'  # ,
                # gen_config['shp_attr_token']
            ]
        },
        'SaniManholes': {
            'active': True,
            'work_order': 1,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'CITY_PROJECT_NUMBER',
                'CITYID',
                'DateBuilt',
                'DEPTH',
                'DRAWING_SOURCE',
                'INVERT_ELEVATION',
                'MANHOLE_DIAMETER',
                'MANHOLE_MATERIAL',
                'MANHOLETYPE',
                'REMARKS',
                'RIM_ELEVATION'  # ,
                # gen_config['shp_attr_token']
            ]
        },
        'SaniVaults': {
            'active': True,
            'work_order': 4,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'Jurisdiction',
            'maint_field': 'FoMaint',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'BottomElevation',
                'CityId',
                'DateBuilt',
                'Depth',
                'DrawingSource',
                'Length',
                'Material',
                'Remarks',
                'RimElevation',
                'VaultType',
                'Width'  # ,
                # gen_config['shp_attr_token']
            ]
        }
    },
    'Storm': {  # --- begin storm ---
        'ClosedConveyances': {
            'active': False,
            'work_order': 0,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['line_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {  # --- operation specific configurations
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"  # applied to tgt reader
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'CITY_DOWNSTREAM_FACILITY_ID',
                'CITY_PROJECT_NUMBER',
                'CITY_UPSTREAM_FACILITY_ID',
                'CITYID',
                'CONVEYANCE',
                'DateBuilt',
                'DIAMETER',
                'DOWNSTREAM_ELEVATION',
                'DRAWING_SOURCE',
                'HEIGHT',
                'MATERIAL',
                'RECORDED_LENGTH',
                'REMARKS',
                'SLOPE',
                'UPSTREAM_ELEVATION',
                'WIDTH',
                gen_config['shp_attr_token']
            ]
        },
        'OpenConveyances': {
            'active': False,
            'work_order': 1,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['line_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<jurisfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'CHANNEL_TYPE',
                'CITYID',
                'DateBuilt',
                'DOWNSTREAM_ELEVATION',
                'DRAWING_SOURCE',
                'RECORDED_LENGTH',
                'REMARKS',
                'SLOPE',
                'UPSTREAM_ELEVATION',
                gen_config['shp_attr_token']
            ]
        },
        'StormCleanouts': {
            'active': False,
            'work_order': 7,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'Jurisdiction',
            'maint_field': 'FoMaint',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'BottomElevation',
                'CityId',
                'DateBuilt',
                'Depth',
                'DrawingSource',
                'Material',
                'Remarks',
                'RimElevation'  # ,
                # gen_config['shp_attr_token']
            ]
        },
        'StormFittings': {
            'active': False,
            'work_order': 6,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'CITYID',
                'DateBuilt',
                'DRAWING_SOURCE',
                'FITTINGTYPE',
                'REMARKS'  # ,
                # gen_config['shp_attr_token']
            ]
        },
        'StormInlets': {
            'active': False,
            'work_order': 3,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'Acres_Served',
                'BOTTOM_ELEVATION',
                'CITYID',
                'DateBuilt',
                'DRAWING_SOURCE',
                'Has_Filter',
                'INLETTYPE',
                'MATERIAL',
                'REMARKS',
                'RIM_ELEVATION',
                'SUMP',
                'SUMP_DEPTH',
                'TOTAL_DEPTH',
                'WATER_QUALITY_INDICATOR'  # ,
                # gen_config['shp_attr_token']
            ]
        },
        'StormManholes': {
            'active': False,
            'work_order': 2,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'Acres_Served',
                'BOTTOM_ELEVATION',
                'CITYID',
                'DateBuilt',
                'DRAWING_SOURCE',
                'DROP_TYPE',
                'Has_Filter',
                'MANHOLE_DIAMETER',
                'MANHOLETYPE',
                'MATERIAL',
                'REMARKS',
                'RIM_ELEVATION',
                'SUMP',
                'SUMP_DEPTH',
                'TOTAL_DEPTH',
                'WATER_QUALITY_INDICATOR'  # ,
                # gen_config['shp_attr_token']
            ]
        },
        'StormPondOutlets': {
            'active': False,
            'work_order': 5,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'CITYID',
                'DateBuilt',
                'DRAWING_SOURCE',
                'ELEVATION',
                'OUTLETTYPE'  # ,
                'REMARKS',
                # gen_config['shp_attr_token']
            ]
        },
        'StormPonds': {
            'active': False,
            'work_order': 8,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'JURISDICTION',
            'maint_field': 'FO_MAINT',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'ACRES_SERVED',
                'CITY_NAME',
                'CITYID',
                'DateBuilt',
                'DRAWING_SOURCE',
                'NUMBER_OF_INLETS',
                'NUMBER_OF_OUTLETS',
                'PONDTYPE',
                'REMARKS',
                'Water_Quality_Indicator',
                'Water_Quantity_Indicator'  # ,
                # gen_config['shp_attr_token']
            ]
        },
        'StormVaults': {
            'active': False,
            'work_order': 4,
            'match_angle': gen_config['match_angle'],
            'match_dist': gen_config['point_match_dist'],
            'match_attr': gen_config['match_attr_name'],
            'match_type': gen_config['match_type'],
            'juris_field': 'Jurisdiction',
            'maint_field': 'FoMaint',
            'operations': {
                'update': {
                    'state': True,
                    'where_clause': "NOT <maintfield> IN ('CWS') OR <maintfield> IS NULL"
                    },
                'insert': {
                    'state': True,
                    'where_clause': ""
                    },
                'delete': {
                    'state': True,
                    'where_clause': "<maintfield> IN (<cityname>)"
                    }
                },
            'update_fields': [
                'AcresServed',
                'BottomElevation',
                'CityId',
                'CityName',
                'DateBuilt',
                'DrawingSource',
                'HasFilter',
                'Material',
                'Remarks',
                'RimElevation',
                'Sump',
                'SumpDepth',
                'TotalDepth',
                'VaultType',
                'WaterQualityIndicator',
                'WaterQuantityIndicator'  # ,
                # gen_config['shp_attr_token']
            ]
        }
    }
}
