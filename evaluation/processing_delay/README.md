sure_stream.sh PCAP ROOT_DIR RATE PACKETS UDP_PAYLOAD_LEN LOOPS`__
  
  Creates two tcp-dumps for packets of a network stream sent from one physical interface to a second one.
  If each packet in the source .pcap file is uniquely identifiable, end-to-end delays (including delays caused by the operating system) can be inferred from the two files.

+ __`run_procd_test.sh PCAP ROOT_DIR RATE PACKETS`__

  Calls `measure_stream.sh` multiple times, with UDP payload lengths from 100 Bytes up to 1400 Bytes in 50 Byte increments.
