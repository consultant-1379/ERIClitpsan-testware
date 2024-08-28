#!/usr/bin/env python

"""
DESCRIPTION:
Verify the LUNs defined in the LITP model exist on the Storage Array

AGILE:
OSS-76130
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

        # Get all LUNs from the Storage Array
        luns_in_array = [lun['Name'] for lun in self.navi_get_luns().values()]

        # Get all 'lun-disk' items from LITP model
        client = LitpClient(host=self.mws['ip'],password=self.litp_utils.get_litpadmin_password(self))
        model = Model(client)

        self.info('Searching LITP model for lun-disk items')
        luns_in_model = model.luns

        verified_luns = []

        # Verify the LUNs exist in the Storage Array
        for lun in luns_in_model.values():
            lun_name = lun.properties['lun_name']
            if lun_name in verified_luns:
                continue
            if lun.state == 'Applied':
                self.info('Checking LUN %s', lun_name)
                self.assertTrue(lun_name in luns_in_array)
                verified_luns.append(lun_name)
            else:
                self.info(
                    'Skipping LUN %s because state is %s',
                    lun_name, lun.state)


if __name__ == '__main__':
    TestCase().run_test()
