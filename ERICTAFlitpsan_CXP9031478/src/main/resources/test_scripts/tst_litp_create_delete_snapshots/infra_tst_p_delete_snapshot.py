#!/usr/bin/env python

from infra_utils.snap_test import SnapTest


class TestCase(SnapTest):
    """
    Test Case:
    1) Creates a snapshot through LITP
    2) Checks with navissecli if the snapshot was created and
       that all luns with external_snap=false and snap_size>0
       were snapped.
    3) Remove the snapshot through LITP
    4) Checks that the snapshot was removed from the model
    5) Checks that the snapshot was removed from the SAN

    Documentation:
    http://confluence-nam.lmera.ericsson.se/pages/viewpage.action?pageId=145871423

    TMS:
    http://taftm.lmera.ericsson.se/#tm/viewTC/14764
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
        snap = self.litp_client.get('/snapshots/%s' % self.snap)
        self.assertTrue(snap)

        # check with naviseccli if the snapshot was created
        san_snap = self.navi_get_snapshots()
        model_snap = self.get_model_snapshots()
        self.assertTrue(self.verify_snapshot_creation(
            san_snap, model_snap))

        print "removing snapshot through LITP"
        self.litp_client.remove_snapshot(self.snap)
        plan = self.litp_client.wait_plan_completion()
        self.assertEqual(plan.properties['state'], 'successful')

        # check that the snapshot was removed from the model
        snap = self.litp_client.get('/snapshots/%s' % self.snap)
        self.assertFalse(snap)

        # verify if snapshot was removed from the SAN
        san_snap = self.navi_get_snapshots()
        self.assertTrue(self.verify_snapshot_removal(
            san_snap, model_snap))

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
                self.navi_delete_snapshot(snap['Name'])


if __name__ == '__main__':
    TestCase().run_test()
