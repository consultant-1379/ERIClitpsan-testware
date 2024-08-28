#!/usr/bin/env python


"""
DESCRIPTION:
Verify the create snapshot functionality

AGILE:
TORF-93743
"""

from infra_utils.snap_test import SnapTest

class TestCase(SnapTest):

    """
    Test case to verify snapshots exist on SAN after upgrade
    http://taftm.lmera.ericsson.se/#tm/viewTC/infra_tst_snapshots_exist_on_san

    :Jira          Story TORF-93743
    :Requirement   ID: TORF-93743
    :Title:        Check snapshots exist on SAN after upgrade
    :Description:  Positive test to verify that snapshots have been created on
    the VNX for snappable lun-disks after upgrade
    :PreCondition: Snapshots have been created (litp create_snapshot)
    :TestStep:     1: Get all LUNs from the model that should be snapped by the SAN
                   2: Get all snapshots on the SAN
                   3: Verify that for LUN to be snapped by the SAN that a snapshot exists
    """

    def test(self):
        """
        Test case implementation
        """
        self.info('Searching LITP model for luns to be snapped by SAN plugin')
        luns_to_be_snapped = self.get_model_snapshots()
        self.info('Searching for all snaps')
        navi_snaps = self.navi_get_snapshots()
        self.info('Verifying a snap exists for each lun to be snapped by SAN')
        self.assertTrue(self.verify_snapshot_creation(navi_snaps,
                                                      luns_to_be_snapped))


if __name__ == '__main__':
    TestCase().run_test()