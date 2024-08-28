
#!/usr/bin/env python


"""
DESCRIPTION:
verify restore_snapshot fails when one snap has been removed

AGILE: ID: 
TORF-101579
"""

from infra_utils.snap_test import SnapTest
from ptaf.utils.litp_cmd_utils import LitpUtils
from ptaf.utils.litp_utils.api_client import LitpClient
from infra_utils.utils.enm_helpers import Model
from infra_utils.restore_test import RestoreTest
from random import randint


class TestCase(RestoreTest):

    """
    Test case to verify restore_snapshot fails when one snap has been removed.
    http://taftm.lmera.ericsson.se/#tm/viewTC/15652/version/1

    :Jira          Story TORF-101579
    :Requirement   ID: TORF-101579
    :Title:        INFRA: Hooligans Test restore snapshot when one snap is missing.
    :Description:  Attempt to restore snapshot when one of the snaps 
                   has been deleted from the san. Restore should fail.
    :PreCondition: ENM deployed
    :TestStep:     1.Get list of snapable luns
                   2.create snapshot
                       2.1 assert that litp plan succeeded
                   3.Delete one snap using naviseccli
                   4.Try restore snapshot
                       4.1.Assert that litp plan failed
                       4.2.Check that the task failed for Verify Snapshot Exists
    """

    def setUp(self):
        super(TestCase, self).setUp()

    def tearDown(self):
        """
        Clean up after the test case
        """
        super(TestCase, self).tearDown()
        self.remove_snapshots()

    def get_lun_snap_name(self, lun_name):
        snap = '_'.join(['L', lun_name, ''])
        return snap

    def test(self):
        # 1.Get list of snapable luns
        snappable_luns = self.get_model_snapshots()

        # 2.create snapshot
        self._logger.info('Creating snapshot with litp')
        modelitem = self.litp_client.create_snapshot()
        self._logger.info('Waiting for plan to complete')
        plan = self.litp_client.wait_plan_completion()

        # 2.1 assert that litp plan succeeded
        self.assertEqual(plan.properties['state'], "successful")

        # 3.Delete one snap using naviseccli
        random_snappable_lun = randint(0,(len(snappable_luns)-1))
        lun = snappable_luns[random_snappable_lun].properties['lun_name']
        removable_snap = self.get_lun_snap_name(lun)
        self._logger.info('Removing single snap {0}'.format(removable_snap))
        self.navi_delete_snapshot(removable_snap)

        # 4.Try restore snapshot
        self._logger.info('Attempting restore snapshot')
        self.litp_client.restore_snapshot()
        self._logger.info('Waiting for plan to complete')
        plan = self.litp_client.wait_plan_completion()

        # 4.1.Assert that litp plan failed
        self.assertEqual(plan.properties['state'], "failed")

        # 4.2.Check that the task failed for Verify Snapshot Exists
        task_name = 'Verify snapshot exists for LUN {0}'.format(lun)
        task_status = LitpUtils.get_litp_task_status(self, task_name)
        self._logger.info('Task status is: {0}'.format(task_status.lower()))
        self.assertEqual(task_status.lower(), 'failed',
                         'Fail: Verify snapshot exists task did not Fail for any LUN')

if __name__ == '__main__':
    TestCase().run_test()
