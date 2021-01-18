from scapy.all import AsyncSniffer
from scapy.config import conf
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether


from .util import BROADCAST_MAC, ReservationPacket, Reservation


class Listener:
    """
    A wrapper for receiving and answering stream advertisements in a TSN
    network.

    Attributes
    ----------
    interface
        The system's interface which is connected to the TSN network
    ip
        The IPv4 address used as the source in answers
    mac
        The MAC address used as the source in answers
    """
    def __init__(self, interface, ip, mac):
        self.interface = interface
        self.ip = ip
        self.mac = mac
        self.socket = conf.L2socket(iface=self.interface)
        self.sniffer = AsyncSniffer(
            iface=self.interface,
            filter="inbound and dst portrange 999-1000",
            prn=lambda p: self._handle_packet(p)
        )
        self.answered_advertisements = set()
        self.subscribed_streams = set()
        self.sniffer.start()

    def _handle_packet(self, raw_packet):
        try:
            packet = ReservationPacket(raw_packet[3])
            if packet.status == 0:
                self._handle_advertisement(Reservation(packet))
            elif packet.status == 2:
                self._handle_acknowledgement(Reservation(packet))
            else:
                return
        except Exception:
            print("Received a non-advertisement packet")
            return

    def _handle_advertisement(self, advertisement: Reservation):
        approval = advertisement.to_subscription_packet(self.ip)
        self.socket.send(
            Ether(src=self.mac, dst=BROADCAST_MAC) /
            IP(src=self.ip, dst=advertisement.src_ip) /
            UDP(dport=1000, sport=1000) /
            approval
        )
        self.answered_advertisements.add(advertisement)
        print(
            f"Answered advertisement for {advertisement.signature()} "
            f"with accMaxD of {advertisement.acc_max_delay}"
        )

    def _handle_acknowledgement(self, acknowledgement: Reservation):
        if acknowledgement in self.answered_advertisements and \
           acknowledgement.dst_ip == self.ip:
            self.subscribed_streams.add(acknowledgement)
            print(
                f"Receieved acknowledgement for {acknowledgement.signature()} "
                f"with accMaxD of {acknowledgement.acc_max_delay}"
            )
