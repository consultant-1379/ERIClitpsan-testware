from infra_utils.hwcomm_test import HWCommTest
from infra_utils.utils.hwcomm_utils import SED_PATH

from time import strftime
from datetime import datetime


class TestCase(HWCommTest):
    """
    Test case to test the external dependencies of infra_utils
    http://taftm.lmera.ericsson.se/#tm/viewTC/18931

    :Jira          Story TORF-110813
    :Requirement   ID: TORF-110813
    :Title:        INFRA: Test the external dependencies of infra_utils.
    :Description:  This test case tests the external dependencies by running
                   HWCommTest commands. This is the only module that has
                   external dependencies on infra_utils
    :PreCondition: ENM deployed
    :TestStep:     1. Verify run_oa_cmd is called
    """

    def setUp(self):
        """
        Setup the test
        """
        super(TestCase, self).setUp()
        self._oa_pex_spawn = {}

    def tearDown(self):
        """
        Clean up after the test case
        """
        super(TestCase, self).tearDown()

    def test(self):
        """Start test of pexpect """
        print self.shortDescription()
        self.sed_dict["enclosure1_OAIP1"] = self.dmt[-1]["enclosure1_OAIP1"]
        self.sed_dict["enclosure1_OAIP2"] = self.dmt[-1]["enclosure1_OAIP2"]
        self.sed_dict["enclosure1_username"] = self.dmt[-1]["enclosure1_username"]
        self.sed_dict["enclosure1_password"] = self.dmt[-1]["enclosure1_password"]
        self.oa_connect("enclosure1")
        self._logger.info('Testing run_oa_cmd')
        res=self.run_oa_cmd("SHOW SERVER INFO ALL", "enclosure1")
        self.assertTrue('Server' in res)

if __name__ == '__main__':
    TestCase().run_test()
