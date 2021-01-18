import argparse as ap
import json
import os
import pandas as pd

PROTOCOL_OVERHEAD = {
    'ETHERNET_HEADER': 8,
    'IP_HEADER': 20,
    'UDP_HEADER': 8
}

DL_OVERHEAD = {
    'ETHERNET_PREAMBLE': 7,
    'ETHERNET_FRAME_DELIMITER': 1,
    'ETHERNET_CRC': 4,
}


def parse_id(s):
    s_1 = s.split(':')
    s_1.reverse()
    return int(''.join(s_1), 16)


def to_delays(input_file_out=None, input_file_in=None, bytes_on_wire=None, send_rate=None, **kwargs):
    assert os.path.isfile(os.path.abspath(input_file_in))
    assert os.path.isfile(os.path.abspath(input_file_out))
    import numpy
    out_data = json.load(open(input_file_out, 'r'))
    in_data = json.load(open(input_file_in, 'r'))
    packets = {}
    for data in out_data:
        assert data is not None
        try:
            assert data['id'] is not None
            assert data['time'] is not None
        except AssertionError as a:
            print(data)
            raise a
        packet_id = parse_id(data['id'])
        leave_time = float(data['time'])
        packets[packet_id] = {
            'id': packet_id,
            'out': leave_time
        }

    for data in in_data:
        assert data is not None
        assert data['id'] is not None
        assert data['time'] is not None
        packet_id = parse_id(data['id'])
        arrival_time = float(data['time'])
        if packet_id in packets:
            packets[packet_id]['in'] = arrival_time

    result = []

    transmission_delay = (bytes_on_wire / (send_rate / 8)) * 2
    frame_bytes = bytes_on_wire - sum(DL_OVERHEAD.values())
    udp_bytes = frame_bytes - sum(PROTOCOL_OVERHEAD.values())

    for packet in packets.values():
        if 'in' not in packet:
            continue
        packet['delay'] = packet['in'] - packet['out']
        assert packet['delay'] >= 0
        packet['transmission_delay'] = transmission_delay
        packet['processing_delay'] = packet['delay'] - packet['transmission_delay']
        packet['bytes_on_wire'] = bytes_on_wire
        packet['frame_bytes'] = frame_bytes
        packet['udp_bytes'] = udp_bytes
        result.append(packet)

    return pd.DataFrame(result)


def main(action=None, csv_file=None, **kwargs):
    assert os.path.isdir(os.path.dirname(os.path.abspath(csv_file)))
    if action == 'eval-processing-delay':
        df = to_delays(**kwargs)
        print('\n')
        df.to_csv(csv_file)


if __name__ == '__main__':
    parser = ap.ArgumentParser(description="Script for running and evaluating TSN-transmissions.")

    parser.add_argument(
        'action',
        help='The action that should be run by the script',
        choices=['eval-processing-delay']
    )

    parser.add_argument(
        '--input-file-in',
        help="The json containing the id and capture time for all received packets.",
    )

    parser.add_argument(
        '--input-file-out',
        help="The json containing the id and capture time for all sent packets.",
    )

    parser.add_argument(
        '--csv-file',
        help="A CSV containing the packets with id and transmission delay.",
    )

    parser.add_argument(
        '--packets',
        type=int,
        help='The number of packets to send for testing a connection.',
        default=0
    )

    parser.add_argument(
        '--bytes-on-wire',
        type=int,
        help='The complete size of a frame, including data-link overhead.',
        default=0
    )

    parser.add_argument(
        '--send-rate',
        help='The bandwidth at which packets are sent in Bit/second',
        type=int,
    )
    try:
        kwargs = vars(parser.parse_args())
    except Exception:
        print(parser)
    main(**kwargs)