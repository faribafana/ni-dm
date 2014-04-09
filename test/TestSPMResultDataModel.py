#!/usr/bin/env python
'''Testing of NI-DM data model by comparing the prov file (converted to json) generated by SPM and the expected prov file (manually generated) for a set of experiments

@author: Camille Maumet <c.m.j.maumet@warwick.ac.uk>, Satrajit Ghosh
@copyright: University of Warwick 2014
'''
import unittest
from prov.model import ProvBundle, ProvRecord, ProvExceptionCannotUnifyAttribute, graph, ProvEntity
import prov.model.graph
import os
from subprocess import call
import re
import rdflib
from rdflib.graph import ReadOnlyGraphAggregate, RDF
from rdflib.plugins.memory import IOMemory
from rdflib import Namespace, Literal, URIRef
from rdflib.graph import Graph, ConjunctiveGraph, BNode
from rdflib.plugins.memory import IOMemory

import logging

logger = logging.getLogger(__name__)

class TestSPMResultsDataModel(unittest.TestCase):

    def compare_query_results_all_attributes(self, res, res_other):
        print res.bindings[0].items()


    def compare_query_results(self, res, res_other, info_str=""):
        if not res.bindings:
            self.my_execption = info_str+""": Empty query results"""
        for idx, row in enumerate(res.bindings):
            rowfmt = []
            # FIXME: Deal with more than 1 item
            print "Item %d" % idx
            for key, val in sorted(row.items()):
                found_other = False
                for idx_other, row_other in enumerate(res_other.bindings):
                    if not found_other:
                        # FIXME: Probably not the most efficient way to look for corresponding value
                        for key_other, val_other in sorted(row_other.items()):
                            if key_other == key:
                                found_other = True
                                break
                if not found_other:
                    self.my_execption = self.my_execption + """
                        """+info_str+""": Value of """+key+""" not found"""
                elif not val_other == val:
                    self.my_execption = self.my_execption + """
                        """+info_str+""": Value of """+key+""" should be """+val+""" ("""+val_other+""" instead)"""

    def print_results(self, res):
        for idx, row in enumerate(res.bindings):
            rowfmt = []
            print "Item %d" % idx
            for key, val in sorted(row.items()):
                print type(val)
                print val.decode()
                rowfmt.append('%s-->%s' % (key, val.decode()))
            print '\n'.join(rowfmt)

    def setUp(self):
        self.seq = range(10)
        self.my_execption = ""
        # Display log messages
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def compare_full_graphs(self, gt_ttl_file, other_ttl_file):
        gt = Graph()
        gt.parse(gt_ttl_file, format='turtle')

        spmexport = Graph()
        spmexport.parse(other_ttl_file, format='turtle')

        # Check for predicates which are not in common to both graphs (XOR)
        diff_graph = gt ^ spmexport

        # FIXME: There is probably something better than using os.path.basename to remove namespaces
        exlude_s = list()
        missing_s = list()

        exc_wrong = ""
        exc_added = ""
        exc_missing = ""

        for s,p,o in diff_graph.triples( (None,  None, None) ):
            # If triple is found in spmexport
            if (s,  p, o) in spmexport:
                # If subject and predicate found in gt
                if (s,  p, None) in gt:
                    gt_possible_value = ""
                    for (s_gt,  p_gt, o_gt) in gt.triples((s,  p, None)):
                        gt_possible_value += "; "+os.path.basename(o_gt)
                    exc_wrong += """
    Wrong:   '%s' \ton '%s' \tis '%s' (instead of '%s')"""%(os.path.basename(p),spmexport.label(s),os.path.basename(o),gt_possible_value[2:])
                # If subject found in gt
                elif (s,  None, None) in gt:
                    gt_possible_value = ""
                    for (s_gt,  p_gt, o_gt) in gt.triples((s,  p, None)):
                        gt_possible_value += "; "+os.path.basename(p_gt)
                    exc_added += """
    Added:   '%s' \ton '%s' (instead of '%s')"""%(os.path.basename(p),spmexport.label(s),gt_possible_value[2:])
                # If subject is *not* found in gt
                else:
                    if not s in exlude_s:
                        exc_added += """
    Added:   '%s' """%(s)
                        exlude_s.append(s)
            # If subject and predicate are found in spmexport only and subject is found in gt
            elif (s,  p, o) in gt:
                if (s,  p, None) in spmexport:
                    # Do nothing as already taken into account before
                    a = 1
                # If subject found in gt
                elif (s,  None, None) in spmexport:
                    spmexport_possible_value = ""
                    for (s_export,  p_export, o_export) in spmexport.triples((s,  p, None)):
                        spmexport_possible_value += "; "+os.path.basename(p_export)
                        if ""+os.path.basename(p_export) == ""+os.path.basename(p):
                            print "----> FOUND"
                    exc_missing += """
    Missing:   '%s' \ton '%s' (instead of '%s')"""%(os.path.basename(p),gt.label(s),spmexport_possible_value[2:])
                # If subject is *not* found in gt
                else:
                    if not s in missing_s:
                        exc_missing += """
    Missing:   '%s' """%(s)
                        missing_s.append(s)

        self.my_execption += exc_wrong+exc_added+exc_missing
    #             for (s_ex,  p_ex, o_ex) in spmexport.triples((s,  p, None)):
    #                 self.my_execption += """
    # Added:   '%s' \ton '%s' \t(value: '%s')"""%(os.path.basename(p_ex), s_ex, os.path.basename(o_ex))
    #         elif (s,  p, None) in gt:
    #             for (s_gt,  p_gt, o_gt) in spmexport.triples((s,  p, None)):
    #                 self.my_execption += """
    # Missing: '%s' \ton '%s' \t(instead of '%s')"""%(os.path.basename(p_gt), gt.label(s_gt), os.path.basename(o_gt))
    #         else:
    #             self.my_execption += """
    # Could not determine issue in: '%s' \ton '%s' \t('%s')"""%(os.path.basename(p), gt.label(s), os.path.basename(o))


    '''Test01: Analysis of single-subject auditory data based on test01_spm_batch.m using SPM12b r5918 
    '''
    def test_ex1_auditory_singlesub(self):
        # FIXME: Is this the right thing to do to get the test directory?
        test_dir = os.path.dirname(os.path.realpath('TestSPMResultsDataModel.py'))

        # ground_truth_json = os.path.join(test_dir, 'spm', 'GroundTruth', 'test01', 'test01_spm_results.json');
        ground_truth_ttl = os.path.join(test_dir, 'spm', 'GroundTruth', 'test01', 'test01_spm_results.ttl');
        # spm_export_json = os.path.join(test_dir, 'spm', 'SPMexport', 'test01', 'spm_nidm.json');
        spm_export_ttl = os.path.join(test_dir, 'spm', 'SPMexport', 'test01', 'spm_nidm.ttl');

        self.compare_full_graphs(ground_truth_ttl, spm_export_ttl)

        # add_graph = spmexport - gt
        # for s,p,o in add_graph.triples( (None,  None, None) ):
        #     print "Additional: (%s, %s, %s)"%(os.path.basename(s),p,o)

        # print "gt:"
        # print gt

        # prefixInfo = """
        # prefix prov: <http://www.w3.org/ns/prov#>
        # prefix spm: <http://www.fil.ion.ucl.ac.uk/spm/ns/#>
        # prefix nidm: <http://nidm.nidash.org/>
        # """
        
        # # FIXME: Check how this work with more than 1 contrast
        # # FIXME comparison of sha and coordinateSpace

        # # Assume that we have a single `Model fitting` entity per model 

        # # # Check outputs of `Model fitting`
        # # query = prefixInfo+"""
        # # SELECT ?outid ?outtype WHERE {
        # #  ?mfid a spm:estimation .
        # #  ?outid a ?outtype ;
        # #         prov:wasGeneratedBy ?mfid .
        # # }
        # # """
        # # self.compare_query_results(gt.query(query), spmexport.query(query), 'residualMeanSquaresMap: ')

        # # query = prefixInfo+"""
        # # SELECT ?mfid ?rpvid WHERE {
        # #  ?mfid a spm:estimation .
        # #  ?rpvid a spm:reselsPerVoxelMap ;
        # #         prov:wasGeneratedBy ?mfid .
        # # }
        # # """
        # # self.compare_query_results(gt.query(query), spmexport.query(query), 'reselsPerVoxelMap: ')

        # # # Check that contrastMap, contrastStandardErrorMap and statisticalMap are the same
        # # query = prefixInfo+"""
        # # SELECT ?cfile ?clabel ?cfilename ?ccontrastname ?csfile ?ssfile ?slabel ?sfilename ?sdof ?sstattype ?seffectdof ?scontrastname WHERE {
        # #  ?aid a spm:contrast .
        # #  ?cid a nidm:contrastMap ;
        # #         prov:wasGeneratedBy ?aid ;
        # #         prov:atLocation ?cfile ;
        # #         rdfs:label ?clabel ;
        # #         nidm:fileName ?cfilename ;
        # #         nidm:contrastName ?ccontrastname .
        # #  ?csid a nidm:contrastStandardErrorMap ;
        # #         prov:wasGeneratedBy ?aid ;
        # #         prov:atLocation ?csfile .
        # #  ?sid a nidm:statisticalMap ;
        # #         prov:wasGeneratedBy ?aid ;
        # #         prov:atLocation ?ssfile ;
        # #         rdfs:label ?slabel ;
        # #         nidm:fileName ?sfilename ;
        # #         nidm:errorDegreesOfFreedom ?sdof ;
        # #         nidm:statisticType ?sstattype ;
        # #         nidm:effectDegreesOfFreedom ?seffectdof ;
        # #         nidm:contrastName ?scontrastname .
        # # }
        # # """

        # # # self.compare_query_results(gt.query(query), spmexport.query(query))

        # # # Compare all attributes of contrastMap
        # # query = prefixInfo+"""
        # # SELECT ?attname ?attvalue WHERE {
        # #  ?cid a nidm:contrastMap ;
        # #         ?attname ?attvalue .
        # # }
        # # """
        # # self.compare_query_results_all_attributes(gt.query(query), spmexport.query(query))
 

        # # gt.parse(StringIO(test_graph_b), format="n3")
        # unionGraph = ReadOnlyGraphAggregate(graphs=[gt,spmexport])
        # print unionGraph.quads()

        # # unionGraph = ReadOnlyGraphAggregate([gt, spmexport])
        # # uniqueGraphNames = set(
        # #     [graph.identifier for s, p, o, graph in unionGraph.quads(
        # #         (None, RDF.predicate, None))])
        # # print gt
        # for s, p, o, graph in unionGraph.quads((None, RDF.predicate, None)):
        #     print "graph id="
        #     print graph.identifier


        #        # self.print_results(gt.query(query))
        if self.my_execption:
            raise Exception(self.my_execption)

        # # file = open(ground_truth_json, 'r')
        # # ground_truth_prov = ProvBundle.from_provjson(file.read())

        # # file = open(spm_export_json, 'r')
        # # spm_export_prov = ProvBundle.from_provjson(file.read())


        # # # Compare record by record to know where the problem is if there is one...
        # # ground_truth_records = ground_truth_prov.get_records()
        # # struct_comparison = ''
        # # values_comparison = ''

        # # for gt_record in ground_truth_records:           
        # #     gt_record_id = gt_record.get_identifier()
        # #     if gt_record_id:

        # #         # Find record in SPM export that correspond to the ground truth export
        # #         se_record = spm_export_prov.get_record(gt_record_id)

        # #         if se_record is None:

        # #             struct_comparison = struct_comparison+'Comparison failed: Record '+str(gt_record_id)+' is missing\n'
        # #         else:
        # #             # Comparing attributes 1 by 1
        # #             ground_truth_attributes = gt_record.get_attributes()
                    
        # #             if ground_truth_attributes is not None:
        # #                 for gt_attribute in ground_truth_attributes[1:]:
        # #                     if gt_attribute is not None:
        # #                         # logger.debug("gt_attribute:")
        # #                         # logger.debug(gt_attribute)
        # #                         for name, value in gt_attribute:
        # #                             if not se_record.get_attribute(name):
        # #                                 struct_comparison = struct_comparison+'Comparison failed: Attribute %s of %s is missing.\n' % (name,gt_record.get_identifier())
        # #                             else:
        # #                                 # Check attribute values
        # #                                 if not value == se_record.get_attribute(name)[0]:
        # #                                     # FIXME: Convert to numeric values to be able to check given a certain precision
        # #                                     # FIXME: Deal with repeated attributes (ex prov:type)
        # #                                     values_comparison = values_comparison+'Comparison failed: Attribute %s of %s has a wrong value (%s instead of %s)\n' % (name,gt_record.get_identifier(),se_record.get_attribute(name)[0],value)
        # #             # self.assertEqual(gt_record, se_record)#, 'Compa failed:  %s.' % str(gt_record.get_identifier()))
            
        # # # Compare relations
        # # ground_truth_relations = [record for record in ground_truth_records if record is not None and record.is_relation()]
        # # spm_export_relations = [record for record in spm_export_prov.get_records() if record is not None and record.is_relation()]
        
        # # # FIXME: This comes from the prov toolbox. Maybe we could instead modify the core prov code to return a detailed comparison message? (right now we will only get True or False and a single error message when comparing using ==). This would allow to use self.assertEqual instead.
        # # for record_a in ground_truth_relations:
        # #     found = False

        # #     for record_b in spm_export_relations:
        # #         if record_a == record_b:
        # #             spm_export_relations.remove(record_b)
        # #             found = True
        # #             break
        # #     if not found:
        # #         struct_comparison = struct_comparison+"Comparison failed: Relation %s is missing. \n" % unicode(record_a)
                
        # # if struct_comparison+values_comparison:
        # #     raise Exception(struct_comparison+'\n\n'+values_comparison)

        # # # If we had no error until now check using equality that manual and exported version are indeed equal
        # # self.assertEqual(g, spm_export_prov, 'Comparison failed:  %s.' % groundTruthFile)

if __name__ == '__main__':
    unittest.main()
