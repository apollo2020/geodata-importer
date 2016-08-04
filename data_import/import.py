# dev notes:
# GlobalID not supported at arcpy 10.1 - update at upgrade to 10.2
# Reader fields must have OID@ as first item and Shape@ as final item

# --- import modules ---

import os
import sys
import math
import arcpy
import logging
import datetime
import numpy as np
from config import gen_config

# --- get general configuration import variables ---

shp_attr_token = gen_config['shp_attr_token']
oid_attr_token = gen_config['oid_attr_token']
log_dir = gen_config['log_dir']

# --- configure error and message logging ---

logname = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
logpath = os.path.join(log_dir, r'%s.txt' % logname)
logging.basicConfig(filename=logpath, level=logging.DEBUG)

# --- global functions ---

def get_workspace_path(table_path):
    """Return workspace space from full table_path.

    Only works for .mdb, .gdb and .sde databases.
    """

    database_types = ('.mdb', '.gdb', '.sde')
    db_type = [ext for ext in database_types if ext in table_path][0]
    end_pos = table_path.index(db_type) + len(db_type)
    result = table_path[:end_pos]
    return result


def clean_field_name(name):
    """Return name as lower case with underscores and spaces removed."""

    result = (
        name
        .lower()
        .replace("_", "")
        .replace(" ", "")
        )
    return result


def fieldname_to_index(reader, field_name):
    """Return index of input field name in read_field_names (list) attribute if input reader."""
    
    test_names = [clean_field_name(name) for name in reader.field_names_read]
    test_value = clean_field_name(field_name)
    result = test_names.index(test_value)
    return result


def calc_angle(geom):
    """Returns the geometry's direction in degrees.

    Only point and line supported. Points always return zero. Lines return dir from first pnt to last pnt.
    """

    if geom.type == 'point':
        return 0.0
    elif geom.type == 'polyline':
        p1 = geom.firstPoint
        p2 = geom.lastPoint
        x1, y1 = p1.X, p1.Y
        x2, y2 = p2.X, p2.Y
        dx = x2 - x1
        dy = y2 - y1
        rads = math.atan2(-dy, dx) + math.pi/2
        result = rads * 180.0 / math.pi
        return result
    else:
        print("Invalid geometry type. Use point or polyline.")


def calc_dist(point1, point2):
    """Return the cartesian distance between two Point objects."""

    result = ((point2.X - point1.X)**2.0 + (point2.Y - point1.Y)**2.0)**0.5
    return result


def calc_average_dist(geom1, geom2):
    """Return the average cartesian distance between two Geometry objects.

    For points result is point-to-point distance
    For polylines result is average of point-to-point distances between firstPoint, centroid and lastPoint
    """

    if geom1.type == geom2.type:
        if geom1.type == 'point':
            result = geom1.distanceTo(geom2)
        elif geom1.type == 'polyline':
            pnts1 = [geom1.firstPoint, geom1.centroid, geom1.lastPoint]
            pnts2 = [geom2.firstPoint, geom2.centroid, geom2.lastPoint]
            result = np.array([calc_dist(p1, p2) for p1, p2 in zip(pnts1, pnts2)]).sum()/len(pnts1)
        else:
            print("Geometry not of type point or polyline.")
            return
    else:
        print("Input geometry types %s and %s do not match." % (geom1.type, geom2.type))
        return

    return result


def get_nearest_oid(base_rec, comp_recs):
    """Return the OID of the rec in comp_recs that is nearest to base_rec."""

    base_geom = base_rec[-1]
    comp_geom = comp_recs[0][-1]
    near_dist = calc_average_dist(base_geom, comp_geom)
    result = comp_recs[0][0]
    
    for rec in comp_recs:
        comp_geom = rec[-1]
        this_dist = calc_average_dist(base_geom, comp_geom)
        if this_dist < near_dist:
            result = rec[0]
    
    return result


def combine_extents(extents):
    """Return encompassing extent for all extents in input iterable of Extent objects."""

    x_vals = []
    y_vals = []
    for ext in extents:
        x_vals += [ext.XMin, ext.XMax]
        y_vals += [ext.YMin, ext.YMax]
    x_vals.sort()
    y_vals.sort()
    result = arcpy.Extent(x_vals[0], y_vals[0], x_vals[-1], y_vals[-1])
    return result


