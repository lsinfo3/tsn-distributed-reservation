import pandas as pd
import seaborn as sns
import numpy as np
from matplotlib import pyplot as plt
import json
from datetime import datetime

def convert_to_dataframe(timestamps):
    lowest = None
    packets = {}
    for ts in timestamps:
        t = ts['time']
        i = ts['id']
        if i not in packets:
            packets[i] = {
                'out': t,
                'id': int(i,16)
            }
            if lowest is None or t < lowest:
                lowest = t
        else:
            packets[i]['in'] = t

    for value in packets.values():
        value['delay'] = value['in'] - value['out']
        value['out'] -= lowest
        value['in'] -= lowest

    return pd.DataFrame(
        list(
            sorted(
                packets.values(),
                key=lambda v: v['in']
            )
        )
    )


def get_floating_avg_rate(time_series, interval):
    return list(
        map(
            lambda d: (1 * interval) / (d[1] - d[0]), 
            zip(
                time_series[:-interval], 
                time_series[interval:]
            )
        )
    )


def get_avg_speeds(dfs, interval):
    speedss = [get_floating_avg_rate(df['in'], interval) for df in dfs]
    return list(map(lambda speeds: sum(speeds) / len(speeds), zip(*speedss)))
        
    
INTERVAL = 10

raw_data_optimized = [
    json.load(open(f"./data/converted_json_rdopt{i}.pcap","r")) 
    for i 
    in range(10)
]

raw_data_naive = [
    json.load(open(f"./data/converted_json_rdnaiv{i}.pcap","r"))
    for i 
    in range(10)
]

raw_data_naive_extended = json.load(
    open(f"./data/converted_json_rdnaiv10.pcap", "r")
)

frames_optimized     = [convert_to_dataframe(data) for data in raw_data_optimized]
frames_naive         = [convert_to_dataframe(data) for data in raw_data_naive]
frame_naive_extended =  convert_to_dataframe(raw_data_naive_extended)

optimized      = get_avg_speeds(frames_optimized, INTERVAL)
naive          = get_avg_speeds(frames_naive,     INTERVAL)
naive_extended = get_floating_avg_rate(frame_naive_extended['in'], INTERVAL)


opt_data = pd.DataFrame(
    [
        {"Deployed streams": pid, "rate": delay, "Algorithm": "Optimized (Average of 10 runs)"} 
        for dataframe in frames_optimized 
        for pid, delay in enumerate(get_floating_avg_rate(dataframe["in"], INTERVAL))
    ] + 
    [
        {"Deployed streams": pid, "rate": delay, "Algorithm": "Naive (Average of 10 runs)"} 
        for dataframe in frames_naive
        for pid, delay in enumerate(get_floating_avg_rate(dataframe["in"], INTERVAL))
    ] +
    [
        {"Deployed streams": pid, "rate": delay, "Algorithm": "Naive (Single run)"}
        for pid, delay in enumerate(naive_extended)
    ][len(get_floating_avg_rate(frames_naive[0]["in"], INTERVAL)):]
)


def graph_subs_per_second():
    fig, ax_mod = plt.subplots(figsize=(15, 5))
    with sns.axes_style("whitegrid"):
        sns.lineplot(data=opt_data, x="Deployed streams", y="rate", ax=ax_mod, hue="Algorithm")

    ax_mod.set(
        ylim=(-5,100),
        yticks=range(0,110,10),
        xticks=range(0,1100, 100),
        xlim=(0,1000),
        ylabel=f"Subscriptions / second\n(Trailing average of previous {INTERVAL} subscriptions)",
        xlabel=f"Deployed streams"
    )
    ax_mod.grid()
    ax_mod.legend()
    fig.show()


def graph_sub_delay_comparison():
    fig, axs = plt.subplots(1, 2, figsize=(15,5))
    (ax1, ax2) = axs

    start = frames_optimized[0]
    start["Method"] = "Optimized algorithm (avg. of 10 runs)"

    for frame in frames_optimized[1:]:
        frame["Method"] = "Optimized algorithm (avg. of 10 runs)"
        start = start.append(frame)
        
    for frame in frames_naive:
        frame["Method"] = "Naive algorithm (avg. of 10 runs)"
        start = start.append(frame)
        
    df_limited["Method"] = "Optimized algorithm\n(rate limited, single run)"
    start = start.append(df_limited)

    sns.lineplot(data=start, x="id", y="delay", ax=ax1, hue="Method")
    sns.lineplot(data=frames_optimized[0], x="in", y="id", ax=ax2, label="Optimized algorithm")
    sns.lineplot(data=frames_naive[0], x="in", y="id", ax=ax2, label="Naive algorithm")
    sns.lineplot(data=df_limited, x="in", y="id", ax=ax2, label="Optimized algorithm\n(rate limited)")

    ax1.set(
        ylim=(-0.5,15),
        xlim=(2000,3000),
        yticks=range(0,20),
        xticks=range(2000, 3100, 100),
        xticklabels=[f"{i}" for i in range(0, 1100, 100)],
        xlabel="Deployed streams",
        ylabel="Measured delay in seconds",
        title='Reservation delays by different methods\nwith 95% confidence intervals'
    )
    ax1.legend(loc="upper center")

    ax2.set(
        xlim=(0,45),
        ylim=(2000,3000),
        yticks=[2000,2200,2400,2600,2800,3000],
        yticklabels=["0","200","400","600","800","1000"],
        xlabel='Time x in seconds since first advertisement was sent',
        ylabel='Cumulative deployed streams at x seconds',
        title='Number of streams deployed at a given time (single runs)'
    )
    ax2.legend(loc="upper left")

    for ax in axs:
        ax.grid()
