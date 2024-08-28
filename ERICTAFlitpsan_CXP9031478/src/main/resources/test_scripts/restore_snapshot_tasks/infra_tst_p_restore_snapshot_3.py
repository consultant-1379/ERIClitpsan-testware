#!/usr/bin/env python

"""
DESCRIPTION:
Verify the restore snapshot functionality

AGILE:
TORF-96620
"""

from infra_utils.restore_test import RestoreTest

class TestCase(RestoreTest):

    """
    Test case to verify the create_snapshot functionality in the plugin
    http://taftm.lmera.ericsson.se/#tm/viewTC/infra_tst_p_restore_snapshot_3

    :Jira          Story TORF-83703
    :Requirement   ID: TORF-83703
    :Title:        Create files on file systems supported by snappable LUNs
    :Description:  Positive test set up step for restore_snapshot_tasks suite
    :PreCondition: A ENM deployment has been initially installed
    :TestStep:     1: Verify that file set A is present
                   2: Verify that file set B is removed
                   3: Remove any remaining test files

    """

    def test(self):
        self.pre_tasks_file = 'TORF-96617-Pre_Tasks'
        self.tasks_file = 'TORF-96619-Tasks'
        self.resultStr1 = ""
        self.resultStr2 = ""
        self.service_dict = self.get_service_fs(self.litp_client)
        self.service_online = {}

        # Iterate through each node
        for node_id, node in self.model.nodes.items():
            print "> NODE %s, hostname %s, ip %s" % (node_id,
                    node.properties['hostname'], node.ip)
            snappable_luns = self.get_snappable_luns(node)
            # Iterate through each LUN &
            # use only snap size \> 0, external snap == false
            for lun_name, lun in snappable_luns.items():
                # get file systems
                fs = self.get_file_systems(node_id, lun_name)
                print "      LUN: %s  FS: %s" % (lun_name, ', '.join(fs))
                if not fs:
                    print "no file systems to create files on"
                    continue
                for item in fs:
                    if item == "/":
                        cmd_path1 = item + self.pre_tasks_file
                        cmd_path2 = item + self.tasks_file
                    else:
                        cmd_path1 = item + '/' + self.pre_tasks_file
                        cmd_path2 = item + '/' + self.tasks_file
                    # 1: Verify that file set A is present
                    command1 = "test -f %s" % ''.join(cmd_path1)
                    errorMsg1 = "File %s not found on LUN: %s" \
                    % (cmd_path1, lun_name)
                    # 3: Remove any remaining files
                    command2 = "rm -f %s" % ''.join(cmd_path1)
                    errorMsg2 = ""
                    # 2: Verify that file set B is removed
                    command3 = "test -f %s" % ''.join(cmd_path2)
                    errorMsg3 = "Incorrect File %s found on LUN: %s" \
                    % (cmd_path2, lun_name)
                    # 3: Remove any remaining files
                    command4 = "rm -f %s" % ''.join(cmd_path2)
                    print "Node: " + node_id
                    service = None
                    print "checking LUN shared"
                    if lun.properties['shared'] == 'true':
                        # shared luns only run commands
                        # if service is online
                        print "lun %s is shared" % lun_name
                        service_is_online = self.verify_online_services(item,\
                             node)
                        if service_is_online:
                            self.run_server_command(command1, errorMsg1, \
                                cmd_path1, node, lun_name, log_path=True)
                            self.run_server_command(command2, errorMsg2, \
                                cmd_path1, node, lun_name, log_path=None)
                            self.run_server_command(command3, errorMsg3, \
                                cmd_path2, node, lun_name, log_path=False)
                            self.run_server_command(command4, errorMsg2, \
                                cmd_path2, node, lun_name, log_path=None)
                    else:
                        # non shared luns always run commands
                            self.run_server_command(command1, errorMsg1, \
                                cmd_path1, node, lun_name, log_path=True)
                            self.run_server_command(command2, errorMsg2, \
                                cmd_path1, node, lun_name, log_path=None)
                            self.run_server_command(command3, errorMsg3, \
                                cmd_path2, node, lun_name, log_path=False)
                            self.run_server_command(command4, errorMsg2, \
                                cmd_path2, node, lun_name, log_path=None)

        exitCode = 0
        if self.resultStr1:
            print "Files not found in: " + self.resultStr1
            exitCode = 1
        if self.resultStr2:
            print "Unexpected files found in: " + self.resultStr2
            exitCode = 1
        for svc in self.service_online:
            if self.service_online[svc] == 0:
                print "Unexpected offline service, unable to check file \
                system: %s " % svc
                exitCode = 1
        self.assertEquals(exitCode, 0)

if __name__ == '__main__':
    TestCase().run_test()