def expand_extent(extent, distance):
    """Return extent object with bounds extended by distance."""

    x_min = extent.XMin - distance
    y_min = extent.YMin - distance
    x_max = extent.XMax + distance
    y_max = extent.YMax + distance
    result = arcpy.Extent(x_min, y_min, x_max, y_max)
    return result


def validate_value(value):
    """Return value if valid otherwise None.

    Invalid values are: empty_string, 0, 0.0, None"""

    if str(value).strip() not in ("", "0", "0.0", "None"):
        return value
    else:
        return None


# --- global classes ---


class Reader(object):
    """Read records from ESRI feature class."""

    def __init__(self, table_path):
        """Set source table path."""

        self.table_path = table_path
        self.describe = arcpy.Describe(self.table_path)
        self.extent = self.describe.extent
        self.field_names_all = [fld.name for fld in self.describe.fields]
        self.field_name_oid = self.describe.OIDFieldName
        self.field_name_shape = self.describe.shapeFieldName
        self.field_names_read = []
        self.data = []

    def read(self, field_names, extent=None, where_clause=""):
        """Read records from source feature class

        GlobalID field not supported in 10.1, resolved in 10.2.
        """

        logging.info("READING RECORDS: %s" % self.table_path)
        result = []
        with arcpy.da.SearchCursor(self.table_path, field_names, where_clause) as scur:
            if extent and isinstance(extent, arcpy.Extent):
                for row in scur:
                    if extent.contains(row[-1].centroid):
                        result.append(row)
            else:
                for row in scur:
                    result.append(row)
        self.field_names_read = [name for name in field_names]
        self.data = result


