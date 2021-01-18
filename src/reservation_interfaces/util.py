from scapy.fields import ByteEnumField, IntField, ShortField, IPField
from scapy.packet import Packet


BROADCAST_MAC = 'ff:ff:ff:ff:ff:ff'


def round_up(x):
    """ Round a given number to the next higher integer

    Parameters
    ----------
    x
        The number to round up

    Returns
    -------
    int
        Either `int(x) + 1` if `x > int(x)` or `x`
    """
    if int(x) < x:
        return int(x) + 1
    else:
        return int(x)


class ReservationPacket(Packet):
    """ The implementation of the developed model's reservation packet

    Attributes
    ----------
    status : int
        Either 0, indicating an advertisement, or 1, if the packet is a
        subscription
    req_latency : int
        The required maximum end-to-end delay in nanoseconds for single packets
        of the advertised stream
    src_ip
        The advertised stream's source IP address (Talker)
    dst_ip
        In case of a subscription the Listener's IP address, else 0.0.0.0
    src_port : int
        The transport layer source port of the advertised stream
    dst_port : int
        The transport layer destination port of the advertised stream
    min_frame : int
        The size in Byte of the smallest frame included in the advertised
        stream
    max_frame : int
        The size in Byte of the largest frame included in the advertised stream
    burst_size : int
        The size in Byte of the largest amount of data sent at once
        (usually 'max_frame')
    burst_interval : int
        The time window in nanoseconds in which at most 'burst_size' Byte are
        sent
    acc_max_delay : int
        The accumulated maximum delay in nanoseconds the advertisement has
        collected on its route
    acc_min_delay : int
        The accumulated minimum delay in nanoseconds the advertisement has
        collected on its route
     """
    name = "Reservation"
    fields_desc = [
        ByteEnumField('status', 0, {0: "ADVERTISEMENT", 1: "SUBSCRIPTION"}),
        IntField('req_latency', 0),
        IntField('priority', 0),
        IPField('src_ip', '0.0.0.0'),
        IPField('dst_ip', '0.0.0.0'),
        ShortField('src_port', 0),
        ShortField('dst_port', 0),
        IntField('min_frame', 0),
        IntField('max_frame', 0),
        IntField('burst_size', 0),
        IntField('burst_interval', 0),
        IntField('acc_max_delay', 0),
        IntField('acc_min_delay', 0),
    ]


