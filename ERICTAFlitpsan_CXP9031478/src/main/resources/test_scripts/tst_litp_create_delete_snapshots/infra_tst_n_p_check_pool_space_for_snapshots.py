#!/usr/bin/env python

"""
DESCRIPTION:
Verify the create snapshot functionality when insufficient space in pool for thick and thin LUN deployments
Verify that the thin LUN space calculation works and snapshot is created successfully 

AGILE:
OSS-78423, TORF-101584
"""
from ptaf.utils.litp_cmd_utils import LitpUtils
from infra_utils.snap_test import SnapTest
from ptaf.utils.litp_utils.api_client import LitpException
from time import sleep


class TestCase(SnapTest):
    """
    Test case to verify the create_snapshot functionality in the plugin
    http://taftm.lmera.ericsson.se/#tm/viewTC/infra_tst_n_p_check_pool_space_for_snapshots

    :Jira          Story OSS-78423
                   Refactor story TORF-101584
    :Requirement   ID: OSS-78423
    :Title:        Check pool space for create_snapshot for Thin and Thick LUN deployments
    :Description:  Negative test SAN plugin does not create any snapshots on
                   the SAN. Litp create_snapshot plan fails.
                   For thin LUNs, the thin LUN space calculation functionality 
                   is tested. Litp create_snapshot plan succeeds.
    :PreCondition: A cluster is installed with at least one lun-disk on one
                   node. The remaining pool space is insufficient to allow the
                   plugin to create snapshots on the SAN.
                   If it is a thin LUN deployment, test that the thin LUN 
                   calculation method works and a snapshot is created successfully.
    :TestStep:     1: Find all LUNs in the model the san plugin should snap.
                   2: Determine the remaining capacity of the pool.
                   3. Find if this is a thin or thick LUN deployment
                   4. Create a LUN to fill the remaining space.
                   5. Run "litp create_snapshot".
                       5.1 verify check for sufficent pool capacity failed.
                       5.2 verify litp plan fails.
                       5.3 verify no snaps created on the SAN.
                   If thick LUN deployment, test ends here
                   and the tear down method is called.
                   6. If this is a thin LUN deployment, remove test luns that
                      were created in step 3 and any snapshots that may 
                      have been created in step 4.
                   7. Find the total snap size usage by the LUNs on the SAN
                   8. Create thick LUN taking up most of the remaining space 
                      leaving just enough space for snapshot of the thin LUN deployment
                   9. Run Litp command 'litp create_snapshot', to create an upgrade snapshot
                       9.1 assert that litp plan succeeded
    """

    def setUp(self):
        """
        Set up the test case
        """

        super(TestCase, self).setUp()
        self.snapable_luns = []
        self.test_lun_name_l = 'test_lun_oss_78423_l'  # Large test LUN
        self.sanapi_target = self.mws

    def tearDown(self):
        """
        Clean up after the test case
        """

        # Clean down the snap shot and any test luns
        self.remove_snapshot_and_test_luns()

        super(TestCase, self).tearDown()

    def remove_snapshot_and_test_luns(self):
        """
        Remove Litp snapshot and any snapshots which were created on the SAN
        during running of create_snapshot plan.
        Remove test LUNs
        """

        # Destroy the LUN created earlier
        self._logger.info('Cleaning down test LUN {0}'.format(self.test_lun_name_l))
        self.navi_destroy_snaps_and_lun(self.test_lun_name_l)
        # The LUN can take a long time to delete, polling this
        while True:
            self._logger.info('Waiting for lun {0} to be removed'.format(self.test_lun_name_l))
            res = self.navi_get_lun(self.test_lun_name_l)
            if not res:
                break
            sleep(5)

        # Remove Litp snapshot
        try :
            self._logger.info('Cleaning down any snap shots that might have been created')
            self.litp_client.remove_snapshot('snapshot')
            self._logger.info('Waiting for plan to complete')
            self.litp_client.wait_plan_completion()
        except LitpException:
            self._logger.info("No Snap Shot To remove")

    def create_thick_lun(self, space_for_thick_lun, pool_name):
        self._logger.info('Creating thick LUN')
        lun_size = int(int(space_for_thick_lun) * .97)
        cmd = self.navi_create_lun(pool_name=pool_name,
                                   lun_name=self.test_lun_name_l,
                                   lun_type='nonThin',
                                   capacity=lun_size,
                                   units='gb',
                                   storage_processor='a',
                                   ignore_thresholds=True)
        self.assertEqual(cmd.retcode, 0,
                        'Fail: create test LUN failed')

    def get_thin_lun_snap_size(self, luns_in_model):
        self._logger.info('Calculating total size of thin LUN snapshots')
        total_snap_size = 0
        for lun in luns_in_model.values():
            if (lun.properties['external_snap'] == 'false' and
                lun.properties['snap_size'] != '0'):
                    snap_size=int(lun.properties['snap_size'])
                    lun_information = self.navi_get_lun(lun.properties['lun_name'])
                    lun_size=float(lun_information['Consumed Capacity (GBs)'])
                    self._logger.info('LUN name: {0}'.format(lun.properties['lun_name']))
                    self._logger.info('LUN size: {0}'.format(lun_size))
                    lun_snap_size=(lun_size*snap_size)/100
                    self._logger.info('LUN snap size: {0}'.format(lun_snap_size))
                    total_snap_size+=lun_snap_size
        return total_snap_size

    def test(self):
        """
        Run create_snapshot when there is insufficient space remaining in
        the storage pool

        Actions:
            1: Assert that the plan fails and that the SAN plugin does not
               generate any snapshot tasks

        """

        # 1.Select a LUN from the Litp model with properties 'external snap' set to False and 'snap size' > 0
        luns_in_model = self.model.luns

        for lun in luns_in_model.values():
            if (lun.properties['external_snap'] == 'false' and
                lun.properties['snap_size'] != '0' and
                lun.properties['lun_name']  not in self.snapable_luns):
                self.snapable_luns.append(lun.properties['lun_name'])
        self.assertTrue(len(self.snapable_luns) > 0,
                            'Fail: no LUN found for SAN plugin to snap')

        # 2.Find how much unused storage memory is available in the storage pool to which the LUN belongs
        lun_information = self.navi_get_lun(self.snapable_luns[0])
        pool_name = lun_information['Pool Name']
        pool_information = self.navi_get_pool(pool_name)
        pool_free_capacity = float(pool_information['Available Capacity (GBs)'])
        self._logger.info('pool capacity = {0}'.format(pool_free_capacity))

        # 3.Find if thin or thick LUN
        if lun_information['Is Thin LUN'] == "No":
            ThinLun = False
        else:
            ThinLun = True

        # 4. Create a large test LUN to use remaining capacity in the pool
        self.create_thick_lun(pool_free_capacity, pool_name)

        # Pause to allow available pool space to update
        sleep(15)

        # 5.Run Litp command 'litp create_snapshot', to create an upgrade snapshot
        modelitem = self.litp_client.create_snapshot()

        self._logger.info('Waiting for plan to complete')
        plan = self.litp_client.wait_plan_completion()

        # 5.1 assert that litp plan failed
        self.assertEqual(plan.properties['state'], "failed")

        # 5.2check that the san plugin task Pool Capacity Check failed
        if ThinLun:
            task_name = "Checking Pool reserve and LUN consumed"
        else:
            task_name = "Checking Pool Snapshot Reserve"
        print "TASK NAME = ", task_name

        task_status = LitpUtils.get_litp_task_status(self, task_name)
        self._logger.info('Task status is: {0}'.format(task_status.lower()))
        self.assertEqual(task_status.lower(), 'failed',
                         'Fail: Check Pool Snapshot reserve task did not Fail')

        # 5.3 check that no snapshots created on the SAN
        for lun in self.snapable_luns:
            upgrade_snap_name = '_'.join(['L', lun, ''])
            self._logger.info('Upgrade snap name =  {0}'.format(upgrade_snap_name))
            cmd = self.sanapi_get_snapshot(upgrade_snap_name)
            self.assertFalse(cmd,
                            'Fail: Snapshot found on the SAN')

        # Run test to verify that the thin LUN space calculation works
        if ThinLun:
            # 6.Remove snapshot and test luns that were created in the previous test
            self.remove_snapshot_and_test_luns()
            self._logger.info('Thin LUN deployment detected')

            # 7.Find the total snap size usage by the LUNs on the SAN
            total_snap_size = self.get_thin_lun_snap_size(luns_in_model)
            self._logger.info('Space needed on the storage pool to create snapshot = {0}'
                              .format(total_snap_size))
            space_for_thick_lun = pool_free_capacity - total_snap_size

            # 8.Create thick LUN taking up most of the remaining space leaving just enough space for snapshot of the thin LUN deployment
            self.create_thick_lun(space_for_thick_lun, pool_name)

            # Pause to allow available pool space to update
            sleep(15)

            # 9.Run Litp command 'litp create_snapshot', to create an upgrade snapshot
            modelitem = self.litp_client.create_snapshot()
            self._logger.info('Waiting for plan to complete')
            plan = self.litp_client.wait_plan_completion()

            # 9.1 assert that litp plan succeeded
            self.assertEqual(plan.properties['state'], "successful")

if __name__ == '__main__':
    TestCase().run_test()
