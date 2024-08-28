
#!/usr/bin/env python


"""
DESCRIPTION:

AGILE:
"""

from infra_utils.restore_test import RestoreTest
from ptaf.utils.litp_cmd_utils import LitpUtils
from ptaf.utils.litp_utils.api_client import LitpClient
from infra_utils.utils.enm_helpers import Model
import os


class TestCase(RestoreTest):

    """
    Test case to verify snapshots exist on SAN after upgrade
    http://taftm.lmera.ericsson.se/#tm/viewTC/18509

    :Jira          Story TORF-101581
    :Requirement   ID: TORF-101581
    :Title:        Test restore snapshot when manual snapshot exists
    :Description:  Attempt to restore snapshot when a lun has a 2nd snapshot
                    manually created.
    :PreCondition: ENM deployed
    :TestStep:
    """

    def setUp(self):
        super(TestCase, self).setUp()
        self.ms_ip = self.mws['ip']
        self.ms_user = 'root'
        self.ms_pass = self.mws['root_password']
        self.node_user = 'litp-admin'
        self.node_root = '12shroot'
        self.file_name1 = "TORF-101581.tst1"
        self.file_name2 = "TORF-101581.tst2"
        self.test_suffix = "TST_"
        self.manual_snaps = []
        self.file_systems = {}

    def test(self):
        """
        Run restore_snapshot when manual snaps exists and verify that
        the correct snapshot has been restored.

        Actions:
            1: Creates a file in each file_system from the luns that will be
            snapped
            2: Create Litp snapshot
            3: Remove first files and create a second file set on each lun
            4: Create some manual Snaps
            5: Litp restore snapshot
            6: Verify if first files are present and not the second ones
        """
        snappable_luns = self.get_model_snapshots()
        self.file_systems = self.get_file_systems_dict(snappable_luns)
        self.info("File systems found : " % self.file_systems)
        self.info("create file set 1")
        for lun, fs_tuple in self.file_systems.items():
            node, fs_list = fs_tuple
            for fs in fs_list:
                self.create_file(fs, self.file_name1, node)
        self.info("create litp snapshot")
        self.litp_client.create_snapshot()
        self.litp_client.wait_plan_completion()

        self.info("remove file set 1")
        self.info("create file set 2")
        for lun, fs_tuple in self.file_systems.items():
            node, fs_list = fs_tuple
            for fs in fs_list:
                self.remove_file(fs, self.file_name1, node)
                self.create_file(fs, self.file_name2, node)
        self.info("create manual snap")
        self.make_manual_snap(snappable_luns)

        self.info("litp restore snapshot")
        self.litp_client.restore_snapshot()
        plan = self.litp_client.wait_plan_completion()
        self.info("verify file set 1 is present")
        self.info("verify file set 2 is absent")
        for lun, fs_tuple in self.file_systems.items():
            node, fs_list = fs_tuple
            for fs in fs_list:
                self.assertTrue(self.verify_file(fs, self.file_name1, node))
                self.assertFalse(self.verify_file(fs, self.file_name2, node))

    def tearDown(self):
        """
        Clean up after test
        Actions:
            1: Stop and remove plan
            2: Remove snapshot
            3: Remove manual snaps
            4: Remove added files
        """
        plan = self.litp_client.get("/plans/plan")
        if plan is not None:
            self.cleanup_plan(plan)
        snapshot = self.litp_client.get("/snapshots/snapshot")
        if snapshot is not None:
            self.litp_client.remove_snapshot()
            self.litp_client.wait_plan_completion()
        if len(self.manual_snaps) > 0:
            for snap in self.manual_snaps:
                self.sanapi_delete_snapshot(snap[1])
        for lun, fs_tuple in self.file_systems.items():
            node, fs_list = fs_tuple
            for fs in fs_list:
                self.remove_file(fs, self.file_name1, node)
                self.remove_file(fs, self.file_name2, node)

    def get_file_systems_dict(self, s_luns):
        """
        Builds a dictionary containing where luns
        are keys and tuples of node and file systems are 
        values. All the values where filtered to contain only
        the luns that should have files added to it.
        """
        lun_fs = {}
        for lun in s_luns:
            lun_name = lun.properties["lun_name"]
            fs = self.model.luns[lun_name].vg.file_systems
            # swap file systems shold be removed
            if 'swap' in fs:
                del fs['swap']
            if len(fs) > 0:
                node, online = self.get_node_and_status(lun, fs)
                if online:
                    lun_fs[lun] = (node, fs)
        return lun_fs

    def get_node_and_status(self, lun, fs_d):
        """
        Get the node related to a lun and if it's services
        are online. Only returns offline to sfha clusters,
        if not it assumes as online
        """
        cluster_path = self._get_parent_level(lun.path, 5)
        cluster = self.litp_client.get(cluster_path)
        node_path = self._get_parent_level(lun.path, 3)
        node_id = node_path.split("/")[-1]
        node = self.model.nodes[node_id]
        online = True
        if cluster.properties["cluster_type"] == "sfha":
            services = cluster["services"]
            for service in services:
                for filesys in service["filesystems"]:
                    if filesys.properties["mount_point"] in fs_d:
                        res = self.run_hastatus_online_command(
                                service.id, node)
                        online = "ONLINE" in res.stdout
        return node, online

    def run_node_cmd(self, command, node):
        """
        helper to abstract call to nodes
        """
        node_pass = self.get_node_password(node, 'litp-admin')
        return self.cmd_utils.run_ssh_command_as_root_via_proxy(command,
                self.ms_ip, self.ms_user, self.ms_pass,
                node.ip, self.node_user, node_pass,
                self.node_root)

    def create_file(self, fs, file_name, node):
        """
        Runs a touch command to create files
        """
        file_path = self._build_file_path(fs, file_name)
        touch_cmd = "touch %s" % file_path
        return self.run_node_cmd(touch_cmd, node)

    def remove_file(self, fs, file_name, node):
        """
        Runs a rm command to delete files
        """
        file_path = self._build_file_path(fs, file_name)
        rm_cmd = "rm %s" % file_path
        return self.run_node_cmd(rm_cmd, node)

    def sanapi_create_snapshot(self, snap_name, lun_name):
        """
        Overwrites sanapi_create_snapshot from SanUtils
        to run command from ms, not locally
        """
        cmd = self.sanapi_get_cmd([
            "--action=create_snapshot",
            "--snap_name='{0}'".format(snap_name),
            "--lunname='{0}'".format(lun_name),
        ])
        return self.cmd_utils.run_ssh_command(cmd, self.ms_ip,
                self.ms_user, self.ms_pass)

    def sanapi_delete_snapshot(self, snap_name):
        """
        Overwrites sanapi_delete_snapshot from SanUtils
        to run command from ms, not locally
        """
        cmd = self.sanapi_get_cmd([
            "--action=delete_snapshot",
            "--snap_name='{0}'".format(snap_name),
        ])
        return self.cmd_utils.run_ssh_command(cmd, self.ms_ip,
                self.ms_user, self.ms_pass)

    def make_manual_snap(self, snappable_luns, n_of_luns=2):
        """
        Creates n manual snaps, where n is defined by "n_of_luns" 
        """
        luns = snappable_luns[:n_of_luns]
        for lun in luns:
            l_name = lun.properties["lun_name"]
            self.manual_snaps.append((l_name, self.test_suffix + l_name))
        for lun_name, snap_name in self.manual_snaps:
            cmd = self.sanapi_create_snapshot(snap_name, lun_name)
            self.assertTrue(cmd.retcode == 0,
                            'Fail: sanapi.create_snapshot failed in %s snap'\
                            'creation' % snap_name)

    def verify_file(self, fs, file_name, node):
        """
        Verify if a file is present. Returns a bool value
        """
        file_path = self._build_file_path(fs, file_name)
        test_cmd = "test -e %s" % file_path
        cmd = self.run_node_cmd(test_cmd, node)
        return cmd.retcode == 0

    def _get_parent_level(self, path, level):
        """
        Helper function to return the parent of a litp item from it's path
        """
        return "/".join(path.split("/")[0: level * -1])

    def _build_file_path(self, fs, file_name):
        """
        Helper function to append slashes to a file path and
        build it's full path
        """
        if fs == "/":
            file_path = fs + file_name
        else:
            file_path = fs + "/" + file_name
        return file_path


if __name__ == '__main__':
    TestCase().run_test()
