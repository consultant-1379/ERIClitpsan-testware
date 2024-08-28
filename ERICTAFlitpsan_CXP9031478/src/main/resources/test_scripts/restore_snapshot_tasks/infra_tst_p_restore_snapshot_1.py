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
    http://taftm.lmera.ericsson.se/#tm/viewTC/infra_tst_p_restore_snapshot_1
    :Jira          Story TORF-83703
    :Requirement   ID: TORF-83703
    :Title:        Create files on file systems supported by snappable LUNs
    :Description:  Positive test set up step for restore_snapshot_tasks suite
    :PreCondition: A ENM deployment has been initially installed
    :TestStep:     1: Determine which file systems to place files on
                   2: Place files on each node in the model

    """

    def test(self):
        self.pre_tasks_file = 'TORF-96617-Pre_Tasks'
        self.tasks_file = 'TORF-96619-Tasks'
        self.resultStr1 = ""
        self.service_dict = self.get_service_fs(self.litp_client)
        self.service_online = {}

        # 1: Determine which file systems to place files on
        # Iterate through each node
        for node_id, node in self.model.nodes.items():
            print "> NODE %s, hostname %s, ip %s" % (node_id,
                    node.properties['hostname'], node.ip)
            snappable_luns = self.get_snappable_luns(node)
            # Iterate through each LUN &
            # Use only snap size > 0, external snap == false
            for lun_name, lun in snappable_luns.items():
                # get file systems
                fs = self.get_file_systems(node_id, lun_name)
                print "      LUN: %s  FS: %s" % (lun_name, ', '.join(fs))
                if not fs:
                    print "no file systems to create files on"
                    continue
                for item in fs:
                    if item == "/":
                        file_path1 = item + self.pre_tasks_file
                    else:
                        file_path1 = item + '/' + self.pre_tasks_file
                    # 2: Place files on each node in the model
                    command = "touch %s" % ''.join(file_path1)
                    errorMsg = "Problem touching file: %s on LUN: %s" \
                    % (file_path1, lun_name)
                    print "Node: " + node_id
                    print "checking LUN shared"
                    if lun.properties['shared'] == 'true':
                        # shared luns only run touch command
                        # if service is online
                        print "lun %s is shared" % lun_name
                        service_is_online = self.verify_online_services(item,\
                             node)
                        if service_is_online:
                            self.run_server_command(command, errorMsg, \
                            file_path1, node, lun_name, log_path=True)
                    else:
                        # non shared luns always run touch command
                        self.run_server_command(command, errorMsg, \
                            file_path1, node, lun_name, log_path=True)
        exitCode = 0
        if self.resultStr1:
            print "Unable to create file(s) in: " + self.resultStr1
            exitCode = 1
        for svc in self.service_online:
            if self.service_online[svc] == 0:
                print "Unexpected offline service, unable to check\
                 file system: %s " % svc
                exitCode = 1
        self.assertEquals(exitCode, 0)

if __name__ == '__main__':
    TestCase().run_test()
