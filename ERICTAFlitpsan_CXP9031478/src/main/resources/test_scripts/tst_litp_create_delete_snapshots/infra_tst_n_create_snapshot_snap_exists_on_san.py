#!/usr/bin/env python

"""
DESCRIPTION:
Verify the create snapshot functionality when snapshot exists on the SAN

AGILE:
OSS-78423
"""
from infra_utils.snap_test import SnapTest
from ptaf.utils.litp_cmd_utils import LitpUtils

class TestCase(SnapTest):
    """
    Test case to verify the create_snapshot functionality in the plugin
    http://taftm.lmera.ericsson.se/#tm/viewTC/infra_tst_n_create_snapshot_snap_exists_on_san

    :Jira          Story OSS-78423
    :Requirement   ID: OSS-78423
    :Title:        Run create_snapshot when snapshot named L_<LUN name>_snapshot
                   exists on SAN
    :Description:  Negative test SAN plugin does not create any snapshots on
                   the SAN. Litp create_snapshot plan fails.
    :TestStep:     1: Create a snapshot on one of the LUNs in the model.
                   2: Run litp create_snapshot command
                   3: Wait for plan to complete
                     3.1 Verify that the plan fails
                     3.2 Verify that the san plugin task to check if a snapshot
                         L_<LUN name>_snapshot already exists on the SAN
    """

    def setUp(self):
        """
        Set up the test case
        """
        super(TestCase, self).setUp()

        self.sanapi_target = self.mws
    
    
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
    
    
    def clean_down(self):
        """
         clean_down  method run after the test is completed or after the plan fails
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
        
    def tearDown(self):
        """
        tearDown method run after the test is completed or after the plan fails
        """
        self.clean_down()

    def test(self):
        """
        Run create_snapshot when a snapshot already exists on a LUN on the
        SAN (with name <lun name>_snapshot)

        Actions:
            1: Assert that the plan fails and that the SAN plugin does not
               generate any snapshot tasks
            2: Delete the snapshot on the SAN and run create_snapshot again.
               Verify that it is successful.
        """

        # From the Litp model find a LUN which is snapable
        luns_to_be_snapped = self.get_model_snapshots()
        lun_to_be_snapped = luns_to_be_snapped[0].properties["lun_name"]
        
        
        # create a snapshot of the LUN
        snap_name = "L_"+lun_to_be_snapped+"_"
        cmd = self.sanapi_create_snapshot(snap_name,lun_to_be_snapped)
        self.assertTrue(cmd.retcode == 0,
                        'Fail: sanapi.create_snapshot failed')


        # Run litp command create_snapshot
        print "creating snapshot"
        self.litp_client.create_snapshot(self.snap)

        # check that litp plan failed
        self._logger.info('Waiting for plan to complete')
        plan = self.litp_client.wait_plan_completion()

        self.assertEqual(plan.properties['state'], "failed")

        # check that the san plugin task to check for existing snaps failed
        task_name = "Checking for existing snapshots"
        task_status = LitpUtils.get_litp_task_status(self, task_name)
        self.assertEqual(task_status.lower(), 'failed',
                         'Fail: Check for existing snapshots failed')

        # Remove the litp snapshot and the SAN snapshot
        self.clean_down()


if __name__ == '__main__':
    TestCase().run_test()
