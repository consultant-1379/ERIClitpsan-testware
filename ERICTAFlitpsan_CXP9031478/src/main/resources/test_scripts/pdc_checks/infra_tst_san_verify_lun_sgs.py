#!/usr/bin/env python
#from pprint import pprint

"""
TEST CASE DESCRIPTION:

Verify that the modelled LUNs are in the correct storage group:

- Non-shared LUNs should only be in the SG for the node
- Shared LUNs should be in each node's SG
- Bootable LUNs should have HLU 0
- Non-Bootable LUNs should have HLU > 0

"""

from infra_utils.san_test import SanTest
from ptaf.utils.litp_cmd_utils import LitpUtils
from ptaf.utils.litp_utils.api_client import LitpClient
from ptaf.utils.model_utils import ModelUtils
from infra_utils.utils.enm_helpers import Model

class TestCase(SanTest):

    """
    Test case to verify LUNs defined in the model
    """

    def setUp(self):
        """
        Set up the test case
        """
        super(TestCase, self).setUp()

        self.litp_utils = LitpUtils()
        self.model_utils = ModelUtils()
        self.navi_target = self.mws


    def tearDown(self):
        """
        Clean up after the test case
        """
        super(TestCase, self).tearDown()

    def test(self):
        """
        Test case implementation
        """
        # GET LUN AND SG INFORMATION FROM SAN
        san_luns = self.navi_get_luns()
        san_sgs = self.navi_get_sgs()

        litp_pass = self.litp_utils.get_litpadmin_password(self)
        client = LitpClient(host=self.mws['ip'],password=litp_pass)
        model = Model(client)

        # GET ALL LUNS FROM MODEL, USING THE 'DEPLOYMENTS' LINK
        # AS THIS PROVIDES INFORMATION IN THE PATH TO DETERMINE THE SG
        model_luns = model.luns
        # ITERATE THROUGH THE LUN-DISKS
        for model_lun in model_luns.values():
            lun_name = model_lun.properties['lun_name']
            self.info("Verifying SG for LUN: %s" % lun_name)

            lun_found = False
            for san_lun_id, san_lun in san_luns.items():
                # CHECK THAT MODELLED LUN IS ON THE SAN
                if lun_name == san_lun['Name']:
                    lun_found = True
                    self.info("Found LUN %s on SAN.  LUN ID: %s" % (lun_name, san_lun_id))
                    # GET THE NUMBER OF NODES
                    # SHOWS HOW MANY SGS THE LUN SHOULD BE REGISTERED IN
                    lun_node_count = len(model_lun.nodes)
                    # MAKE LIST OF SGS WHICH THE LUN BELONGS TO
                    sg_matches = {}
                    for san_sg in san_sgs: # LUN ID is KEY
                        if san_lun_id in san_sg['HLU/ALU Pairs']:
                            self.info("LUN is registered with SG %s " % san_sg['Storage Group Name'])
                            sg_matches[san_sg['Storage Group Name']] = san_sg
                    break

            # VALIDATE THE MODEL WITH THE SAN INFORMATION

            # 1) DID WE FIND THE LUN
            if lun_found == False:
                self.fail("LUN %s not found on SAN" % lun_name)

            # 2) IS LUN IN ANY SG
            if len(sg_matches) == 0:
                self.fail("LUN %s not registered to any SG on SAN" % lun_name)

            # 3) IS THE LUN IN THE CORRECT SG
            sg_name = self.model_utils.sg_name_from_item(model_lun)
            if sg_name not in sg_matches:
                self.fail("LUN %s is not attached to correct storage group" % lun_name)

            # 4) IS THE LUN IN THE CORRECT NUMBER OF SGS
            if len(sg_matches) != lun_node_count:
                self.fail("LUN %s should be in %s SGs, this is in %s " % lun_name,
                           lun_node_count, len(sg_matches))

            # 5) DOES THE HLU MATCH THE MODELLED BOOTABLE FLAG?
            if model_lun.properties['bootable'] == 'true':
                if sg_matches[sg_name]['HLU/ALU Pairs'][san_lun_id] != '0':
                    self.fail("Bootable LUN has sg HLU non-zero")
            else:
                if sg_matches[sg_name]['HLU/ALU Pairs'][san_lun_id] == '0':
                    self.fail("Non-Bootable LUN has sg HLU zero")

            self.info("Test Completed Successfully")

if __name__ == '__main__':
    TestCase().run_test()
