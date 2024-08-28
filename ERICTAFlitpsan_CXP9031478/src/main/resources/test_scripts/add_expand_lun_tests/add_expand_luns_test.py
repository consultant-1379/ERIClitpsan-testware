from infra_utils.san_test import SanTest
from ptaf.utils.litp_utils.api_client import LitpClient
from ptaf.utils.cmd_utils import CMDUtils
from infra_utils.utils.enm_helpers import Model
from ptaf.utils.litp_cmd_utils import LitpUtils
from infra_utils.utils.san_utils import SanClient
import re
import time


class AddExpandTest(SanTest):

    """
    A generic class with some functionality
    for writing restore snapshot test cases
    """

    def setUp(self):
        """
        SetUp the test case.
        Instantiates a LitpClient object to communicate with LITP.
        """
        super(AddExpandTest, self).setUp()
        self.litp_utils = LitpUtils()
        self.cmd_utils = CMDUtils()
        self.litp_client = LitpClient(host=self.mws['ip'],
            password=self.litp_utils.get_litpadmin_password(self))
        self.model = Model(self.litp_client)
        self.root_user = 'root'
        self.root_pass = self.mws['root_password']
        self.node_user = 'litp-admin'
        self.node_pass = '12shroot'
        self.san_client = SanClient(self.san, navi_target=self.mws)
        self.postfix_lun = 'TORF92038'
        
    def tearDown(self):
        super(AddExpandTest, self).tearDown()
        self.litp_client.remove_plan()

    def prefix(self):
        """
        Creates a time stamp to add to the lun device name
        """
        now = time.localtime()
        prefix = "%s%s%s%s%s" % (now.tm_year, now.tm_yday, now.tm_hour,
                 now.tm_min, now.tm_sec)
        return prefix

    def get_luns_for_expansion(self):
        """
        Gets a list of the current luns for expansion
        excluding vg_root luns
        """
        luns = []

        for node in self.model.nodes.values():
            for vg in node.vgs.values():
                if vg.properties['volume_group_name'] != "vg_root":
                    for lunk in vg.luns:
                        lun = vg.luns[lunk]
                        inherited_path = lun.get_inherited_path(node)
                        luns.append(Obj(nodeId=node._id,
                             lunk=lunk, size=lun.properties['size'],
                             inherited_path=lun.get_inherited_path(node)))
        return luns

    def split_size(self, current_size):
        size = "0"
        type = ""
        m = re.match(r"(?P<numbers>[^a-zA-Z]+)(?P<let>[a-zA-Z]+)",
             current_size)

        if m:
            size = (m.group('numbers'))
            type = (m.group('let'))
            
        return size, type

    def get_new_lun_size(self, current_size):
        """
        Reads the current lun size
        Splits the lun size at the letter
        Based on the letter a value to expand the lun is passed back
        """
        size, type = self.split_size(current_size)
        if type == "G":
            expand_size = 1
        elif type == "M":
            expand_size = 1024
        elif type == "K":
            expand_size = 1048576
        else:
            print "Storage size not recognized: " + type

        new_size = int(size) + expand_size
        total_size = str(new_size) + type
        return total_size
    
    def convert_to_gb(self, current_size):
        size, type = self.split_size(current_size)
        if type == "M":
            size = size / 1024.0
        elif type == "K":
            size = size / 1048576.0
        return size

    def get_luns_for_addition(self):
        """
        Creates a list of new 1G luns with properties
        based on existing luns excluding vg_root
        """
        luns = []
        prefix = self.prefix()
        base = self.postfix_lun
        for node in self.model.nodes.values():
            for vg in node.vgs.values():
                if vg.properties['volume_group_name'] != "vg_root":
                    for lunk in vg.luns:
                        lun = vg.luns[lunk]
                        basepath = lun.get_inherited_path(node) + '_'
                        newpath = ''
                        vg_in = ''
                        for cnt in range(1, 51):
                            newpath = basepath + base + '_' + str(cnt)
                            vg_in = base + '_' + str(cnt)
                            # Rest call to check model for newpath.
                            # Break if it does not exist.
                            check_path = self.litp_client.get(newpath)
                            if not check_path:
                                break

                        # Create the new LUN name using the last element of newpath
                        rep = newpath.split("/")
                        rep = rep[-1]
                        luns.append(Obj(nodeId=node._id,
                             lunk=lunk + '_' + rep,
                             size='1G',
                             storage_container=lun.properties['storage_container'],
                             bootable=lun.properties['bootable'],
                             shared=lun.properties['shared'],
                             name=prefix + lun.properties['name'],
                             external_snap=lun.properties['external_snap'],
                             snap_size=lun.properties['snap_size'],
                             vg_inherited=vg.inherited_path + '/physical_devices/'+ vg_in,
                             path=lun.get_path(node),
                             inherited_path=newpath))
        return luns

    def get_lun_properties(self):
        """
        Gets a list of lun properties
        """
        lun_properties = []

        for node in self.model.nodes.values():
            for vg in node.vgs.values():
                if vg.properties['volume_group_name'] != "vg_root":
                    for lunk in vg.luns:
                        lun = vg.luns[lunk]
                        lun_properties.append({"lun_name" : lunk, "size" : lun.properties['size'], 
                                               "lun_uuid" : lun.properties['uuid'], "path": lun.path})
        return lun_properties

    def verify_luns_on_host(self, luns):
        """
        Verify that new luns can be seen on the host
        """
        for lun in luns:
            node_path = "/".join(lun["path"].split("/")[0:7])
            node = self.litp_client.get(node_path)
            cmd = "ls -l /dev/disk/*/* | grep -i " + lun['lun_uuid'] + " | grep scsi"
            result = self.cmd_utils.run_ssh_command_via_proxy(cmd, self.mws['ip'],
                                    self.root_user, self.root_pass, node.id, 
                                    self.node_user, self.node_pass)
            self.assertTrue(result.stdout)

class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__str__()
