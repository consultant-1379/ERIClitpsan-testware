#!/usr/bin/env python

from infra_utils.snap_test import SnapTest
import time

class TestCase(SnapTest):
    """
    Test Case:
    1) Creates a snapshot through LITP
    2) Checks with naviseccli if the snapshot was created
    3) Remove the snapshot through naviseccli
    4) Checks that the snapshot was removed from the SAN
    5) Remove the snapshot through LITP
    6) Checks that the snapshot was removed from the model
    """

    def test(self):
        # check if the snapshot already exists
        snaps = self.litp_client.get('/snapshots').children
        for snap in snaps:
            if snap.id == self.snap:
                raise Exception("Snapshot '%s' already exists" % self.snap)
            
        print "creating snapshot"
        self.litp_client.create_snapshot(self.snap)
        plan = self.litp_client.wait_plan_completion()
        if plan.properties['state'] != 'successful':
            raise Exception("Snapshot creation failed \n plan output: %s" % \
                    str(plan.properties))
        snap_in_model = self.litp_client.get('/snapshots/%s' % self.snap)
        self.assertTrue(snap_in_model)
    
        # Assert the LUNs in the model were snapped on the SAN
        san_snaps = self.navi_get_snapshots()
        model_snaps = self.get_model_snapshots()
        self.assertTrue(self.verify_snapshot_creation(
            san_snaps, model_snaps))
        
        # Remove the snaps on the LUNS on the SAN
        our_snaps = self.filter_snapshot(san_snaps, model_snaps)
        self.assertTrue(len(our_snaps)> 0, str(len(our_snaps)))
        print "removing snapshot with navisec" 
        self.navi_delete_snapshot(our_snaps[0])

        print "removing snapshot with litp"
        self.litp_client.remove_snapshot(self.snap)
        plan = self.litp_client.wait_plan_completion()
        self.assertEqual(plan.properties['state'], 'successful')
        
        # check that the snapshot was removed from the model
        snap = self.litp_client.get('/snapshots/%s' % self.snap)
        self.assertFalse(snap)

    def filter_snapshot(self, navi_snaps, model_snaps):
        model_names = [m_snp.properties["lun_name"] for m_snp in model_snaps]
        snaps = []
        for navi_snap in navi_snaps:
            navi_name = navi_snap["Name"]
            for name in model_names:
                snap_name = "L_" + name + "_"
                if snap_name in navi_name:
                    snaps.append(navi_snap)
        return snaps

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
                print "removing snapshot with litp"
                self.litp_client.remove_snapshot(self.snap)
                plan = self.litp_client.wait_plan_completion()
                self.assertEqual(plan.properties['state'], 'successful')

 
        
        # Remove the snaps on the LUNS on the SAN
        all_snaps  = self.navi_get_snapshots()
        model_snaps = self.get_model_snapshots()
        filtered_snaps = self.filter_snapshot(all_snaps, model_snaps)
        for snap in filtered_snaps:
            if snap:
                print "removing snapshot with navisec"
                self.navi_delete_snapshot(self.snap)

if __name__ == '__main__':
    TestCase().run_test()
