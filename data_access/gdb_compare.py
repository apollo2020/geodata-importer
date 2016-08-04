import os
import time
import arcpy
from xml.dom.minidom import parse

# result class accepts two lists as arguments, creates sets from the lists,
# compares the sets and saves detected differences as instance variables
class Result():

    def __init__(self, base_list=None, test_list=None):
        self.base_set = set(base_list)
        self.test_set = set(test_list)
        self.combined_set = self.get_combined()
        self.common_set = self.get_common()
        self.removed_set = self.get_removed()
        self.added_set = self.get_added()
        self.base_list = list(self.base_set)
        self.test_list = list(self.test_set)
        self.combined_list = list(self.combined_set)
        self.common_list = list(self.common_set)
        self.removed_list = list(self.removed_set)
        self.added_list = list(self.added_set)

    # get all items in base and test sets (union)
    def get_combined(self):
        return self.base_set | self.test_set

    # get items common to both base and test sets (intersection)
    def get_common(self):
        return self.base_set & self.test_set   

    # get items in test_set not in base_set (difference) 
    def get_added(self):
        return self.test_set - self.base_set

    # get items in base_set not in test_set (difference)
    def get_removed(self):
        return self.base_set - self.test_set    

# returns Result instances
class ResultFactory():

    def make_result(self, base_list=None, test_list=None):
        return Result(base_list, test_list)
        
