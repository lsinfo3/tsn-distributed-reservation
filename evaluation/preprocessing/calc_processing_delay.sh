#/bin/bash

in_file=$1
out_file=$2
csv_file=$3
send_rate=$4
bytes_on_wire=$5

#
# Convert the raw data to filtered json
#

echo "Converting raw files to json..."
sh convert_to_json.sh $in_file
sh convert_to_json.sh $out_file

in_filtered=${in_file}_json_filtered
out_filtered=${out_file}_json_filtered

#
# Evaluate delay measurements
#

echo "Performing delay caluclation..."
python experiment.py eval-processing-delay --input-file-in $in_filtered --input-file-out $out_filtered --csv-file $csv_file --send-rate $send_rate --bytes-on-wire $bytes_on_wire