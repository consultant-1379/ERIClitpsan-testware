#!/bin/bash/env python
from infra_utils.san_test import SanTest
from ptaf.utils.litp_cmd_utils import LitpUtils
from ptaf.utils.litp_utils.api_client import LitpClient
from ptaf.utils.cmd_utils import CMDUtils

class TestCase(SanTest):

    """
    DESCRIPTION:
    
    Test to perform various sanity checks on the test environment for reporting purposes.
    Checks:
    - LITP Version
    - Deployment Description Version
    - SAN Plugin and PSL rpm versions
    - SAN API Version
    - Naviseccli version
    - VNX Flare/OE Version
    - VNX Version
    - ENMinst Version
    - Red Hat Version
    
    STORY:
    OSS-77847
    """

    def setUp(self):
        """
        Set up the test case
        """
        super(TestCase, self).setUp()

        self.litp_utils = LitpUtils()

        # Create instance of CMDUtils to run popen cmds on the MS
        self.cmd_utils = CMDUtils()
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
        # Dictionary to record name and versions of checks for printing purposes
        self.env_versions = {}

        #Check to see what version of LITP is installed on the machine and prints out the version
        litp_cmd = self.cmd_utils.run_ssh_command("litp version", self.navi_target['ip'], 'root', self.navi_target['root_password'])
        self.env_versions["LITP Version"] = litp_cmd.stdout

        # Check the version of the red-hat release
        red_hat_cmd = self.cmd_utils.run_ssh_command("cat /etc/redhat-release", self.navi_target['ip'], 'root', self.navi_target['root_password'])
        self.env_versions["Red Hat Version: "] = red_hat_cmd.stdout

        # Check the version of ENM
        enm_version_cmd = self.cmd_utils.run_ssh_command("cat /etc/enm-version", self.navi_target['ip'], 'root', self.navi_target['root_password'])
        self.env_versions["ENM Version: "] = enm_version_cmd.stdout

        # Returns a naviseccli command with correct parameters to get vnx flare/OE version
        navi_args = ["ndu", "-list", "-name", "VNX-Block-Operating-Environment", "-rev"]
        oe_version = self.cmd_utils.run_ssh_command(self.navi_get_cmd(navi_args), self.navi_target['ip'], 'root', self.navi_target['root_password'])
        print "oe version ", oe_version
        version_num = oe_version.stdout.split(":")
        print "version", version_num
        self.env_versions["VNX Flare/OE Version"]  = version_num[2]

        #Returns a naviseccli command to find the VNX  version
        navisec_args = ["getall", "|" , "grep", "'^Model:'"]
        vnx_version = self.cmd_utils.run_ssh_command(self.navi_get_cmd(navisec_args), self.navi_target['ip'], 'root', self.navi_target['root_password'])
        vnx_vers_num = vnx_version.stdout.split(":")
        self.env_versions["VNX Version"]  = vnx_vers_num[1]


        # Interrogates the MS for RPM's and their Versions
        self.get_version_information("SAN PSL", "ERIClitpsanemc_")
        self.get_version_information("SAN Plugin", "ERIClitpsan_")
        self.get_version_information("SAN API", "ERIClitpsanapi_")
        self.get_version_information("Naviseccli", "NaviCLI")
        self.get_version_information("ENMinst", "ERICenminst_")
        self.get_version_information("Deployment Description", "ERICenmdeploymenttemplates_")

        # Prints out the versions
        self.print_version_details()

    def get_version_information(self, key_name, rpm_search_name ):
        """
        Contacts the model to retrieve the version information from the rpms.
        Checks that the command returns the correct information
        the version information of the rpms is then stored in a dictionary
        """

        cmd = self.cmd_utils.run_ssh_command("rpm -qa | grep -i " + rpm_search_name, self.navi_target['ip'], 'root', self.navi_target['root_password'])
        # Checks to see that the rpm searched for is what is returned in the cmd
        prod_version = self.cmd_utils.run_ssh_command("rpm -q --qf '%{VERSION}\n' " + cmd.stdout, self.navi_target['ip'], 'root', self.navi_target['root_password'])
        self.env_versions[key_name + " Version"] = prod_version.stdout

    def print_version_details(self):
        """
        Removes any stray characters in the dictionary before printing output
        prints the output of the dictionary
        """

        word_len = 0

        self.env_versions = dict(map(str.strip,x) for x in self.env_versions.items())

        # Gets the longest key name for printing purposes
        for k,v in self.env_versions.items():
            if len(k) > word_len:
                word_len = len(k) + 2

        # prints out the formatted information of the dictionary
        format_str = '{0:' + str(word_len)+ 's} {1:10s}'
        for k,v in self.env_versions.items():
            print format_str.format(k,v)

if __name__ == '__main__':
    TestCase().run_test()

