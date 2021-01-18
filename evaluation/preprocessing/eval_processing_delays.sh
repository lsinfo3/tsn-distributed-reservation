local_data_dir=$1   # The local directory into which to copy the measurements and write the results
send_rate=$2        # The send rate at which the measurements were made 
remote_data_dir=$3  # The remote directory where measuremnts are stored by their total packet size

echo "Copying Files..."
mkdir -p $local_data_dir
scp -r "$remote_data_dir/*" $local_data_dir

for file in $local_data_dir/*
do
    #
    # Create directory and filenames
    #
    
    bytes_on_wire=$(eval "basename $file")

    dir=$local_data_dir/$bytes_on_wire
    in_file=$dir/in
    out_file=$dir/out
    csv_file=$dir/delays.csv
    results_file=$dir/results.txt
    
    #
    # Run processing delay analysis and delete raw data after success
    #

    echo "Calculate processing delay for ${bytes_on_wire} Byte..."
    sh calc_processing_delay.sh $in_file $out_file $csv_file $send_rate $bytes_on_wire # && rm $dir/*in* && rm $dir/*out*
done