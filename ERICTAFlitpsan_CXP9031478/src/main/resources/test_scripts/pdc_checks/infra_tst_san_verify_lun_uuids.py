#!/usr/bin/env python

"""
TEST CASE DESCRIPTION:

Verify the LUNs defined in the LITP model exist on the storage array
and are in 'Ready' state
"""

from infra_utils.san_test import SanTest
from ptaf.utils.litp_cmd_utils import LitpUtils
from ptaf.utils.litp_utils.api_client import LitpClient
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

        # Get all LUNs fet back	om the Storage Array
        luns_in_array = self.navi_get_luns()

        # Get all 'lun-disk' items from LITP model
        client = LitpClient(host=self.mws['ip'],
            password=self.litp_utils.get_litpadmin_password(self)
        )
        model = Model(client)
        luns_in_model = model.luns
        # Verify the LUNs exist in the Storage Array
        for lun in luns_in_model.values():
            lun_name = lun.properties['lun_name']
            lun_uuid = lun.properties['uuid']
            self.info("Checking LUN %s", lun_name)
            for array_lun in luns_in_array.values():
                if array_lun['Name'] == lun_name:
                    # Assert that the UUID in the model is the same as on the
                    # SAN
                    self.info("Checking UUIDs match for model and SAN for LUN %s", lun_name)
                    array_lun_uuid = array_lun['UID'].translate(None, ":-_")
                    assert(lun_uuid == array_lun_uuid)


if __name__ == '__main__':
    TestCase().run_test()
