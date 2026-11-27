from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)

        #this is not used right now, but we can use it later for the adding of slices
        self.ports = {
            1: {"s2": 1, "s4": 2, "s5": 3, "h1": 4}, #s1
            2: {"s1": 1, "s3": 2, "h2": 3, "h3": 4}, #s2
            3: {"s2": 1, "s4": 2, "s5": 3, "h4": 4}, #s3
            4: {"s1": 1, "s3": 2, "h5": 3, "h6": 4}, #s4
            5: {"s1": 1, "s3": 2, "h7": 3}, #s5
        }

        #slice1: h1 - s1 - s5 - h7 
        #slice2: h2 - s2 - s3 - s4 - h6
        #for test: pingall
        self.slice_to_port = {
            "slice1": {
                1: {4: 3, 3: 4},
                5: {1: 3, 3: 1}
            },
            "slice2": {
                2: {3: 2, 2: 3},
                3: {1: 2, 2: 1},
                4: {2: 4, 4: 2}
            }
        }


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match, instructions=inst
        )
        datapath.send_msg(mod)

    def _send_package(self, msg, datapath, in_port, actions):
        data = None
        ofproto = datapath.ofproto
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match["in_port"]
        dpid = datapath.id
        
        self.logger.info("Switch: %s, Input port: %s", dpid, in_port)

        for slc_ports in self.slice_to_port.values():

            if dpid not in slc_ports:
                continue

            if in_port not in slc_ports[dpid]:
                continue

            #basic topology slicing
            out_port = slc_ports[dpid][in_port]# which port should the packtet go out
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]# send the package
            match = datapath.ofproto_parser.OFPMatch(in_port=in_port)# for all packets

            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)
