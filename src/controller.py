from telnetlib import Telnet

from ryu.base import app_manager
from ryu.lib.packet import packet
from ryu.controller import ofp_event
from ryu.controller.controller import Datapath
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls,\
    CONFIG_DISPATCHER
from ryu.lib.packet.packet import Packet
from ryu.ofproto.ofproto_v1_0 import OFPFC_DELETE, OFPFC_ADD, OFP_NO_BUFFER, \
    OFPP_ALL, OFP_DEFAULT_PRIORITY, OFPP_CONTROLLER, OFPFW_ALL, OFPP_NONE, OFPP_FLOOD
from ryu.ofproto.ofproto_v1_0_parser import OFPPacketIn, OFPPacketOut, \
    OFPActionOutput, OFPMatch, OFPFlowMod
from scapy.compat import raw

from reservation_interfaces.util import Reservation, ReservationPacket, \
    round_up

# The network mask applied to the QoS Flow List entries
# Must be 0.0.0.0 to match exact addresses
NETWORK_MASK = '0.0.0.0'

SWITCH_IP_ADDRESS = '192.168.179.2'
SWITCH_USERNAME = 'operator'
QOS_FLOW_LIST_NAME = 'TSN'

# The maximum number of hops in a network a stream can pass
MAX_HOPS_IN_NETWORK = 2

# The delay guarantees available for each traffic class
CLASS_DELAY_MAP = {
    7: 500,
    6: 1000,
    5: 2000,
    4: 5000
}

# Dict of all advertised Streams
ADVERTISED_STREAMS = {}
SUBSCRIBED_STREAMS = {x: set() for x in range(49)}
SUBSCRIPTION_WC_DELAYS = {}

# Link Speed in Bit/s
LINK_SPEED = 100000000


class SwitchInterface:
    """ This class allows the abstract deployment of QoS-Filtering rules """
    READS_PER_COMMAND = 3

    def __init__(self):
        self.tn = Telnet(SWITCH_IP_ADDRESS)
        self.connected = False
        self.sequence_no = 1

    def connect(self):
        """ Sets up the switch so that all ports belonging to VLAN 1 have the
        TSN Flow List applied to them and adds the default filter to match all
        non real-time traffic
        """
        if not self.connected:
            self.tn.read_until(b'login: ')
            self._write_command(SWITCH_USERNAME)
            self._write_command('enable')
            self._write_command('config')
            self._write_command(f'no ip qos-flow-list {QOS_FLOW_LIST_NAME}')
            self._write_command(f'ip qos-flow-list {QOS_FLOW_LIST_NAME}')
            self._write_command('exit')
            self._write_command('interface vlan 1')
            self._write_command(f'ip qos-flow-group {QOS_FLOW_LIST_NAME} in')
            self._write_command('exit')
            self._write_command(f'ip qos-flow-list {QOS_FLOW_LIST_NAME}')
            self.add_default_filter()
            self.connected = True

    def add_tsn_stream(self, subscription: Reservation):
        """ Adds a QoS Flow List entry for a given subscription

        Parameters
        ----------
        subscription: Reservation
            The subscription that should be added to the TSN QoS Flow List
        """
        # Convert the raw burst rate from the subscription to a valid bandwidth
        # value that is accepted by the switch
        burst_rate = get_best_possible_burst_rate(subscription.burst_rate)

        command = f'{self.sequence_no} qos udp '\
            f'{subscription.src_ip} {NETWORK_MASK} ' \
            f'eq {subscription.src_port} ' \
            f'{subscription.dst_ip} {NETWORK_MASK} ' \
            f'eq {subscription.dst_port} ' \
            f'action cos {subscription.priority} ' \
            f'max-rate {burst_rate} max-rate-burst 32'
        self._write_command(command)
        self.sequence_no += 1

    def add_default_filter(self):
        """ Add a flow that matches all traffic not matched by any real-time
        flows and sets their traffic class to 0
        """
        # Set the ID to 100000 since flows are matched in ascending order of ID
        # and this should only match unmatched streams
        command = '100000 qos ip any any action cos 0'
        self._write_command(command)

    def _write_command(self, command: str):
        """ Executes a single given command.

        Parameters
        ----------
        command: str
            A single command without newlines or other controll characters
        """
        # Append newline and carriage return characters to the command
        command += '\r\n'

        # Send the command
        command = command.encode('utf-8')
        self.tn.write(command)

        # Read until all returned messages are processed
        for _ in range(0, self.READS_PER_COMMAND):
            self.tn.read_very_eager()