class Matcher(object):
    """Match features from base and comparison (comp) reader objects."""

    def __init__(self, src_reader, tgt_reader, match_attr_name="cityid", match_spatial_threshold=25, match_angle=45, grid_size=75):
        """Set base and comparison (comp) readers, build simple spatial indexes, and initialize properties."""

        self.src_reader = src_reader
        self.tgt_reader = tgt_reader
        self.match_attr_name = match_attr_name
        self.match_angle_threshold = match_angle
        self.match_spatial_threshold = match_spatial_threshold
        self.grid_size = grid_size
        self.extent = combine_extents([self.src_reader.extent, self.tgt_reader.extent])
        self.src_spatial_index = self._build_spatial_index(self.src_reader)
        self.src_field_index = self._build_field_index(self.src_reader, self.match_attr_name)
        self.src_oid_index = self._build_field_index(self.src_reader, oid_attr_token)
        self.tgt_spatial_index = self._build_spatial_index(self.tgt_reader)
        self.tgt_field_index = self._build_field_index(self.tgt_reader, self.match_attr_name)
        self.tgt_oid_index = self._build_field_index(self.tgt_reader, oid_attr_token)
        self.attr_matches = {}
        self.geom_matches = {}
        self.comb_matches = {}
        self.unmatched = {}

    def _make_spatial_hash(self, geom):
        """Return spatial hash id based on reader extents and geom centroid."""

        x_bin = int(math.floor((geom.centroid.X - self.extent.XMin) / self.grid_size))
        y_bin = int(math.floor((geom.centroid.Y - self.extent.YMin) / self.grid_size))
        result = x_bin, y_bin
        return result

    def _build_field_index(self, reader, match_attr_name):
        """Return records aggregated by field name at specified index (field_name_index)."""

        result = {}
        field_pos = fieldname_to_index(reader, match_attr_name)
        for rec in reader.data:
            value = rec[field_pos]
            if value in result:
                result[value].append(rec)
            else:
                result[value] = [rec]
        return result

    def _build_spatial_index(self, reader):
        """Populate index_bins with reader records."""

        result = {}
        for rec in reader.data:
            hashid = self._make_spatial_hash(rec[-1])
            if hashid in result:
                result[hashid].append(rec)
            else:
                result[hashid] = [rec]
        return result

    def _find_attr_matches(self):
        """Return records that match on value at field_name_index.

        Result is of form {comp_oid_1:[base_oid_1,...,base_oid_n],...,comp_oid_n:[base_oid_1,...,base_oid_n]}
        """

        result = {}
        src_field_pos = fieldname_to_index(self.src_reader, self.match_attr_name)
        for rec in self.src_reader.data:
            src_oid = rec[0]
            src_value = rec[src_field_pos]
            try:
                matches = self.tgt_field_index[src_value]
            except KeyError:
                matches = []
            result[src_oid] = [m[0] for m in matches]
        return result

    def _find_geom_matches(self,):
        """Return match records with average distance within match_spatial_threshold.

        Result is of form {comp_oid_1:[base_oid_1,...,base_oid_n],...,comp_oid_n:[base_oid_1,...,base_oid_n]}
        """

        result = {}
        for rec in self.src_reader.data:
            tgt_neighbors = []
            src_oid = rec[0]
            src_shape = rec[-1]
            src_hash = self._make_spatial_hash(src_shape)
            x_bin, y_bin = src_hash[0], src_hash[1]
            for x in range(x_bin-1, x_bin+2):
                for y in range(y_bin-1, y_bin+2):
                    try:
                        tgt_neighbors += self.tgt_spatial_index[x, y]
                    except KeyError:
                        pass
            near_neighbors = []
            for tgt_nbr in tgt_neighbors:
                tgt_shape = tgt_nbr[-1]
                average_dist = calc_average_dist(src_shape, tgt_shape)
                angle_diff = abs(calc_angle(src_shape) - calc_angle(tgt_shape))
                if average_dist <= self.match_spatial_threshold and angle_diff <= self.match_angle_threshold:
                    near_neighbors.append((average_dist, tgt_nbr))
            sorted_neighbors = sorted(near_neighbors)
            if len(sorted_neighbors) > 0:
                nearest_neighbor = sorted_neighbors[0][-1]
                tgt_oid = [nearest_neighbor[0]]
            else:
                tgt_oid = []
            result[src_oid] = tgt_oid
        return result

    def _find_comb_matches(self, attr_matches, geom_matches):
        """Return records that match on both attribute and shape."""

        result = {}
        for k in attr_matches.keys():
            attr_oid_set = set(attr_matches[k])
            geom_oid_set = set(geom_matches[k])
            comb_oid_list = list(attr_oid_set & geom_oid_set)
            result[k] = comb_oid_list
        return result

    def _find_unmatched(self, attr_matches, geom_matches):
        """Return dict of comp_reader OIDs that do not match base_reader records on attribute, shape, or either.

        Result is of form {'attr':[1, 2, 3], 'geom':[3, 4, 5], 'comb':[1, 2, 3, 4, 5]}
        """

        logging.info("FINDING UNMATCHED RECORDS")
        unmatched_attr_oids = [k for k in attr_matches.keys() if len(attr_matches[k]) == 0]
        unmatched_geom_oids = [k for k in geom_matches.keys() if len(geom_matches[k]) == 0]
        unmatched_comb_oids = list(set(unmatched_attr_oids) | set(unmatched_geom_oids))
        result = {'attr':unmatched_attr_oids,
                  'geom':unmatched_geom_oids,
                  'comb':unmatched_comb_oids}
        return result

    def find_matches(self):
        """Find matches and populate class properties accordingly."""

        logging.info("FINDING MATCHED RECORDS")
        self.attr_matches = self._find_attr_matches()
        self.geom_matches = self._find_geom_matches()
        self.comb_matches = self._find_comb_matches(self.attr_matches, self.geom_matches)
        self.unmatched = self._find_unmatched(self.attr_matches, self.geom_matches)


