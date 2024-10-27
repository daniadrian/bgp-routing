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
        
        config_path = "/home/USER/bgp-routing-pre-policy/bgp-routing/frr-config/%(name)s"
        privateDirs = [('/var/log'),
                      ('/etc/frr', config_path),
                      ('/var/run'),
                      '/var/mn']

        # AS1 Routers
        R11 = self.addNode("R11", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R12 = self.addNode("R12", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R13 = self.addNode("R13", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R14 = self.addNode("R14", cls=LinuxRouter, ip=None, privateDirs=privateDirs)

        # AS2 Routers
        R21 = self.addNode("R21", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R22 = self.addNode("R22", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R23 = self.addNode("R23", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R24 = self.addNode("R24", cls=LinuxRouter, ip=None, privateDirs=privateDirs)

        # # AS3 Routers
        R31 = self.addNode("R31", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R32 = self.addNode("R32", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R33 = self.addNode("R33", cls=LinuxRouter, ip=None, privateDirs=privateDirs)
        R34 = self.addNode("R34", cls=LinuxRouter, ip=None, privateDirs=privateDirs)

        # # Switch
        S11 = self.addSwitch("S11", inNamespace=True)
        S22 = self.addSwitch("S22", inNamespace=True)
        S33 = self.addSwitch("S33", inNamespace=True)

        # Host
        C11= self.addHost('C11', ip="172.16.1.2/24", defaultRoute="via 172.16.1.1")
        C22= self.addHost('C22', ip="172.17.1.2/24", defaultRoute="via 172.17.1.1")
        C33= self.addHost('C33', ip="172.18.1.2/24", defaultRoute="via 172.18.1.1")

        # Internal links for AS1 (iBGP full mesh)
        self.addLink(R11, R12, intfName1="R11-eth0", intfName2="R12-eth0")
        self.addLink(R11, R13, intfName1="R11-eth1", intfName2="R13-eth0")
        self.addLink(R12, R14, intfName1="R12-eth1", intfName2="R14-eth0")
        self.addLink(R13, R14, intfName1="R13-eth1", intfName2="R14-eth1")

    #     # Internal links for AS2 (iBGP full mesh)
        self.addLink(R21, R22, intfName1="R21-eth0", intfName2="R22-eth0")
        self.addLink(R21, R23, intfName1="R21-eth1", intfName2="R23-eth0")
        self.addLink(R22, R24, intfName1="R22-eth1", intfName2="R24-eth0")
        self.addLink(R23, R24, intfName1="R23-eth1", intfName2="R24-eth1")

    #     # Internal links for AS3 (iBGP full mesh)
        self.addLink(R31, R32, intfName1="R31-eth0", intfName2="R32-eth0")
        self.addLink(R31, R33, intfName1="R31-eth1", intfName2="R33-eth0")
        self.addLink(R32, R34, intfName1="R32-eth1", intfName2="R34-eth0")
        self.addLink(R33, R34, intfName1="R33-eth1", intfName2="R34-eth1")

        # # eBGP links between ASes
        self.addLink(R14, R22, intfName1="R14-eth2", intfName2="R22-eth2")
        self.addLink(R11, R31, intfName1="R11-eth2", intfName2="R31-eth2")
        self.addLink(R23, R34, intfName1="R23-eth2", intfName2="R34-eth2")

        self.addLink(S11, R12, intfName2="R12-eth2")
        self.addLink(S11, C11)

        self.addLink(S22, R21, intfName2="R21-eth2")
        self.addLink(S22, C22)

        self.addLink(S33, R33, intfName2="R33-eth2")
        self.addLink(S33, C33)

        if flags.generateConfig or not Path.exists(Path(config_path % {"name": ""})):
            print("Generating configuration files...")
            for n in self.nodes():
                if "cls" in self.nodeInfo(n):
                    node_info = self.nodeInfo(n)
                    if node_info["cls"].__name__ == "LinuxRouter":
                        self.generate_config(n, config_path)

        super().build(*args, **kwargs)

#     def add_bgp_configuration(self, config_file, router_name):
#         """Add BGP configuration based on router name"""
#         as_number = int(router_name[1])  # Extract AS number from router name
#         with open(config_file, 'a') as f:
#             f.write(f"""
# router bgp {64500 + as_number}
#  bgp router-id {router_name}
#  no bgp ebgp-requires-policy
# """)
#             # Add iBGP neighbors based on AS
#             if router_name[2] in ['a', 'b', 'c', 'd']:
#                 for peer in ['a', 'b', 'c', 'd']:
#                     if peer != router_name[2]:
#                         f.write(f" neighbor R{as_number}{peer} remote-as {64500 + as_number}\n")
            
#             # Add eBGP neighbors
#             if router_name == "R13":
#                 f.write(" neighbor R21 remote-as 64502\n")
#             elif router_name == "R21":
#                 f.write(" neighbor R13 remote-as 64501\n")
#             elif router_name == "R23":
#                 f.write(" neighbor R31 remote-as 64503\n")
#             elif router_name == "R31":
#                 f.write(" neighbor R23 remote-as 64502\n")

print("Starting BGP topology...")
net = Mininet(topo=BGPTopo(), switch=LinuxBridge, controller=None)

try:
    net.start()
    CLI(net)
finally:
    print("Stopping network...")
    net.stop()