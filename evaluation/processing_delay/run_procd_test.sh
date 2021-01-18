#!/bin/bash

pcap=$1             # The file from which to source the packets to send
root_dir=$2         # The root directory in which a subdirectory with the capture files will be written
rate=$3             # The rate in Mbits at which to send the packets
packets=$4          # The number of packets that will be sent

mkdir -p $root_dir

for udp_payload_len in $(seq 100 50 1400)
do
    sh measure_stream.sh $pcap $root_dir $rate $packets $udp_payload_len  > /dev/null
    sleep 3
done