# compares two esri file geodatabases to detect schema changes
class CompareGDB():

    def __init__(self, base_data_path=None, test_data_path=None):
        self.base_data_path = base_data_path
        self.test_data_path = test_data_path
        self.base_xml_path = self.make_xml_workspace_doc(base_data_path)
        self.test_xml_path = self.make_xml_workspace_doc(test_data_path)
        self.base_xml_dom = parse(self.base_xml_path)
        self.test_xml_dom = parse(self.test_xml_path)
        self.result_factory = ResultFactory()

    # removes xml workspace documents created by make_xml_workspace_doc()
    def cleanup(self):
        if os.path.isfile(self.base_xml_path):
            os.remove(self.base_xml_path)
        if os.path.isfile(self.test_xml_path):
            os.remove(self.test_xml_path)

    # create a esri xml workspace document for a workspace
    def make_xml_workspace_doc(self, in_data=None):
        out_dir = os.path.split(in_data)[0]
        out_name = os.path.split(in_data)[-1].split('.')[0]
        out_file = os.path.join(out_dir, out_name) + '.xml'
        export_type = 'SCHEMA_ONLY'
        arcpy.env.overwriteOutput = True
        arcpy.ExportXMLWorkspaceDocument_management(in_data, out_file, export_type)
        arcpy.env.overwriteOutput = False
        return out_file

    # detect changes in domains between base and test databases
    def compare_domains(self):
        base_domain_elems = self.get_domain_elements(self.base_xml_dom)
        base_domain_vals = [(self.get_child_value(elem, 'DomainName'),
                             self.get_child_value(elem, 'FieldType'))
                             for elem in base_domain_elems]
        test_domain_elems = self.get_domain_elements(self.test_xml_dom)
        test_domain_vals = [(self.get_child_value(elem, 'DomainName'),
                             self.get_child_value(elem, 'FieldType'))
                             for elem in test_domain_elems]
        result = self.result_factory.make_result(base_domain_vals, test_domain_vals)
        return result
    
    # detect changes in feature classes between base and test databases
    def compare_feat_classes(self):
        base_feat_class_elems = self.get_feat_class_elements(self.base_xml_dom)
        base_feat_class_names = [(self.get_child_value(elem, 'Name'),
                                  self.get_child_value(elem, 'ShapeType'))
                                 for elem in base_feat_class_elems]
        test_feat_class_elems = self.get_feat_class_elements(self.test_xml_dom)
        test_feat_class_names = [(self.get_child_value(elem, 'Name'),
                                  self.get_child_value(elem, 'ShapeType'))
                                 for elem in test_feat_class_elems]
        result = self.result_factory.make_result(base_feat_class_names, test_feat_class_names)
        return result

    # detect changes in fields for matching feature classes
    def compare_fields(self, base_feat_class_element=None, test_feat_class_element=None):
        base_field_elems = self.get_field_elements(base_feat_class_element)
        base_field_values = [(self.get_child_value(elem, 'Name'),
                             self.get_child_value(elem, 'Type'))
                             for elem in base_field_elems]
        test_field_elems = self.get_field_elements(test_feat_class_element)
        test_field_values = [(self.get_child_value(elem, 'Name'),
                             self.get_child_value(elem, 'Type'))
                             for elem in test_field_elems]
        result = self.result_factory.make_result(base_field_values, test_field_values)
        return result

    # get DOM elements for all domains below input element
    def get_domain_elements(self, xml_dom=None):
        domain_elems = xml_dom.getElementsByTagName('Domain')        
        return domain_elems

    # get DOM elements for all feature classes below input element
    def get_feat_class_elements(self, xml_dom=None):
        data_elems = xml_dom.getElementsByTagName('DataElement')
        feat_class_elems = [elem for elem in data_elems
                            if elem.getAttribute('xsi:type') == 'esri:DEFeatureClass']
        return feat_class_elems

    # get DOM elements for all fields below input element
    def get_field_elements(self, feat_class_element=None):
        field_elems = feat_class_element.getElementsByTagName('Field')
        return field_elems

    # get child node value by name
    def get_child_value(self, element=None, child_name=None):
        child_value = element.getElementsByTagName(child_name)[0].firstChild.nodeValue
        return child_value

    # create text report with results of comparison
    def make_report(self):
        changes = 0
        report_str = "\n"
        report_str += "----- BEGIN REPORT -----\n\n"
        report_str += "WORKSPACE COMPARISON REPORT: "
        report_str += "%s\n\n" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        report_str += "TEST WORKSPACE:\n"
        report_str += "  NAME: %s\n" % (os.path.split(self.test_data_path)[-1])
        report_str += "  PATH: %s\n\n" % (self.test_data_path)
        report_str += "BASE WORKSPACE:\n"
        report_str += "  NAME: %s\n" % (os.path.split(self.base_data_path)[-1])
        report_str += "  PATH: %s\n\n" % (self.base_data_path)

        domain_result = self.compare_domains()
        if len(domain_result.added_list) > 0:
            report_str += "DOMAINS ADDED:\n"
            for domain_vals in domain_result.added_list:
                report_str += "  %s\n" % str(domain_vals)
                changes += 1
            report_str += "\n"
        if len(domain_result.removed_list) > 0:
            report_str += "DOMAINS REMOVED:\n"
            for domain_vals in domain_result.removed_list:
                report_str += "  %s\n" % str(domain_vals)
                changes += 1
            report_str += "\n"
        
        fc_result = self.compare_feat_classes()
        if len(fc_result.added_list) > 0:
            report_str += "CLASSES ADDED:\n"
            for fc_vals in fc_result.added_list:
                report_str += "  %s\n" % str(fc_vals)
                changes += 1
            report_str += "\n"
        if len(fc_result.removed_list) > 0:
            report_str += "CLASSES REMOVED:\n"
            for fc_vals in fc_result.removed_list:
                report_str += "  %s\n" % str(fc_vals)
                changes += 1
            report_str += "\n"
            
        for fc_vals in fc_result.common_list:
            base_feat_class_element = [elem for elem
                                       in self.get_feat_class_elements(self.base_xml_dom)
                                       if (self.get_child_value(elem, 'Name'),
                                          self.get_child_value(elem, 'ShapeType')) == fc_vals][0]
            test_feat_class_element = [elem for elem
                                       in self.get_feat_class_elements(self.test_xml_dom)
                                       if (self.get_child_value(elem, 'Name'),
                                          self.get_child_value(elem, 'ShapeType')) == fc_vals][0]
            fld_result = self.compare_fields(base_feat_class_element, test_feat_class_element)
            if len(fld_result.added_list + fld_result.removed_list) > 0:
                report_str += "CLASS: %s\n" % str(fc_vals)
                if len(fld_result.added_list) > 0:
                    report_str += "  FIELDS ADDED:\n"
                    for fld_vals in fld_result.added_list:
                        report_str += "    %s\n" % str(fld_vals)
                        changes += 1
                    report_str += "\n"
                if len(fld_result.removed_list) > 0:
                    report_str += "  FIELDS REMOVED:\n"
                    for fld_vals in fld_result.removed_list:
                        report_str += "    %s\n" % str(fld_vals)
                        changes += 1
                    report_str += "\n"
        if changes == 0:
            report_str += "NO CHANGES DETECTED.\n\n"
        report_str += "----- END REPORT -----\n"
        return report_str
