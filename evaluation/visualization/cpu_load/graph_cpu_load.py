import pandas as pd
from matplotlib import pyplot as plt


def graph_cpu_usage():
    load_opt = pd.read_csv("./data/load_optimized.csv")
    load_naive = pd.read_csv("./data/load_naive.csv")


    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(load_opt.cpu, label='Optimized worst-case calculation')
    ax.plot(load_naive.cpu, label='Naive worst-case calculation')
    ax.set(
        xlim=(0,35),
        ylim=(1,110),
        xticks=range(0,50),
        yticks=range(0,110, 10),
        title="CPU load comparison",
        xlabel="Time in seconds",
        ylabel="CPU load in %"
    )

    ax.grid()
    ax.legend()

    fig.show()


def graph_cpu_usage_limited_rate():
    load_limited = pd.read_csv("./data/load_limited.csv")

    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(load_limited.cpu)
    ax.set(
        xlim=(0, len(load_limited.cpu)-1),
        ylim=(1,110),
        xticks=range(0,50),
        yticks=range(0,110, 10),
        xlabel="Time in seconds",
        ylabel="CPU load in %"
    )

    ax.grid()

    fig.show()
