#!/usr/bin/env python

"""
TEST CASE DESCRIPTION:

Check that there is a Storage Group on the SAN corresponding to each node in the model

Check that the host initiators as per model are registered in the storage group

This test should be able to be run in KGB+N and maintrack testing loops.

Checks:
1) Storage Group for node is created
2) Each wwn defined in the model is registered to correct port for correct storage group
"""

from infra_utils.san_test import SanTest
from ptaf.utils.litp_cmd_utils import LitpUtils
from ptaf.utils.litp_utils.api_client import LitpClient
from infra_utils.utils.enm_helpers import Model
from ptaf.utils.dmt_utils import DMTUtils

from ptaf.utils.model_utils import ModelUtils

class TestCase(SanTest):

    """
    Test case to verify that there is a Storage Group on the SAN corresponding to each node in the model and
    Check that the host initiators as per model are registered in the storage group
    http://taftm.lmera.ericsson.se/#tm/viewTC/7386/version/1
    """

    def setUp(self):
        """
        Set up the test case
        """
        super(TestCase, self).setUp()

        self.litp_utils = LitpUtils()
        self.model_utils = ModelUtils()
        self.navi_target = self.mws
        #self.dmt_utils = DMTUtils()

    def tearDown(self):
        """
        Clean up after the test case
        """
        super(TestCase, self).tearDown()

    def test(self):
        """
        Test case implementation
        """
        # GET LITP Model INFORMATION
        litp_pass = self.litp_utils.get_litpadmin_password(self)
        client = LitpClient(host=self.mws['ip'],password=litp_pass)
        model = Model(client)

        # get site ID and pool name for deployment from SED, either could be
        # the first part of SG name
        site_id = self.san.get('siteId')
        pool_name = self.san.get('pool')

        # List of LUNs for which possible Storage group names already
        # obtained
        checked_luns=[]

        # Iterate through each node
        for node_id in model.nodes.keys():
            node_sgs = {}
            node_wwns = []
            node = model.nodes[node_id]

            # Get WWNs for each node
            for controller_id in node.controllers.keys():
                for prop in  [ "hba_porta_wwn", "hba_portb_wwn" ]:
                    try:
                        wwn = str(node.controllers[controller_id].properties[prop])
                        node_wwns.append(wwn.upper())
                    except KeyError:
                        pass

            # Iterate through each node's LUN
            for lun_name in node.luns.keys():
                lun = node.luns[lun_name]
                # get the two possible storage groups
                site_id_sg = self.model_utils.get_sg_name_from_lun_item(lun, site_id)
                pool_name_sg = self.model_utils.get_sg_name_from_lun_item(lun, pool_name)
                # if the lun name not in check luns, add that lun name as a key in the dict
                # with both possible storage groups in a list as the item
                if lun_name not in checked_luns:
                    node_sgs[lun_name] = [site_id_sg, pool_name_sg]
                    checked_luns.append(lun_name)

            # Iterate through each Storage group in the model
            for lun_name in node_sgs.keys():
                # call navisec to check that the storage group exists on the SAN
                possible_sgs = node_sgs[lun_name]
                site_id_sg = possible_sgs[0]
                pool_name_sg = possible_sgs[1]

                # one of these possible SGS should exist
                found_site_id_sg = self.navi_get_sg(site_id_sg)
                found_pool_name_sg = self.navi_get_sg(pool_name_sg)
                # if both don't exist, error
                if found_site_id_sg == {} and found_pool_name_sg == {}:
                    self._logger.error("Neither storage group " +\
                      "'{0}' nor '{1}' exist on the SAN for node '{2}'".format(
                      found_site_id_sg, found_pool_name_sg, node))
                else:
                    # set the model sg as whichever one was a real sg
                    if found_site_id_sg != {}:
                        san_sg = found_site_id_sg
                        model_sg = site_id_sg
                    else:
                        san_sg = found_pool_name_sg
                        model_sg = pool_name_sg
                #Assert model SG equals what was returned by the navi call
                self.assertEqual(san_sg['Storage Group Name'], model_sg)

                #Get WWNs from the SAN
                wwn_list = []
                for hba in san_sg['HBA UID']:
                    wwn = hba[0]
                    wwn1 = str(wwn[:len(wwn)/2])
                    wwn2 = str(wwn[(len(wwn)/2)+1:])
                    wwn_list.append(wwn1)
                    wwn_list.append(wwn2)

                # Check that at least 1 wwn exists in SG
                wwn_exists=False
                for wwn in node_wwns:
                    if wwn in wwn_list:
                        wwn_exists=True
                        self.info("WWN %s exists on SAN for node %s: True" % (wwn, node))
                    else:
                        self.info("WWN %s exists on SAN for node %s: False" % (wwn, node))
                self.assertEqual(wwn_exists, True)
                san_sg=None

        self.info("Test Completed Successfully")

if __name__ == '__main__':
    TestCase().run_test()
