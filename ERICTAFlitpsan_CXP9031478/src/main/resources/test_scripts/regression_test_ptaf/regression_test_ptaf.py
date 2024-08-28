#!/usr/bin/env python

from ptaf.utils.litp_cmd_utils import LitpUtils
from ptaf.utils.litp_utils.api_client import LitpClient
from ptaf.utils.litp_utils.model_item import ModelItem
from infra_utils.utils.enm_helpers import Model
from ptaf.generic_test import GenericTest
from socket import gaierror


class TestCase(GenericTest):

    """
    Test case to test the external dependencies of PTAF
    http://taftm.lmera.ericsson.se/#tm/viewTC/18929

    :Jira          Story TORF-110813
    :Requirement   ID: TORF-110813
    :Title:        INFRA: Test the external dependencies of PTAF.
    :Description:  This test case tests the external dependencies
                   by running each of the ptaf commands.
    :PreCondition: ENM deployed
    :TestStep:     1. Test cmd_utils commands
                        1.1. Verify run_local_command
                        1.2. Verify run_ssh_command
                        1.3. Verify run_ssh_command_via_proxy
                        1.4. Verify run_ssh_command_as_root_via_proxy
                        1.5. Assert timeout is working when command fails
                   2. Testing litp_utils.api_client
                        2.1. Verify create_item
                        2.1. Verify remove_item
    """

    def setUp(self):
        """
        Set up the test case
        """
        super(TestCase, self).setUp()
        self.litp_utils = LitpUtils()
        # GET LITP Model INFORMATION
        litp_pass = self.litp_utils.get_litpadmin_password(self)
        self.client = LitpClient(host=self.mws['ip'], password=litp_pass)
        self.model = Model(self.client)
        self.ms_ip = self.mws['ip']
        self.ms_user = 'root'
        self.ms_pass = self.mws['root_password']
        self.node_user = 'litp-admin'
        self.node_root = '12shroot'
        self.item_path = '/software/items/TORF-110813'

    def tearDown(self):
        """
        Clean up after the test case
        """
        super(TestCase, self).tearDown()
        if self.client.get(self.item_path):
            self.client.remove_item(self.item_path)

    def get_node_password(self, node, username):
        """Gets the node password from the DMT"""
        node_name = node.id.replace('-', '')
        for item in self.dmt:
            if 'type' in item and item['type'] == node_name:
                # Find passwords for users
                for user in item['users']:
                    if user['username'] == username:
                        return user["password"]

    def test(self):
        """
        Test case implementation
        """
        cmd = 'uname -a'
        # Testing cmd_utils commands
        self._logger.info('Testing run_local_command')
        res = self.cmd_utils.run_local_command(cmd)
        self.assertTrue('Linux' in res.stdout)

        self._logger.info('Testing run_ssh_command')
        res = self.cmd_utils.run_ssh_command(cmd, self.ms_ip,
                             self.ms_user, self.ms_pass)
        self.assertTrue('Linux' in res.stdout)

        self._logger.info('Testing run_ssh_command_via_proxy')
        node_name, node = self.model.nodes.items()[0]
        node_pass = self.get_node_password(node, 'litp-admin')
        res = self.cmd_utils.run_ssh_command_via_proxy(cmd,
                            self.ms_ip, self.ms_user, self.ms_pass, node_name,
                            self.node_user, node_pass)
        self.assertTrue('Linux' in res.stdout)

        self._logger.info('Testing run_ssh_command_as_root_via_proxy')
        res = self.cmd_utils.run_ssh_command_as_root_via_proxy(cmd,
                            self.ms_ip, self.ms_user, self.ms_pass, node_name,
                            self.node_user, node_pass, self.node_root)
        self.assertTrue('Linux' in res.stdout)

        # Assert timeout is working when command fails
        self._logger.info('Assert timeout is working when command fails')
        self.assertRaises(gaierror,
                    self.cmd_utils.run_ssh_command,
                    cmd, '0.0.0.0k', self.ms_user, self.ms_pass)

        # Testing litp_utils.api_client
        self._logger.info('Creating model item /software/items/TORF-110813')
        item = self.client.create_item(self.item_path, 'package',
                                       epoch=0, name='test')
        self.assertTrue(isinstance(item, ModelItem))

        self._logger.info('Removing model item /software/items/TORF-110813')
        item = self.client.remove_item(self.item_path)
        self.assertTrue(isinstance(item, ModelItem))

if __name__ == '__main__':
    TestCase().run_test()