switch_interface = SwitchInterface()


def in_bandwidth_check(new_stream, port):
    used_bandwidth = new_stream.burst_rate
    for streams in SUBSCRIBED_STREAMS.values():
        for (stream, _) in streams:
            advert = ADVERTISED_STREAMS[stream]
            if advert['in_port'] == port:
                used_bandwidth += advert['advertisement'].burst_rate
                if used_bandwidth > LINK_SPEED:
                    return False
    return True


def out_bandwidth_check(new_stream, port):
    if port not in SUBSCRIBED_STREAMS:
        return True

    used_bandwidth = new_stream.burst_rate
    for (stream, _) in SUBSCRIBED_STREAMS[port]:
        used_bandwidth += stream.burst_rate
        if used_bandwidth > LINK_SPEED:
            return False
    return True


def get_best_possible_burst_rate(burst_rate: int):
    """ Matches a given burst rate to the closest value technically possible.
    This is necessary because the used NEC PF5420 switch can only limit
    bandwidths from 64kBps up to 960kBps in 64kBps steps or from 1MBps on
    in 0.1MBps steps

    Parameters
    ----------
    burst_rate: int
        The raw burst rate e.g. as provided by a stream advertisement

    Returns
    -------
    possible_burst_rate: int
        The closest burst rate equal or higher than the given one, wich is
        technically possible
     """
    if burst_rate <= 960000:
        factor = round_up(burst_rate / 64000)
        return int(factor * 64000)
    elif burst_rate <= 1000000:
        return int(1000000)
    else:
        factor = round_up(burst_rate / 100000)
        return int(factor * 100000)


def calc_y(stream_x, stream_i):
    advert_i = ADVERTISED_STREAMS[stream_x]['advertisement']
    advert_x = ADVERTISED_STREAMS[stream_i]['advertisement']

    acc_max_d_x = advert_x.acc_max_delay + CLASS_DELAY_MAP[stream_x.priority]
    acc_min_d_x = advert_i.acc_min_delay

    delta_p_i = CLASS_DELAY_MAP[stream_i.priority]

    tau_x = stream_x.burst_interval

    return round_up((acc_max_d_x - acc_min_d_x + delta_p_i) / tau_x)


def calc_z(stream_x):
    advert_x = ADVERTISED_STREAMS[stream_x]['advertisement']

    acc_max_d_x = advert_x.acc_max_delay + CLASS_DELAY_MAP[stream_x.priority]
    acc_min_d_x = advert_x.acc_min_delay

    tau_x = advert_x.burst_interval

    return round_up((acc_max_d_x - acc_min_d_x) / tau_x)
    

def calculate_as_higher_prio_delay(stream_x: Reservation,
                                   stream_i: Reservation):
    """ Calculate the worst-case delay a stream x may cause for an observed
    stream i of a lower-priority traffic class

    Parameters
    ----------
    stream_x: Reservation
        The higher-priority stream
    stream_i: Reservation
        The observed lower-priority stream

    Returns
    -------
    int
        The maximum delay caused by all of the streams
    """
    y = calc_y(stream_x, stream_i)
    return round_up((y * stream_x.burst_size * 8) / (LINK_SPEED / 1000000))


def calculate_as_equal_prio_delay(stream_x: Reservation):
    """ Calculate the worst-case delay a stream x may cause for any other
    other stream of the same priority

    Parameters
    ----------
    stream_x: Reservation
        The higher-priority stream

    Returns
    -------
    int
        The maximum delay caused by all of the streams
    """
    z = calc_z(stream_x)
    return round_up((z * stream_x.burst_size * 8) / (LINK_SPEED / 1000000))