class Writer(object):
    """Updates, inserts, and deletes features in target feature class based on Matcher results."""

    def __init__(self, matcher, target_table):
        """Set matcher, target table path."""

        self.matcher = matcher
        self.target_table = target_table
        self.describe = arcpy.Describe(self.target_table)
        self.extent = self.describe.extent
        self.field_names_all = [fld.name for fld in self.describe.fields]
        self.field_name_oid = self.describe.OIDFieldName
        self.field_name_shape = self.describe.shapeFieldName
        self.field_names_write = []
        self.proc_matches = self._process_matches()

    def _process_matches(self):
        """Invert match mapping: {src_oid : [tgt_oid]} --> {tgt_oid : [src_oid]} and keep nearest matches."""

        attr_matches = self.matcher.attr_matches
        attr_matches_swap = {}
        for k, v in attr_matches.iteritems():
            if len(v) > 0:
                if v[0] in attr_matches_swap:
                    attr_matches_swap[v[0]] += [k]
                else:
                    attr_matches_swap[v[0]] = [k]
        for k, v in attr_matches_swap.iteritems():
            if len(v) > 1:
                k_rec = self.matcher.tgt_oid_index[k][0]
                v_recs = [self.matcher.src_oid_index[i][0] for i in v]
                v_keep = get_nearest_oid(k_rec, v_recs)
                attr_matches_swap[k] = [v_keep]

        geom_matches = self.matcher.geom_matches
        geom_matches_swap = {}
        for k, v in geom_matches.iteritems():
            if len(v) > 0:
                if v[0] in geom_matches_swap:
                    geom_matches_swap[v[0]] += [k]
                else:
                    geom_matches_swap[v[0]] = [k]
        for k, v in geom_matches_swap.iteritems():
            if len(v) > 1:
                k_rec = self.matcher.tgt_oid_index[k][0]
                v_recs = [self.matcher.src_oid_index[i][0] for i in v]
                v_keep = get_nearest_oid(k_rec, v_recs)
                geom_matches_swap[k] = [v_keep]

        comb_matches = self.matcher.comb_matches
        comb_matches_swap = {}
        for k, v in comb_matches.iteritems():
            if len(v) > 0:
                if v[0] in comb_matches_swap:
                    comb_matches_swap[v[0]] += [k]
                else:
                    comb_matches_swap[v[0]] = [k]
        for k, v in comb_matches_swap.iteritems():
            if len(v) > 1:
                k_rec = self.matcher.tgt_oid_index[k][0]
                v_recs = [self.matcher.src_oid_index[i][0] for i in v]
                v_keep = get_nearest_oid(k_rec, v_recs)
                comb_matches_swap[k] = [v_keep]
        
        result = {'attr':attr_matches_swap,
                  'geom':geom_matches_swap,
                  'comb':comb_matches_swap}
        
        return result

    def update(self, field_names, match_type):
        """Update rows in target table based on matched features in writer.matcher.

        match_type can be one of 'attr', 'geom', 'comb'.
        GlobalID field not supported in 10.1, resolved in 10.2.
        """

        result = 1
        logging.info("UPDATING RECORDS: %s" % self.target_table)

        tgt_matches = self.proc_matches[match_type]
        tgt_oids_update = tgt_matches.keys()
                
        if len(tgt_oids_update) > 0:
            query = "OBJECTID IN " + str(tuple(tgt_oids_update)).replace(',)', ')')
        else:
            query = "OBJECTID IN (-1)"

        src_reader = self.matcher.src_reader
        src_reader.read([oid_attr_token] + field_names)
        src_reader_dict = {}
        for rec in src_reader.data:
            src_reader_dict[rec[0]] = rec[1:]

        target_workspace = get_workspace_path(self.target_table)

        try:
            # print("--Initializing editor...")
            edit = arcpy.da.Editor(target_workspace)
            # print("--Starting edit session...")
            edit.startEditing(False, True)
            # print("--Initializing update cursor...")
            with arcpy.da.UpdateCursor(self.target_table, [oid_attr_token] + field_names, query) as ucur:
                # print("--Starting edit operation...")
                edit.startOperation()
                # print("--Updating records...")
                for tgt_data in ucur:
                    try:
                        tgt_oid = tgt_data[0]
                        tgt_data = tgt_data[1:]
                        src_oid = tgt_matches[tgt_oid][0]
                        src_data = src_reader_dict[src_oid]
                        src_data_valid = tuple([validate_value(v) for v in src_data])
                        tgt_data_valid = tuple([validate_value(v) for v in tgt_data])
                        if src_data_valid != tgt_data_valid:
                            paired_data = zip(src_data_valid, tgt_data_valid)
                            out_data = tuple([tgt_oid] + [sd if sd is not None else td for sd, td in paired_data])
                            ucur.updateRow(out_data)
                    except (RuntimeError, SystemError) as e:
                        result = 2
                        logging.warning("TARGET OID: %s | %s | %s" % (tgt_oid, sys.exc_info()[0], e))
                edit.stopOperation()
            edit.stopEditing(True)  # save all changes
        except (arcpy.ExecuteError, SystemError) as e:
            result = 0
            edit.stopEditing(False)  # discard all changes
            logging.warning("Unexpected error: %s | %s" % (sys.exc_info()[0], e))
            logging.info("No changes were saved.")

        return result

    def insert(self, field_names, match_type):
        """Insert rows into target table based on unmatched features in Matcher.

        match_type can be one of 'attr', 'geom', 'comb'.
        GlobalID field not supported in 10.1, resolved in 10.2.
        """

        result = 1
        logging.info("INSERTING RECORDS: %s" % self.target_table)

        tgt_matches = self.proc_matches[match_type]
        src_oids_all = self.matcher.src_oid_index.keys()
        src_oids_matched = [v[0] for k, v in tgt_matches.iteritems()]
        src_oids_insert = list(set(src_oids_all) - set(src_oids_matched))
        
        src_reader = self.matcher.src_reader
        src_reader.read([src_reader.field_name_oid] + field_names)
        src_reader_dict = {}
        
        for rec in src_reader.data:
            src_reader_dict[rec[0]] = rec[1:]

        target_workspace = get_workspace_path(self.target_table)

        try:
            edit = arcpy.da.Editor(target_workspace)
            edit.startEditing(False, True)
            with arcpy.da.InsertCursor(self.target_table, field_names) as icur:
                edit.startOperation()
                for src_oid in src_oids_insert:
                    try:
                        src_data = src_reader_dict[src_oid]
                        out_data = tuple([validate_value(v) for v in src_data])
                        icur.insertRow(out_data)
                    except RuntimeError as e:
                        result = 2
                        logging.warning("SOURCE OID: %s | %s | %s" % (src_oid, sys.exc_info()[0], e))
                edit.stopOperation()
            edit.stopEditing(True)
        except (arcpy.ExecuteError, SystemError) as e:
            result = 0
            edit.stopEditing(False)
            logging.warning("Unexpected error: %s | %s" % (sys.exc_info()[0], e))
            logging.info("No changes were saved.")

        return result

    def delete(self, match_type):
        """Delete rows from target table based on unmatched features in Matcher.

        match_type can be one of 'attr', 'geom', 'comb'.
        GlobalID field not supported in 10.1, resolved in 10.2.
        """

        result = 1
        logging.info("DELETING RECORDS: %s" % self.target_table)
        
        tgt_oids_all = self.matcher.tgt_oid_index.keys()
        tgt_oids_matched = self.proc_matches[match_type].keys()
        tgt_oids_delete = list(set(tgt_oids_all) - set(tgt_oids_matched))

        if len(tgt_oids_delete) > 0:
            query = "OBJECTID IN " + str(tuple(tgt_oids_delete)).replace(',)', ')')
        else:
            query = "OBJECTID IN (-1)"

        target_workspace = get_workspace_path(self.target_table)

        try:
            edit = arcpy.da.Editor(target_workspace)
            edit.startEditing(False, True)
            with arcpy.da.UpdateCursor(self.target_table, [oid_attr_token], query) as ucur:
                edit.startOperation()
                for row in ucur:
                    try:
                        tgt_oid = row[0]
                        ucur.deleteRow()
                    except RuntimeError as e:
                        result = 2
                        logging.warning("TARGET OID: %s | %s | %s" % (tgt_oid, sys.exc_info()[0], e))
                edit.stopOperation()
            edit.stopEditing(True)
        except (arcpy.ExecuteError, SystemError) as e:
            result = 0
            edit.stopEditing(False)
            logging.warning("Unexpected error: %s | %s" % (sys.exc_info()[0], e))
            logging.info("No changes were saved.")

        return result
