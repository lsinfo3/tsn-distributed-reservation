#!/bin/bash

pcap=$1             # The file from which to source the packets to send
root_dir=$2         # The root directory in which a subdirectory with the capture files will be written
rate=$3             # The rate in Mbits at which to send the packets
packets=$4          # The number of packets that will be sent
udp_payload_len=$5  # The number of bytes after which the UDP-payload will be cut off, max. 1472 for MTU 1500
loops=$6            # The number of times the pcap should be sent (incompatible with measurement!!)

#
# Add the overhead due to L2, L3 and L4 protocol headers to payload length
#

ether_header_len=$((6 + 6 + 2))
ip_header_len=20
udp_header_len=8

offset=$((ether_header_len + ip_header_len + udp_header_len))

data_length=$((udp_payload_len + offset))

#
# Add the L1 Ethernet bytes to the L2 frame and calculate the total number of bytes sent
#

preamble=7
frame_delimiter=1
crc_checksum=4

bytes_on_wire=$((data_length + preamble + frame_delimiter + crc_checksum))

#
# Create a directory for this run by its packet size
#

dir=$root_dir/$bytes_on_wire

mkdir -p $dir

#
# Startup the capturing machanisms for the outgoing and incoming packets
# to write their captures each to an in and out file
#

dumpcap -a duration:100 -i eth0 -s 128 -B 8 -w $dir/out_raw &
dc1=$!
dumpcap -a duration:100 -i eth1 -s 128 -B 8 -w $dir/in_raw  &
dc2=$!

#
# Wait for the capturing applications to completely set up
#

sleep 5 &
wait $!

#
# Begin transmission of the packets from the pcap file
#

sudo bittwist -i eth0 -m 0 -r $rate -s $data_length $pcap

#
# Wait for the capturing applications to complete
#

wait $dc1
wait $dc2