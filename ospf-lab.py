#!/usr/bin/env python3

from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call
import shutil
import time
from pathlib import Path
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.nodelib import LinuxBridge
import argparse

class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        self.cmd('/usr/lib/frr/zebra -A 127.0.0.1 -s 90000000 -f /etc/frr/frr.conf -d')
        self.cmd('/usr/lib/frr/staticd -A 127.0.0.1 -f /etc/frr/frr.conf -d')
        self.cmd('/usr/lib/frr/bgpd -A 127.0.0.1 -f /etc/frr/frr.conf -d')
        self.cmd('/usr/lib/frr/ospfd -A 127.0.0.1 -f /etc/frr/frr.conf -d')


    def terminate(self):
        self.cmd('killall zebra staticd bgpd')
        super(LinuxRouter, self).terminate()
    
    def start(self):
        return

class BGPTopo(Topo):
    def generate_config(self, router_name, path):
        """Generate config for each router"""
        router = {"name": router_name}
        path = path % router
        template_path = Path("Template/router")
        Path(path).mkdir(exist_ok=True, parents=True)

        for file in template_path.iterdir():
            shutil.copy(file, path)
        
        self.replace_hostname(path+"/frr.conf", "dummy", router_name)
        self.replace_hostname(path+"/vtysh.conf", "dummy", router_name)
        
        # Add BGP configuration based on router name/AS
        self.add_bgp_configuration(path+"/frr.conf", router_name)

    def replace_hostname(self, filepath, toReplace, replacement):
        with open(filepath, 'r') as f:
            content = f.readlines()
            for linenum in range(len(content)):
                if content[linenum] == "hostname "+toReplace+"\n":
                    content[linenum] = "hostname "+ replacement+"\n"
        with open(filepath, "w") as f:
            f.writelines(content)
    
    def parse_argument(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-g", "--generateConfig", 
                          help="Generate router config files",
                          action="store_true")
        parser.add_argument("-v", "--verbose", 
                          help="Print detailed logs",
                          action="store_true")
        return parser.parse_args()

    def build(self, *args, **kwargs):
        flags = self.parse_argument()
        if flags.verbose:
            setLogLevel('info')
        
        config_path = "/home/USER/bgp-routing/frr-config/%(name)s"
        privateDirs = [('/var/log'),
                      ('/etc/frr', config_path),
                      ('/var/run'),
                      '/var/mn']

        # AS1 Routers
        R1a = self.addNode("R1a", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R1b = self.addNode("R1b", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R1c = self.addNode("R1c", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R1d = self.addNode("R1d", cls=LinuxRouter, ip=None, privateDirs=privateDirs)

        # AS2 Routers
        R2a = self.addNode("R2a", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R2b = self.addNode("R2b", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R2c = self.addNode("R2c", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R2d = self.addNode("R2d", cls=LinuxRouter, ip=None, privateDirs=privateDirs)

        # # AS3 Routers
        R3a = self.addNode("R3a", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R3b = self.addNode("R3b", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R3c = self.addNode("R3c", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R3d = self.addNode("R3d", cls=LinuxRouter, ip=None, privateDirs=privateDirs)

        # Internal links for AS1 (iBGP full mesh)
        self.addLink(R1a, R1b, intfName1="R1a-eth0", intfName2="R1b-eth0")
        self.addLink(R1a, R1c, intfName1="R1a-eth1", intfName2="R1c-eth0")
        # self.addLink(R1a, R1d, intfName1="R1a-eth1", intfName2="R1d-eth0")
        # self.addLink(R1b, R1c, intfName1="R1b-eth1", intfName2="R1c-eth1")
        self.addLink(R1b, R1d, intfName1="R1b-eth1", intfName2="R1d-eth0")
        self.addLink(R1c, R1d, intfName1="R1c-eth1", intfName2="R1d-eth1")

    #     # Internal links for AS2 (iBGP full mesh)
        self.addLink(R2a, R2b, intfName1="R2a-eth0", intfName2="R2b-eth0")
        self.addLink(R2a, R2c, intfName1="R2a-eth1", intfName2="R2c-eth0")
    #   #  self.addLink(R2a, R2d, intfName1="R2a-eth1", intfName2="R2d-eth0")
    #   #  self.addLink(R2b, R2c, intfName1="R2b-eth1", intfName2="R2c-eth1")
        self.addLink(R2b, R2d, intfName1="R2b-eth1", intfName2="R2d-eth0")
        self.addLink(R2c, R2d, intfName1="R2c-eth1", intfName2="R2d-eth1")

    #     # Internal links for AS3 (iBGP full mesh)
        self.addLink(R3a, R3b, intfName1="R3a-eth0", intfName2="R3b-eth0")
        self.addLink(R3a, R3c, intfName1="R3a-eth1", intfName2="R3c-eth0")
    #   #  self.addLink(R3a, R3d, intfName1="R3a-eth1", intfName2="R3d-eth0")
    #   #  self.addLink(R3b, R3c, intfName1="R3b-eth1", intfName2="R3c-eth1")
        self.addLink(R3b, R3d, intfName1="R3b-eth1", intfName2="R3d-eth0")
        self.addLink(R3c, R3d, intfName1="R3c-eth1", intfName2="R3d-eth1")

        # # eBGP links between ASes
        # self.addLink(R1c, R2a, intfName1="R1c-eth3", intfName2="R2a-eth3")  # AS1 - AS2
        # self.addLink(R2c, R3a, intfName1="R2c-eth3", intfName2="R3a-eth3")  # AS2 - AS3

        if flags.generateConfig or not Path.exists(Path(config_path % {"name": ""})):
            print("Generating configuration files...")
            for n in self.nodes():
                if "cls" in self.nodeInfo(n):
                    node_info = self.nodeInfo(n)
                    if node_info["cls"].__name__ == "LinuxRouter":
                        self.generate_config(n, config_path)

        super().build(*args, **kwargs)

    def add_bgp_configuration(self, config_file, router_name):
        """Add BGP configuration based on router name"""
        as_number = int(router_name[1])  # Extract AS number from router name
        with open(config_file, 'a') as f:
            f.write(f"""
router bgp {64500 + as_number}
 bgp router-id {router_name}
 no bgp ebgp-requires-policy
""")
            # Add iBGP neighbors based on AS
            if router_name[2] in ['a', 'b', 'c', 'd']:
                for peer in ['a', 'b', 'c', 'd']:
                    if peer != router_name[2]:
                        f.write(f" neighbor R{as_number}{peer} remote-as {64500 + as_number}\n")
            
            # Add eBGP neighbors
            if router_name == "R1c":
                f.write(" neighbor R2a remote-as 64502\n")
            elif router_name == "R2a":
                f.write(" neighbor R1c remote-as 64501\n")
            elif router_name == "R2c":
                f.write(" neighbor R3a remote-as 64503\n")
            elif router_name == "R3a":
                f.write(" neighbor R2c remote-as 64502\n")

print("Starting BGP topology...")
net = Mininet(topo=BGPTopo(), switch=LinuxBridge, controller=None)

try:
    net.start()
    CLI(net)
finally:
    print("Stopping network...")
    net.stop()