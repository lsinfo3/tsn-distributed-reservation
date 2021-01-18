from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import os
import seaborn as sns

def concat_all_data(root_dir):
    result_df = None
    for run in os.listdir(root_dir):
        file_path = os.path.join(root_dir, run, 'delays.csv')
        if result_df is None:
            result_df = pd.read_csv(file_path)
        else:
            result_df = result_df.append(pd.read_csv(file_path))
    return result_df[['out', 'in', 'delay', 'transmission_delay','processing_delay', 'bytes_on_wire', 'frame_bytes', 'udp_bytes']]

data_10 = concat_all_data('./data/procd_test_10MBit')
data_100 = concat_all_data('./data/procd_test_100MBit')

def graph_processing_delays():
    fig, axs = plt.subplots(1,2,figsize=(15,5))

    ax1, ax2 = axs

    ax1.stackplot(
        data_10.groupby(['bytes_on_wire']).max().index,
        data_10.groupby(['bytes_on_wire']).max().processing_delay,
        data_10.groupby(['bytes_on_wire']).max().transmission_delay,
        labels=["Processing-delay component", "Transmission-delay component"]
    )
    ax1.plot(data_10.groupby(['bytes_on_wire']).max().delay, label="Total delay", color="Black")
    ax1.set_ylabel("Delay in milliseconds")
    ax1.set_title("Maximum processing delays\n10MBps link speed")

    ax2.stackplot(
        data_100.groupby(['bytes_on_wire']).max().index,
        data_100.groupby(['bytes_on_wire']).max().processing_delay,
        data_100.groupby(['bytes_on_wire']).max().transmission_delay,
        labels=["Processing-delay component", "Transmission-delay component"]
    )
    ax2.set_title("Maximum processing delays\n100MBps link speed")
    ax2.plot(data_100.groupby(['bytes_on_wire']).max().delay, label="Total delay", color="Black")

    for ax in axs:
        yticks=np.arange(0,0.1, 0.0005)
        xticks=range(0,1500, 200)
        ax.set(
            ylim=(0,0.0035),
            xlim=(150,1450),
            yticks=yticks,
            xticks=xticks,
            yticklabels=[f"{1000*t:.1f}" for t in yticks],
            xlabel="Frame size in Byte"
        )
        ax.grid()
        ax.legend()

    fig.show()

def graph_cum_processing_delay():
    fig, axs = plt.subplots(1,1,figsize=(10,5))

    ax1 = axs

    ax1.hist(
        data_10.processing_delay,
        cumulative=-1,
        histtype='step',
        bins=np.linspace(0, 0.00151, 10000),
        linewidth=2,
        label="Link-speed 10 Mbps"
    )
    ax1.hist(
        data_100.processing_delay,
        cumulative=-1,
        histtype='step',
        bins=np.linspace(0, 0.0008, 10000),
        linewidth=2,
        label="Link-speed 100 Mbps"
    )

    xticks=np.arange(0,0.0016, 0.0001)

    ax1.set(
        yscale='log',
        xlim=(0,0.0015),
        xticks=xticks,
        xticklabels=[f"{1000*t:.1f}ms" for t in xticks],
        xlabel="Processing delay x",
        ylabel="Measurements of processing-delay > x"
    )
    ax1.grid()
    ax1.legend()
    ax1.set_yticklabels(["", "", "1", "10", "100", "1000", "10000", "100000", "1000000"])

    fig.show()