def get_worst_case_delay(stream_i: Reservation, port):
    """ Calucalate the worst-case delay for an observed stream i caused by all
    streams deployed on the same output-port

    Parameters:
    -----------
    stream_i: Reservation
        The observed stream
    port:
        The port on which the stream may be deployed

    Returns:
    --------
    worst_case_delay: int
        The worst case delay a burst of the stream could experience passing
        through the switch
    """
    worst_case_delay = 0

    # Calculate the delay caused by every stream on port (including i as well)
    for (stream_x, _) in SUBSCRIBED_STREAMS[port].union({(stream_i, None)}):
        if stream_x.priority > stream_i.priority:
            # Add as higher-priority delay
            worst_case_delay += calculate_as_higher_prio_delay(
                stream_x, stream_i
            )
        elif stream_x.priority == stream_i.priority:
            # Add as equal-priority delay
            worst_case_delay += calculate_as_equal_prio_delay(stream_x)
        else:
            continue
    # Add the maximum delay caused by any lower-priority stream
    worst_case_delay += round_up((1530 * 8) / (LINK_SPEED / 1000000))
    return worst_case_delay


def update_worst_case_delays(stream_x: Reservation, port):
    """ Adds to all streams deployed on the given port the respective delay
    caused by the additionally deployed stream x
    
    Parameters
    ----------
    stream_x: Reservation
        The stream to test
    port
        The port on which the stream wold be deployed
    """
    # If no other streams are deployed on the port return True
    if port not in SUBSCRIBED_STREAMS:
        return True
    
    # Precalculate the delay caused by x for any equal-priority streams
    equal_prio_delay = calculate_as_equal_prio_delay(stream_x)

    # Iterate through all traffic classes of streams deployed on the port
    for (stream_i, dst_ip) in SUBSCRIBED_STREAMS[port]:
        # Test for each stream of the traffic class if it exceeds the
        # link-local latency-guarantee
        if stream_i.priority == stream_x.priority:
            # Add the equal priority delay to the current worst-case delay of i
            SUBSCRIPTION_WC_DELAYS[(stream_i, dst_ip)] += equal_prio_delay

        elif stream_i.priority <= stream_x.priority:
            # Calculate the delay caused by x for the lower-priority stream i
            higher_prio_delay = calculate_as_higher_prio_delay(
                stream_x, stream_i)
            # Add the equal priority delay to the current worst-case delay of i
            SUBSCRIPTION_WC_DELAYS[(stream_i, dst_ip)] += higher_prio_delay


def test_deployability(stream_x: Reservation, port):
    """ Test for a stream x whether it can be deployed on a given port without
    causing any previously deployed streams to exceed their local delay
    guarantees

    Parameters
    ----------
    stream_x: Reservation
        The stream to test
    port
        The port on which the stream wold be deployed

    Returns
    -------
    boolean
        Whether the new stream can be deployed safely or not
    """
    # If no other streams are deployed on the port return True
    if port not in SUBSCRIBED_STREAMS:
        return True
    
    # Precalculate the delay caused by x for any equal-priority streams
    equal_prio_delay = calculate_as_equal_prio_delay(stream_x)
    # Iterate through all streams deployed on the port
    for (stream_i, dst_ip) in SUBSCRIBED_STREAMS[port]:
        # Test for each stream i if it exceeds the link-local latency-guarantee
        if stream_i.priority == stream_x.priority:
            # Add the equal priority delay to the current worst-case delay of i
            new_wc_delay = SUBSCRIPTION_WC_DELAYS[(stream_i, dst_ip)] + \
                equal_prio_delay
            # Test whether it is still lower than the local delay gurantee 
            if new_wc_delay > CLASS_DELAY_MAP[stream_i.priority]:
                return False

        elif stream_i.priority <= stream_x.priority:
            # Calculate the delay caused by x for the lower-priority stream i
            higher_prio_delay = calculate_as_higher_prio_delay(
                stream_x, stream_i)
            # Add the equal priority delay to the current worst-case delay of i
            new_wc_delay = SUBSCRIPTION_WC_DELAYS[(stream_i, dst_ip)] + \
                higher_prio_delay
            # Test whether it is still lower than the local delay gurantee 
            if new_wc_delay > CLASS_DELAY_MAP[stream_i.priority]:
                return False

    return True


