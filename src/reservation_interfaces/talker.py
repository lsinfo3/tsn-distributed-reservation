import asyncio
import os
from random import randint
import yaml

from scapy.all import AsyncSniffer
from scapy.config import conf
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether

from .util import BROADCAST_MAC, ReservationPacket, Reservation, round_up

import time
import random

DEFAULT_PROCESSING_DELAY = 2000
DEFAULT_LINK_SPEED = 100000000


class Talker:
    """
    Interface for the advertisement of real-time network streams

    Attributes
    ----------
    interface
        The system's interface which is connected to the TSN network
    ip
        This device's IP address
    mac
        This device's MAC address
    timeout
        The time in seconds until an advertisement is resent
    resends
        The number of times an advertisement would be resent
    """

    def __init__(self, interface, ip, broadcast_ip, mac, timeout, resends):
        self.loop = asyncio.get_event_loop()
        self.interface = interface
        self.ip = ip
        self.broadcast_ip = broadcast_ip
        self.mac = mac
        self.timeout = timeout
        self.resends = resends
        self.used_port_combinations = set()
        self.advertised_streams = set()
        self.stream_subscriptions = {}
        self.socket = conf.L2socket(iface=self.interface)
        self.sniffer = AsyncSniffer(
            iface=self.interface,
            # filter="dst port 1000",
            prn=self._handle_subscription
        )
        self.sniffer.start()
        self.n = 0
        self.UDP_OVERHEAD = sum([
            7,  # Preamble
            1,  # Frame Delimiter
            6,  # MAC Destination     -
            6,  # MAC Source
            2,  # Ethertype
            20,  # IPv4 Header
            8,  # UDP Header
            4,  # CRC check sequence
            12  # Interpacket gap
        ])

    def _handle_subscription(self, packet):
        """
        Internal method for the handling of received subscriptions. Adds
        the subscriptions to the `stream_subscriptions` dict.

        Parameters
        ----------
        packet
            The received packet
        """
        try:
            stream_reservation_packet = ReservationPacket(packet[3])
            if stream_reservation_packet.status != 1:
                return
            subscription = Reservation(stream_reservation_packet)
        except Exception:
            print("Received a non-reservation packet")
            return
        if subscription not in self.advertised_streams:
            print('Received subscription for non-advertised stream')
            return
        if subscription in self.stream_subscriptions.keys():
            self.stream_subscriptions[subscription].add(subscription.dst_ip)
        else:
            self.stream_subscriptions[subscription] = {subscription.dst_ip}

        self.socket.send(
                Ether(src=self.mac, dst=BROADCAST_MAC) /
                IP(src=self.ip, dst=subscription.dst_ip) /
                UDP(dport=999, sport=1000) /
                subscription.to_acknowledgement_packet()
            )

    def load_test(self, filepath, n):
        assert os.path.isfile(filepath)
        stream_specification = yaml.safe_load(open(filepath, 'r'))[0]
        if 'src_port' in stream_specification:
            stream_specification.pop('src_port')
        if 'dst_port' in stream_specification:
            stream_specification.pop('dst_port')
        self.resends = 0
        self.timeout = 0

        a = time.time_ns()
        for i in range(n):
            self.advertise_stream(dst_port=i+2001, **stream_specification)
            print(f"Sent {i+1}")
            time.sleep(0.025)
        print((time.time_ns() - a)/1000000000)

    def advertise_streams_from_yaml(self, filepath):
        """ Advertises a set of predefined streams from a yaml-file.

        Parameters
        ----------
        filepath
            Absolute path to file containing the info about the streams
            to reserve. Must have following form:

            - dst_ip: <dst_ip>
              src_port: <src_port> (Optional, default is random)
              dst_port: <dst_port> (Optional, default is random)
              min_frame: <minimum frame size in bytes>
                (Optional, default is 84 Bytes)
              max_udp: <maximum frame size in bytes>
                (Optional, default is 1542 Bytes)
              burst_size: <burst size in bytes>
                (Optional, default is <max_udp>)
              burst_intervall: <burst interval in µs>
              |
              send_rate: <burst rate in Bit/s>

            .
            .
            .

        Returns
        -------
        (successful_reservations, unsuccessful_reservations)
            The final result of the reservation run
        """
        assert os.path.isfile(filepath)
        stream_specifications = yaml.safe_load(open(filepath, 'r'))

        src_data = []
        for data in stream_specifications:
            if 'instances' not in data:
                src_data.append(data)
                continue
            src_data += ([data for x in range(data['instances'])])

        # Try to reserve every stream from the dataset
        for data in stream_specifications:
            if 'instances' in data:
                for _ in range(data['instances']):
                    self.advertise_stream(**data)
                    time.sleep(0.01)
            else:
                self.advertise_stream(**data)
        time.sleep(10)
        subscribed_by_prio = {i: 0 for i in range(1,8)}
        for (stream, subs) in self.stream_subscriptions.items():
            subscribed_by_prio[stream.priority] += len(subs)
        print("Subscriptions:")
        for (prio, subs) in subscribed_by_prio.items():
            print(f"Priority {prio}: {subs}")
        return

    async def advertise_streams(self, stream_specifications):
        """ Advertise a set of streams, specified in an iterable

        Parameters
        ----------
        stream_specifications : Iterable
            The specifications of the streams to advertise

        Returns
        -------

        """
        tasks = []
        for data in stream_specifications:
            if 'instances' in data:
                for _ in range(data['instances']):
                    tasks.append(
                        self.loop.create_task(self._advertise_stream(**data))
                    )
            else:
                tasks.append(
                    self.loop.create_task(self._advertise_stream(**data))
                )

        await asyncio.wait(tasks)

    def advertise_stream(self, **kwargs):
        """ Advertise a stream in a connected TSN-Network.

        Parameters
        ----------
        req_latency
            The requested end-to-end latency in microseconds
        min_udp, optional
            The minimum number of bytes in the udp payload of a frame in the
            stream to advertise (default is 0 Byte)
        max_udp, optional
            The maximum number of bytes in the udp payload of a frame in the
            stream to advertise (default is 1472 Byte)
        burst_size_udp, optional
            The maximum number of bytes sent at once (default is 'max_udp')
        send_rate, optional
            The rate at which the data is sent in Bit/second.
            Alternatively, 'burst_interval' can be passed.
        burst_interval, optional
            The timeframe in which at most 'burst_size_udp' Byte of UDP Payload
            will be sent. Alternatively, 'send_rate' can be passed.
        """
        self.loop.run_until_complete(self._advertise_stream(**kwargs))

    async def _advertise_stream(self, req_latency, priority=0, src_port=None,
                                dst_port=None, min_udp=0, max_udp=1472,
                                burst_size_udp=None, send_rate=None,
                                burst_interval=None, **kwargs):
        """ Internal method. Use 'reserve_stream' insted.
        """

        assert 1 <= priority and priority <= 7
        assert 0 <= min_udp and min_udp <= 1472
        assert 0 <= max_udp and max_udp <= 1472
        assert min_udp <= max_udp
        assert burst_interval is not None or send_rate is not None

        if burst_size_udp is None:
            burst_size_udp = max_udp

        min_frame = min_udp + self.UDP_OVERHEAD
        max_frame = max_udp + self.UDP_OVERHEAD
        burst_size = burst_size_udp + self.UDP_OVERHEAD

        # Get a random value for not defined src-or dst-port values
        if src_port is None and dst_port is None:
            (src_port, dst_port) = (
                randint(1001, 2 ** 16 - 1), randint(1001, 2 ** 16 - 1)
            )
            while (src_port, dst_port) in self.used_port_combinations:
                (src_port, dst_port) = (
                    randint(1001, 2 ** 16), randint(1001, 2 ** 16)
                )

        elif src_port is None:
            src_port = randint(1001, 2 ** 16)
            while (src_port, dst_port) in self.used_port_combinations:
                src_port = randint(1001, 2 ** 16)

        elif dst_port is None:
            dst_port = randint(1001, 2 ** 16)
            while (src_port, dst_port) in self.used_port_combinations:
                dst_port = randint(1001, 2 ** 16)

        else:
            if (src_port, dst_port) in self.used_port_combinations:
                raise ValueError('Port combination already in use!')

        # Add the now used port-combination to the set of used ones
        self.used_port_combinations.add((src_port, dst_port))

        # If no temporal context is given for the burst size, raise ValueError
        if send_rate is None and burst_interval is None:
            raise ValueError('Missing burst-rate or burst-interval!')

        # If a burst rate is given, derive the burst_interval from it
        if send_rate is not None:
            burst_interval = int((burst_size * 8 * 1000000) / send_rate)

        # Set the transmission delay to the first hop as the accumulated
        # minimum delay
        acc_min_delay = int((max_frame * 8) / DEFAULT_LINK_SPEED)

        # Set the sum of accumulated minimum delay and the preconfigured
        # processing delay bound as the accumulated maximum delay
        acc_max_delay = acc_min_delay + DEFAULT_PROCESSING_DELAY

        # Check if the accumulated maximum delay does not already surpass
        # required end-to-end latency
        if acc_max_delay >= req_latency:
            print(f"Required latency of {req_latency} not possible.")
            return None

        # Create a new stream-reservation
        advertisement = Reservation(
            # End-to-end information
            req_latency=req_latency,
            priority=priority,
            src_ip=self.ip,
            src_port=src_port,
            dst_port=dst_port,
            # Stream description
            min_frame=min_frame,
            max_frame=max_frame,
            burst_size=burst_size,
            burst_interval=burst_interval,
            # Delay carriers
            acc_min_delay=acc_min_delay,
            acc_max_delay=acc_min_delay
        )

        self.advertised_streams.add(advertisement)

        # Send the advertisement 1 + `resends` times with a `timeout` interval
        sends = 0
        while self.resends is None or sends <= self.resends:
            self.socket.send(
                Ether(src=self.mac, dst=BROADCAST_MAC) /
                IP(src=self.ip, dst=self.broadcast_ip) /
                UDP(dport=1000, sport=1000) /
                advertisement.to_advertisement_packet()
            )
            if self.timeout != 0:
                await asyncio.sleep(self.timeout)
            sends += 1
