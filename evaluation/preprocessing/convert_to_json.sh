#/bin/bash

raw_file=$1

#
# Convert capture files to json
#

json=${raw_file}_json

tshark -T json -j "frame" -x -r $raw_file > $json

#
# Filter json-tcpdump
#

json_filtered=${json}_filtered

cat $json | jq '[.[] | {time: ._source.layers.frame."frame.time_epoch", id: ._source.layers.frame_raw[0][86:92]}]' > $json_filtered