def flood_advertisement(openflow_packet_in: OFPPacketIn,
                        captured_packet: Packet,
                        advertisement: Reservation):
    """ Flood an advertisement to all ports
    Parameters:
    -----------
    openflow_packet_in: OFPPacketIn
        The received OpenFlow message containing the required data
    captured_packet: Packet
        The captured packet containing the Datalink, Network and Transport
        information of the received advertisement
    advertisement: Reservation
        The advertisement extracted from the received data
    """
    # Craft the packet to be flooded
    advertisement_packet = advertisement.to_advertisement_packet()
    datapath = openflow_packet_in.datapath
    modified_request = packet.Packet()
    modified_request.add_protocol(captured_packet.protocols[0])
    modified_request.add_protocol(captured_packet.protocols[1])
    modified_request.add_protocol(captured_packet.protocols[2])
    modified_request.add_protocol(raw(advertisement_packet))
    modified_request.serialize()
    flood = OFPPacketOut(
        datapath=datapath,
        buffer_id=0xffffffff,
        in_port=openflow_packet_in.in_port,
        actions=[OFPActionOutput(OFPP_FLOOD, 0)],
        data=modified_request.data
    )

    # Flood the packet
    datapath.send_msg(flood)


def forward_subscription(subscription: Reservation,
                         openflow_packet_in: OFPPacketIn):
    """ Forward a subscription over the in-port of the advertisement
    Parameters:
    -----------
    subscription: Reservation
        The subscription that should be forwarded
    openflow_packet_in: OFPPacketIn
        The received OpenFlow message containing the required data
    """
    # Craft the OpenFlow message to be sent to the switch
    datapath = openflow_packet_in.datapath
    actions = [
        OFPActionOutput(ADVERTISED_STREAMS[subscription]['in_port'])
    ]
    out = OFPPacketOut(
        datapath=datapath,
        buffer_id=0xffffffff,
        in_port=OFPP_NONE,
        actions=actions,
        data=openflow_packet_in.data
    )

    # Send the message
    datapath.send_msg(out)
    #print(
    #    f"Forwarded approval {subscription.signature()} to port "
    #    f"{ADVERTISED_STREAMS[subscription]['in_port']} with accMaxD of {subscription.acc_max_delay / 1000:.3f}"
    #)


