#!/usr/bin/env python
from ptaf.utils.litp_utils.api_client import LitpException
"""
DESCRIPTION:
Verify the restore snapshot functionality

AGILE:
TORF-97834
"""

from add_expand_luns_test import AddExpandTest
from ptaf.utils.litp_utils.api_client import LitpException
from infra_utils.utils.enm_helpers import Model
import decimal

class TestCase(AddExpandTest):

    """
    Test case to verify the create_snapshot functionality in the plugin
    http://taftm.lmera.ericsson.se/#tm/viewTC/17392/version/1
    :Jira          Story TORF-92038
    :Requirement   ID: TORF-92038
    :Title:        Automate test for LUN addition
    :Description:  Test the addition of LUNs in a pre-deployed system
    :PreCondition: A ENM deployment has been initially installed
    :TestStep:     1: For each existing LUN, use litp_client.create_item
                      to add a new 1G LUN
                   2: Use litp_client.create_item  to create a new 
                      Storage Profile for each LUN
                   3: Run LITP create_plan
                   4: Run LITP run_plan
                   5: Use Navisec CLI to verify LUNs have been added

    """

    def test(self):
        # 1: For each existing LUN, add a new 1G LUN
        self._logger.info('\nAdding new 1G LUNs')
        # find a list of LUNs
        luns = self.get_luns_for_addition()
        created_devices = set([])
        for lun in luns:
            lun_attributes = {"lun_name": lun.lunk,
                             "name": lun.name,
                             "bootable": lun.bootable,
                             "storage_container": lun.storage_container,
                             "shared": lun.shared,
                             "size": lun.size,
                             "snap_size": lun.snap_size,
                             "external_snap": lun.external_snap}
            phys_attributes = {"device_name": lun.name}

            # make the LITP create_item call to create new LUNs
            item = self.litp_client.create_item(lun.inherited_path, 'lun-disk', **lun_attributes)
            self._logger.info("Creating " + lun.lunk)
  
            # 2: Add each new LUN to a storage profile
            if lun.vg_inherited not in created_devices:
                item = self.litp_client.create_item(lun.vg_inherited, 'physical-device', **phys_attributes)
                created_devices.add(lun.vg_inherited)
  
        # 3: Run LITP create_plan
        self._logger.info("Creating Plan")
        self.litp_client.create_plan()
  
        # 4: Run LITP run_plan
        self._logger.info("Running Plan")
        run_result = self.litp_client.run_plan()
  
        self.litp_client.wait_plan_completion()

        # 5: Use Navisec CLI to verify LUNs have been added
        #create new model instance here
        self.model = Model(self.litp_client)

        lun_properties = self.get_lun_properties()
        lun_properties = [lun  for lun in lun_properties if self.postfix_lun in lun['lun_name']]
        
        self._logger.info("Verifying LUNs are available on Host")
        self.verify_luns_on_host(lun_properties)

        self._logger.info("Verifying LUN sizes")

        for lun in lun_properties:
            check_lun = self.san_client.navi_get_lun(lun['lun_name'])
            check_lun_size = decimal.Decimal(check_lun['User Capacity (GBs)'])
            model_lun_size = decimal.Decimal(self.convert_to_gb(lun['size']))
            self.assertEquals(check_lun_size, model_lun_size)

if __name__ == '__main__':
    TestCase().run_test()
