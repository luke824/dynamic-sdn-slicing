#!/usr/bin/python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink


class NetworkSlicingTopo(Topo):
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        # Create template host, switch, and link
        host_config = dict(inNamespace=True)
        config1 = dict(bw=10)
        config2 = dict(bw=5)
        host_link_config = dict()

        # Network Topology
        #
        #         +---------------------------------------+
        #         |                                       |
        #         |       h2     h3                       |
        #         |         \   /                         |
        # h1 ---- s1 ------- s2 -------+                  |
        #         |                    |                  |
        #         |                    s3 --------------- s5 ---- h7
        #         |                    | \
        #         +--------- s4 -------+  h4
        #                   /  \
        #                  h6   h5

        # Create switch nodes
        for i in range(5):
            sconfig = {"dpid": "%016x" % (i + 1)}
            self.addSwitch("s%d" % (i + 1), **sconfig)

        # Create host nodes
        for i in range(7):
            self.addHost("h%d" % (i + 1), **host_config)

        # Add switch links
        self.addLink("s1", "s2", **config1)
        self.addLink("s1", "s4", **config1)
        self.addLink("s1", "s5", **config1)
        self.addLink("s2", "s3", **config2)
        self.addLink("s3", "s4", **config2)
        self.addLink("s3", "s5", **config2)

        # Add host links
        self.addLink("h1", "s1", **host_link_config)

        self.addLink("h2", "s2", **host_link_config)
        self.addLink("h3", "s2", **host_link_config)

        self.addLink("h4", "s3", **host_link_config)

        self.addLink("h5", "s4", **host_link_config)
        self.addLink("h6", "s4", **host_link_config)

        self.addLink("h7", "s5", **host_link_config)


topos = {"networkslicingtopo": (lambda: NetworkSlicingTopo())}

if __name__ == "__main__":
    topo = NetworkSlicingTopo()
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        build=False,
        autoSetMacs=True,
        autoStaticArp=True,
        link=TCLink,
    )
    controller = RemoteController("c1", ip="127.0.0.1", port=6633)
    net.addController(controller)
    net.build()
    net.start()
    CLI(net)
    net.stop()