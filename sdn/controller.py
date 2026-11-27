import json

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import udp
from ryu.lib.packet import tcp
from ryu.lib.packet import icmp
from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import route
from ryu.app.wsgi import WSGIApplication
from ryu.lib import dpid as dpid_lib
from slice import Slice

simple_switch_instance_name = 'simple_switch_api_app'


class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {'wsgi': WSGIApplication}# restAPI config, wsgi is used for the http

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)

        wsgi = kwargs['wsgi']
        wsgi.register(Controller, {simple_switch_instance_name: self})

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
        #slice3: h3 - s2 - s3 - h4 (uses some ports as slice2)
        #for test: pingall

        slice1 = Slice(
            "slice1",  
            {   1: {4: 3, 3: 4},
                5: {1: 3, 3: 1}},
            {"00:00:00:00:00:01", "00:00:00:00:00:07"},
            True
        )

        slice2 = Slice(
            "slice2",  
            {   2: {3: 2, 2: 3},
                3: {1: 2, 2: 1},
                4: {2: 4, 4: 2}},
            {"00:00:00:00:00:02", "00:00:00:00:00:06"},
            True
        )

        slice3 = Slice(
            "slice3",  
            {   2: {4: 2, 2: 4},
                3: {1: 4, 4: 1}},
            {"00:00:00:00:00:03", "00:00:00:00:00:04"},
            True
        )
        
        self.slices = {
            "slice1": slice1,
            "slice2": slice2,
            "slice3": slice3
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

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP: # ignore lldp packet
            return

        src = eth.src
        dst = eth.dst

        for sl in self.slices.values():

            if not sl.active:  #skip inactive slices
                continue

            if dpid not in sl.ports:  #is the switch in to the slice
                continue

            if in_port not in sl.ports[dpid]:  # is the input port of the switch in the slice
                continue

            if src in sl.macs and dst in sl.macs:
                #basic topology slicing
                out_port = sl.ports[dpid][in_port]# which port should the packtet go out
                actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]# send the package
                match = datapath.ofproto_parser.OFPMatch(#switch rule
                    in_port=in_port,
                    eth_src=src,
                    eth_dst=dst #Distinguish flows using the same links and hosts
                )

                self.add_flow(datapath, 1, match, actions)
                self._send_package(msg, datapath, in_port, actions)



url = '/controller/slice/'
class Controller(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(Controller, self).__init__(req, link, data, **config)
        self.simple_switch_app = data[simple_switch_instance_name]

    #for test: curl -X PUT 'http://127.0.0.1:8080/controller/slice/slice2?active=true'
    @route('slice_on_off', url + "{sliceName}", methods=['PUT'])
    def sliceOnOff(self, req, **kwargs):

        simple_switch = self.simple_switch_app
        sliceName = kwargs['sliceName']
        active = req.GET.get('active')
        
        if sliceName not in simple_switch.slices:
            return Response(status=404)

        if active == 'true':
            active = True
        elif active == 'false':
            active = False
        else:
            return Response(status=400)

        try:
            sl = simple_switch.slices[sliceName]
            sl.active = active
            body = json.dumps({"name": sliceName, "active": sl.active})
            return Response(content_type='application/json', body=body)
        except Exception as e:
            return Response(status=500)