def handle_reservation_frame(openflow_packet_in: OFPPacketIn):
    """ Processes a reservation frame as either a stream advertisement or a
    subscription

    Parameters:
    -----------
    openflow_packet_in: OFPPacketIn
        The received message from the switch
    """
    # Extract the captured packet from the OpenFlow message and gather the
    # contained reservation-information
    captured_packet = packet.Packet(openflow_packet_in.data)
    stream_reservation_packet = ReservationPacket(
        captured_packet.protocols[-1]
    )
    stream_reservation = Reservation(stream_reservation_packet)
    in_port = openflow_packet_in.in_port

    # Process the reservation as an advertisement if its status is 0
    if stream_reservation_packet.status == 0:
        advertisement = stream_reservation

        # Test if an advertisement for the same stream already exists
        if advertisement in ADVERTISED_STREAMS:
            old_advert = ADVERTISED_STREAMS[advertisement]['advertisement']
            # Test if the advertisement's parameters have changed
            if old_advert.stream_hash() == advertisement.stream_hash():
                # If not, flood the modified version saved in the dict
                copy = ADVERTISED_STREAMS[advertisement]['advertisement_update']
                flood_advertisement(
                    openflow_packet_in, captured_packet, copy
                )
                return
            else:
                # If they have changed, remove the advertisement from the dict
                ADVERTISED_STREAMS.pop(advertisement)

        # Test if enough bandwidth is available on the input port
        #if not in_bandwidth_check(advertisement, in_port):
        #    print("Exceeded In-Port Bandwidth limit")
        #    return

        # Test whether the latency-requirement is violated
        new_acc_max_delay = CLASS_DELAY_MAP[advertisement.priority] + \
            advertisement.acc_max_delay
        if new_acc_max_delay > advertisement.req_latency:
            #print(
            #    "Exceeded end-to-end latency requirement of "
            #    f"({advertisement.signature()}) {advertisement.req_latency} "
            #    f"({new_acc_max_delay})"
            #)
            return

        # Copy the advertisement
        advertisement_copy = advertisement.copy()

        # Update the accumulated minimum delay
        advertisement_copy.acc_min_delay = round_up(
            advertisement_copy.acc_min_delay +
            (advertisement_copy.min_frame * 8) / LINK_SPEED
        )

        # Update the accumulated maximum delay
        advertisement_copy.acc_max_delay = round_up(
            advertisement_copy.acc_max_delay +
            CLASS_DELAY_MAP[advertisement_copy.priority]
        )
        
        # Store original and modified advertisement with input port in the dict
        ADVERTISED_STREAMS[advertisement] = {
            'advertisement': advertisement,
            'advertisement_update': advertisement_copy,
            'in_port': in_port
        }

        # Flood the advertisement to all ports
        flood_advertisement(
            openflow_packet_in, captured_packet, advertisement_copy
        )

    # Process the reservation as a subscription if its status is 1
    elif stream_reservation_packet.status == 1:
        subscription = stream_reservation

        # Create an entry in SUBSCRIBED_STREAMS for the output port of the
        # subscription if it does not exist yet
        if in_port not in SUBSCRIBED_STREAMS:
            SUBSCRIBED_STREAMS[in_port] = set()

        # Test if deployment exceeds input-port bandwidth
        #if not in_bandwidth_check(
        #   subscription, ADVERTISED_STREAMS[subscription]['in_port']):
        #    print('Stream subscription would exceed in-port bandwidth')
        #    return

        # Test if deployment exceeds output-port bandwidth
        if not out_bandwidth_check(subscription, in_port):
            print('Stream subscription would exceed out-port bandwidth')
            return

        # Test if deployment would violate any stream's delay guarantee
        deployable = test_deployability(
            subscription, in_port
        )
        if not deployable:
            print('Stream subscription would cause breaking a delay-guarantee')
            return

        # Add the subcsribed stream to the deployed streams on the output-port
        SUBSCRIBED_STREAMS[in_port].add((subscription, subscription.dst_ip))

        # Add an entry for the worst-case delay of the deployed subscription
        SUBSCRIPTION_WC_DELAYS[(subscription, subscription.dst_ip)] = \
            get_worst_case_delay(subscription, in_port)

        # Create the QoS-Filtering rule for the subscribed stream
        switch_interface.add_tsn_stream(subscription)

        # Forward the subscription to over its advertisement's input-port
        print(len(SUBSCRIBED_STREAMS[in_port]))
        forward_subscription(subscription, openflow_packet_in)
        #print(f'Forwared subscription {subscription.signature()}')


def reset_openflow(datapath: Datapath):
    """ Resets the OpenFlow flowtable of the passed datapath-object

    Parameters
    ----------
    datapath: Datapath
        The representation of a physical switch, connected to the controller
    """
    # Delete all existing flows on the switch
    flow_mod_delete = OFPFlowMod(
        match=OFPMatch(OFPFW_ALL),
        datapath=datapath,
        cookie=0,
        command=OFPFC_DELETE,
        idle_timeout=0,
        hard_timeout=0,
        buffer_id=OFP_NO_BUFFER,
        out_port=OFPP_NONE,
    )
    datapath.send_msg(flow_mod_delete)

    # Create a new flow to relay all UDP packets with destination port 1000 to
    # the controller
    flow_mod_add = OFPFlowMod(
        datapath=datapath,
        match=OFPMatch(dl_type=0x0800, nw_proto=0x11, tp_dst=1000),
        cookie=0,
        command=OFPFC_ADD,
        idle_timeout=0,
        hard_timeout=0,
        priority=OFP_DEFAULT_PRIORITY,
        buffer_id=OFP_NO_BUFFER,
        actions=[OFPActionOutput(OFPP_CONTROLLER)]
    )
    datapath.send_msg(flow_mod_add)


class SwitchController(app_manager.RyuApp):
    """ This will be loaded by the RYU
    """
    def __init__(self, *args, **kwargs):
        super(SwitchController, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """ Use one of the setup-messages from the switch on startup to reset
        its Flowtable and QoS-Flows
        """
        datapath = ev.msg.datapath
        reset_openflow(datapath)
        switch_interface.connect()

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        """ Handle a relayed packet.
        """
        openflow_packet_in = event.msg
        # As the switch is configured to only relay reservation-protocol frames
        # they will be handled accordingly
        handle_reservation_frame(openflow_packet_in)
