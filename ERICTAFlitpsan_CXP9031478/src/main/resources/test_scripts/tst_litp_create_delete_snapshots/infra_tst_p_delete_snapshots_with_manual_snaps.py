#!/usr/bin/env python

"""
DESCRIPTION:
Verify the restore snapshot functionality if manual snaps are present

AGILE:
TORF-101576
"""

# To be deleted ----------------------------------------
# mvn clean install \
# -Dsuites=ERIClitpsan-testware/=ERICTAFlitpsan_CXP9031478/src/main/resources/suites/tst_litp_create_delete_snap_suite.xml \
# -Dtaf.clusterId=251


from infra_utils.snap_test import SnapTest
import time

class Object(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
    def __getitem__(self,key):
        return self.__dict__[key]

class Snap(Object):
    def key(self):
        return '{id}:{name}'.format(id=self.id, name=self.name)
    def __str__(self):
        return self.key()
    def __repr__(self):
        return self.__str__()

class ListOfSnaps(object):
    def __init__(self, context, navi_list=[]):
        self.context = context
        self.snaps = {}
        self.add_snaps(navi_list)
    def add_snaps(self, list_of_navi_snaps ):
        for navi_snap in list_of_navi_snaps:
            if type(navi_snap)==type({}):
                snap = Snap(name=navi_snap['Name'], id=navi_snap['Source LUN(s)'])
            else:
                lun_name = navi_snap.properties['lun_name']
                lun = self.context.sanapi_get_lun_by_name(lun_name)
                snap = Snap(name=lun_name, id=lun[lun_name]['lun id'])
            self.snaps[snap.key()]=snap
    def __str__(self):
        return repr(self.snaps)
    def __len__(self):
        return len(self.snaps)
    def __iter__(self):
        return iter(self.snaps.values())
    def __contains__(self, snap):
        return snap.key() in self.snaps


class TestCase(SnapTest):
    """
    Test case to verify the restore snapshot if maunal snaps are present
    Test Case:
    http://taftm.lmera.ericsson.se/#tm/viewTC/15645/version/1

    :Jira             Story TORF-101576
    :Requirement      ID: TORF-101576
    :Title:           Delete snapshots with manual snaps
    :PreCondition:    a ENM deployment has been initially installed
    :TestStep:        1: Create a snapshot through LITP
                      2: create a snapshot through navisec
                      3: delete snapshot through LITP
                      4: check plan successful
                      5: check if snapshot(1) is removed
                      6: check if navisec snapshot (2) still exists
                      7: tearDown remove navisec snapshot

    """
    def setUp(self):
        super(TestCase, self).setUp()
        self.created_manual_snapshots = []

    def _test(self):
        l1a = self.navi_get_snapshots()
        l1 = ListOfSnaps(self, l1a)
        l2a = self.get_model_snapshots()
        l2 = ListOfSnaps(self, l2a)

        #
    def test(self):
        # get all existing snaps previous to the test
        obj_previous_snaps = ListOfSnaps(self, self.navi_get_snapshots())
        self._logger.debug("Found {n} snaps in 251 before executing the test".format(
            n=len(obj_previous_snaps)))
        for snap in obj_previous_snaps:
            self._logger.debug(str(snap))

        # print "-"*80
        # print "LITP Snapshots : "
        # print "-"*80
        # # import pdb; pdb.set_trace()
        # litp_snaps = self.litp_client.get_children('/snapshots')
        # for litp_snap in litp_snaps:
        #     print litp_snap

        snaps = self.litp_client.get('/snapshots').children
        for snap in snaps:
            if snap.id == self.snap:
                raise Exception("Snapshot '%s' already exists" % self.snap)

        self._logger.info("creating snapshots through LITP")
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

        obj_model_snaps = ListOfSnaps(self, model_snaps)
        self.assertTrue(self.verify_snapshot_creation(
            san_snaps, model_snaps))

        # Create manual snapshots and keep record of wich have been added
        for model_snap in obj_model_snaps:
            ret = self.navi_create_snapshot(model_snap.id,
                'manual_'+model_snap.name)
            if ret.retcode == 0:
                model_snap.name = 'manual_'+model_snap.name
                self.created_manual_snapshots.append(model_snap)
        self.assertTrue(len(self.created_manual_snapshots)>0)

        # Remove the snaps using LITP
        self._logger.info("removing snapshot with litp")
        self.litp_client.remove_snapshot(self.snap)
        plan = self.litp_client.wait_plan_completion()
        self.assertEqual(plan.properties['state'], 'successful')

        # check that the snapshot was removed from the model
        snap = self.litp_client.get('/snapshots/%s' % self.snap)
        self.assertFalse(snap)

        # get all the snapshots that still remains in the SAN
        obj_all_remaining_snaps = ListOfSnaps(self, self.navi_get_snapshots())
        # it should be the previous snaps + the manual snaps
        self.assertEqual(len(obj_all_remaining_snaps),
            len(obj_previous_snaps)+len(self.created_manual_snapshots))
        for previous_snap in obj_previous_snaps:
            self.assertTrue(previous_snap in obj_all_remaining_snaps)
        for manual_snap in self.created_manual_snapshots:
            self.assertTrue(manual_snap in obj_all_remaining_snaps)

        self._logger.debug("The following manual snapshots have been created :")
        for manual_snap in self.created_manual_snapshots:
            self._logger.debug(str(manual_snap))


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

        self._logger.info('Teardown: removing remaining LITP snaps')
        # see if any test snap is in the model
        snaps = self.litp_client.get("/snapshots").children
        if snaps:
                self._logger.debug(
                    "removing snapshot {s} with litp".format(s=self.snap))
                self.litp_client.remove_snapshot(self.snap)
                plan = self.litp_client.wait_plan_completion()
                self.assertEqual(plan.properties['state'], 'successful')

        self._logger.info('Teardown: removing remaining LITP snaps')
        # Remove the snaps on the LUNS on the SAN
        all_snaps  = self.navi_get_snapshots()
        model_snaps = self.get_model_snapshots()
        filtered_snaps = self.filter_snapshot(all_snaps, model_snaps)
        for snap in filtered_snaps:
            if snap:
                print "removing snapshot with navisec"
                self.navi_delete_snapshot(snap["Name"])

        # remove the previously manually created snaps
        for snap in self.created_manual_snapshots:
            self.navi_delete_snapshot(snap.name)



if __name__ == '__main__':
    TestCase().run_test()
