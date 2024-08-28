#!/usr/bin/env python

"""
DESCRIPTION:
Verify the expand lun functionality

AGILE:
TORF-80399
"""

from add_expand_luns_test import AddExpandTest
from ptaf.utils.litp_utils.api_client import LitpException
from infra_utils.utils.enm_helpers import Model
import decimal

class TestCase(AddExpandTest):

    """
    Test case to verify the expand lun functionality in the plugin
    http://taftm.lmera.ericsson.se/#tm/viewTC/17391/version/1
    :Jira          Story TORF-80399
    :Requirement   ID: TORF-80399
    :Title:        Automate test for LUN expansion
    :Description:  Test the expansion of all LUN's in a pre-deployed system
    :PreCondition: A ENM deployment has been initially installed
    :TestStep:     1: Get a list of LUNs to expand
                   2: Use litp_client.update_item to update each LUN by 1G
                   3: Run LITP create_plan
                   4: Run LITP run_plan
                   5: Use Navisec CLI to verify LUNs have been expanded

    """

    def test(self):
        # 1: Get a list of LUNs to expand
        pre_expansion_luns = []
        pre_expansion_luns = self.get_luns_for_expansion()

        # 2: update each LUN by 1G using litp_client.update_item
        #make litp_client.update_item call
        expand_size = 0
        self._logger.info('\nExpanding LUNs')
        for lun in pre_expansion_luns:
            current_size = str(lun.size)
            self._logger.info("Current Size of " + lun.lunk + ": "+ current_size)
            total_size = str(self.get_new_lun_size(current_size))
            self._logger.info("New Size of " + lun.lunk + ": "+ total_size)
            lun_attributes = {"size": total_size}
            self.litp_client.update_item(lun.inherited_path, \
                                                **lun_attributes)

        # 3: Run LITP create_plan
        self._logger.info("Creating Plan")
        self.litp_client.create_plan()

        # 4: Run LITP run_plan
        self._logger.info("Running Plan")
        self.litp_client.run_plan()

        self.litp_client.wait_plan_completion()

        # 5: Use Navisec CLI to verify LUNs have been expanded
        #new model instance here
        self.model = Model(self.litp_client)
        #get lun name and sizes here
        lun_properties = self.get_lun_properties()

        for lun in lun_properties:
            check_lun = self.san_client.navi_get_lun(lun['lun_name'])
            check_lun_size = check_lun['User Capacity (GBs)']
            model_lun_size = self.convert_to_gb(lun['size'])
            check_lun_size, model_lun_size = decimal.Decimal(check_lun_size), decimal.Decimal(model_lun_size)
            self.assertEquals(check_lun_size, model_lun_size)

if __name__ == '__main__':
    TestCase().run_test()