class Reservation:
    """ The abstract representation of a reservation packet

    Attributes
    ----------
    req_latency : int
        The required maximum end-to-end delay in nanoseconds for single packets
        of the advertised stream
    priority: int
        The priority set for the stream by the Talker
    src_ip
        The advertised stream's source IP address (Talker)
    dst_ip
        In case of a subscription the Listener's IP address, else 0.0.0.0
    src_port : int
        The transport layer source port of the advertised stream
    dst_port : int
        The transport layer destination port of the advertised stream
    min_frame : int
        The size in Byte of the smallest frame included in the advertised
        stream
    max_frame : int
        The size in Byte of the largest frame included in the advertised stream
    burst_size : int
        The size in Byte of the largest amount of data sent at once
        (usually `max_frame`)
    burst_interval : int
        The time window in nanoseconds in which at most 'burst_size' Byte are
        sent
    acc_max_delay : int
        The accumulated maximum delay in nanoseconds the advertisement has
        collected on its route
    acc_min_delay : int
        The accumulated minimum delay in nanoseconds the advertisement has
        collected on its route
    """
    def __init__(self, reservation_packet=None, req_latency=None, priority=None,
                 src_ip=None, dst_ip=None, src_port=None, dst_port=None,
                 min_frame=None, max_frame=None, burst_size=None,
                 burst_interval=None, acc_max_delay=None, acc_min_delay=None,
                 **kwargs):
        """ Constructs a new reservation from either an exisiting
        ReservaionPacket object or the Class's attributes
        """

        if reservation_packet and \
           type(reservation_packet) == ReservationPacket:
            self.req_latency = reservation_packet.req_latency
            self.priority = reservation_packet.priority
            self.src_ip = reservation_packet.src_ip
            self.dst_ip = reservation_packet.dst_ip
            self.src_port = reservation_packet.src_port
            self.dst_port = reservation_packet.dst_port
            self.min_frame = reservation_packet.min_frame
            self.max_frame = reservation_packet.max_frame
            self.burst_size = reservation_packet.burst_size
            self.burst_interval = reservation_packet.burst_interval
            self.acc_max_delay = reservation_packet.acc_max_delay
            self.acc_min_delay = reservation_packet.acc_min_delay
        else:
            self.req_latency = req_latency
            self.priority = priority
            self.src_ip = src_ip
            if dst_ip is None:
                self.dst_ip = '0.0.0.0'
            else:
                self.dst_ip = dst_ip
            self.src_port = src_port
            self.dst_port = dst_port
            self.min_frame = min_frame
            self.max_frame = max_frame
            self.burst_size = burst_size
            self.burst_interval = burst_interval
            self.acc_max_delay = acc_max_delay
            self.acc_min_delay = acc_min_delay

        self.burst_rate = round_up(
            self.burst_size * 8 / (self.burst_interval / 10**6)
        )

    def __str__(self):
        return f"Stream Reservation:\n"\
               f"{self.src_ip}:{self.src_port} --> " \
               f"{self.dst_ip}:{self.dst_port}\n" \
               f"{self.min_frame} Byte <= Frame size <= " \
               f"{self.max_frame} Byte\n"\
               f"{self.burst_rate} Bit/s Burst Rate\n"\
               f"{self.acc_min_delay / 1000} ms <= Accumulated Delay <= " \
               f"{self.acc_max_delay / 1000} ms\n"\
               f"Required latency:{self.req_latency / 1000} ms"

    def __hash__(self):
        return hash((
            self.src_ip,
            self.src_port,
            self.dst_port,
        ))

    def stream_hash(self):
        return hash((
            self.req_latency,
            self.priority,
            self.min_frame,
            self.max_frame,
            self.burst_size,
            self.burst_interval,
            self.acc_min_delay,
            self.acc_max_delay
        ))

    def __eq__(self, other):
        """ Test for equality between two Reservations

        Parameters
        ----------
        other : Reservation
            The other reservation to compare `self` to

        Returns
        -------
        Boolean
            `True` if the other reservation has the same `src_ip`, `src_port`
            and `dst_port`
        """
        return type(other) == Reservation and hash(self) == hash(other)

    def copy(self):
        """ Copies the reservation to avoid call-by-referenc proplems when
        `acc_max_delay`/`acc_min_delay` values are changed

        Returns
        -------
        Reservation
            A deep copy of `self`
        """
        return Reservation(
            req_latency=int(self.req_latency),
            priority=int(self.priority),
            src_ip=str(self.src_ip),
            dst_ip=str(self.dst_ip),
            src_port=int(self.src_port),
            dst_port=int(self.dst_port),
            min_frame=int(self.min_frame),
            max_frame=int(self.max_frame),
            burst_size=int(self.burst_size),
            burst_interval=int(self.burst_interval),
            acc_max_delay=int(self.acc_max_delay),
            acc_min_delay=int(self.acc_min_delay)
        )

    def to_advertisement_packet(self):
        """ Create an advertisement packet from `self`

        Returns
        -------
        ReservationPacket
            A reservation packet with `status` of 0 and the reservation's
            specifications
        """
        return ReservationPacket(
            status=0,
            req_latency=self.req_latency,
            priority=self.priority,
            src_ip=self.src_ip,
            dst_ip=self.dst_ip,
            src_port=self.src_port,
            dst_port=self.dst_port,
            min_frame=self.min_frame,
            max_frame=self.max_frame,
            burst_size=self.burst_size,
            burst_interval=self.burst_interval,
            acc_max_delay=self.acc_max_delay,
            acc_min_delay=self.acc_min_delay
        )

    def to_subscription_packet(self, destination_ip):
        """ Create a subscription packet from `self`

        Parameters
        ----------
        destination_ip
            The Listener's IP address to insert into the reservation packet's
            `dst_ip` field

        Returns
        -------
        ReservationPacket
            A reservation packet with `status` of 1 and the reservation's
            specifications
        """
        return ReservationPacket(
            status=1,
            req_latency=self.req_latency,
            priority=self.priority,
            src_ip=self.src_ip,
            dst_ip=destination_ip,
            src_port=self.src_port,
            dst_port=self.dst_port,
            min_frame=self.min_frame,
            max_frame=self.max_frame,
            burst_size=self.burst_size,
            burst_interval=self.burst_interval,
            acc_max_delay=self.acc_max_delay,
            acc_min_delay=self.acc_min_delay
        )

    def to_acknowledgement_packet(self):
        """ Create an acknowledgement packet from `self`

        Returns
        -------
        ReservationPacket
            A reservation packet with `status` of 2 and the reservation's
            specifications
        """
        return ReservationPacket(
            status=2,
            req_latency=self.req_latency,
            priority=self.priority,
            src_ip=self.src_ip,
            dst_ip=self.dst_ip,
            src_port=self.src_port,
            dst_port=self.dst_port,
            min_frame=self.min_frame,
            max_frame=self.max_frame,
            burst_size=self.burst_size,
            burst_interval=self.burst_interval,
            acc_max_delay=self.acc_max_delay,
            acc_min_delay=self.acc_min_delay
        )

    def signature(self):
        """ Simplified version of `__str__`

        Returns
        -------
        str
            A short overview of the identifying attribute values of `self`
        """
        return f"{self.src_ip}:{self.src_port} -> " \
               f"{self.dst_ip}:{self.dst_port} ({self.priority})"
