#!/usr/bin/env python

"""
DESCRIPTION:
Verify the create snapshot functionality

AGILE:
OSS-78001
"""

from ptaf.utils.litp_cmd_utils import LitpUtils
from ptaf.utils.litp_utils.api_client import LitpClient
from ptaf.utils import test_constants
from infra_utils.snap_test import SnapTest

class TestCase(SnapTest):

    """
    Test case to verify the create_snapshot functionality in the plugin
    http://taftm.lmera.ericsson.se/#tm/viewTC/7638

    :Jira          Story OSS-78001
    :Requirement   ID: OSS-78001
    :Title:        Test create_snapshot functionality in SAN plugin
    :Description:  Positive test SAN plugin creates snapshots on the VNX for snapable lun-disks
    :PreCondition: A cluster is installed with at least one lun-disk on one node
    :TestStep:     1.1: Run litp create_snapshot command
                   2.1: Wait for plan to complete
                     2.1 Verify that a snapshot exists on the VNX for each snapable lun-disk
    """
    def filter_snapshot(self, snaps):
        filtered = []
        for snap in snaps:
            if snap['Name'].split("_")[-1] == self.snap:
                filtered.append(snap)
        return filtered

    def cleanup_plan(self, plan):
        """
        Will remove a plan when it is not in successful state
        """
        plan_state = plan.properties["state"]
        if plan_state == "running":
            self.litp_client.stop_plan()
            self.litp_client.remove_plan()
        if plan_state != "successful":
            self.litp_client.remove_plan()
    
    def tearDown(self):
        """
        Clean up after the test case
        tearDown method run after the test is completed or after the plan fails
        1) remove plan if it's uncompleted
        2) see if any test snap is in the model
        3) if found, remove test snap through LITP
        4) see if any test snap is found in the SAN
        5) if found, remove test snap through navissecli
        """
        # remove uncompleted plan
        plan = self.litp_client.get_plan()
        if plan is not None:
            self.cleanup_plan(plan)

        # see if any test snap is in the model
        snaps = self.litp_client.get("/snapshots").children
        if snaps:
            names = set([s.id for s in snaps])
            if self.snap in names:
                print "removing snapshot through LITP"
                self.litp_client.remove_snapshot(self.snap)
                self.litp_client.wait_plan_completion()

        # Remove the snaps on the LUNS on the SAN
        all_snaps  = self.navi_get_snapshots()
        filtered_snaps = self.filter_snapshot(all_snaps)
        for snap in filtered_snaps:
            if snap:
                print "removing snapshot with navisec"
                self.navi_delete_snapshot(self.snap)
        super(TestCase, self).tearDown()

    def test(self):
        """
        Test case implementation
        """
        # check if the snapshot already exists
        snaps = self.litp_client.get('/snapshots').children
        for snap in snaps:
            if snap.id == self.snap:
                raise Exception("Snapshot '%s' already exists" % self.snap)

       
        #1.1: Run litp create_snapshot command
        print "creating snapshot"
        self.litp_client.create_snapshot(self.snap)
        
        # 2.1: Wait for plan to complete
        plan = self.litp_client.wait_plan_completion()
        if plan.properties['state'] != 'successful':
            raise Exception("Snapshot creation failed \n plan output: %s" % \
                    str(plan.properties))
        snap = self.litp_client.get('/snapshots/%s' % self.snap)
        self.assertTrue(snap)

        self.info('Searching LITP model for luns to be snapped by SAN plugin')
        luns_to_be_snapped = self.get_model_snapshots()
        self.info('Searching for all snaps')
        navi_snaps = self.navi_get_snapshots()
        #2.1 Verify that a snapshot exists on the VNX for each snapable lun-disk
        self.info('Verifying a snap exists for each lun to be snapped by SAN')
        self.assertTrue(self.verify_snapshot_creation(navi_snaps,
                                                      luns_to_be_snapped))
        

if __name__ == '__main__':
    TestCase().run_test()
