import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import os

data = {
    'A': {
        1: dict(),
        2: dict()
    }
}

for i in range(1,7):
    data['A'][1][i] = pd.read_csv(f'./data/scenario_{i}/1526/delays.csv')
    data['A'][2][i] = pd.read_csv(f'./data/scenario_{i}/1526/delays.csv')


def graph_cum_delay_10():
    fig, axs = plt.subplots(ncols=2, figsize=(15,5))

    (ax1,ax2) = axs

    bins = np.arange(0,1,0.000001)

    ax1.hist(data['A'][1][2].delay, bins=bins, cumulative=True, histtype='step', label='Without stream reservation', linewidth=2)
    ax1.hist(data['A'][2][2].delay, bins=bins, cumulative=True, histtype='step', label='With stream reservation', linewidth=2)
    ax1.set(title='Cumulative distribution of end-to-end delays\nScenario 1: Total traffic < 10Mbits')

    ax2.hist(data['A'][1][3].delay, bins=bins, cumulative=True, histtype='step', label='Without stream reservation', linewidth=2)
    ax2.hist(data['A'][2][3].delay, bins=bins, cumulative=True, histtype='step', label='With stream reservation', linewidth=2)
    ax2.set(title='Cumulative distribution of end-to-end delays\nScenario 2: Total traffic > 10Mbits')

    xticks = [0.0001, 0.001, 0.01, 0.1]

    xticklabels = [f"{t * 1000:.0f}ms" for t in xticks]
    yticks=[1,10,100,1000,10000,25000]
    yticklabels=[str(t) for t in yticks]
    ylim=(1,100000)
    for ax in axs:
        ax.set(
            xlim=(0.0001,0.1),
            xlabel='Total delay x',
            ylabel='Number of frames with delay < x',
            ylim=ylim,
            yscale='log',
            xscale='log'
        )
        ax.set(
            yticks=yticks,
            yticklabels=yticklabels,
            xticks=[0.0001, 0.001, 0.01, 0.1],
            xticklabels=['0.1ms', '1ms', '10ms', '100ms']
        )
        ax.grid()
        ax.legend(loc='lower left')
    fig.show()


def graph_cum_delay_100():
    fig, axs = plt.subplots(ncols=2, figsize=(15,5))

    (ax1,ax2) = axs

    bins = np.arange(0,1,0.000001)

    ax1.hist(data['A'][1][5].delay, bins=bins, cumulative=True, histtype='step', label='Without stream reservation', linewidth=2)
    ax1.hist(data['A'][2][5].delay, bins=bins, cumulative=True, histtype='step', label='With stream reservation', linewidth=2)
    ax1.set(title='Cumulative distribution of end-to-end delays\nTotal traffic < 100Mbits')

    ax2.hist(data['A'][1][6].delay, bins=bins, cumulative=True, histtype='step', label='Without stream reservation', linewidth=2)
    ax2.hist(data['A'][2][6].delay, bins=bins, cumulative=True, histtype='step', label='With stream reservation', linewidth=2)
    ax2.set(title='Cumulative distribution of end-to-end delays\nTotal traffic > 100Mbits')

    xticks = [0.0001, 0.001, 0.01, 0.1]

    xticklabels = [f"{t * 1000:.0f}ms" for t in xticks]
    yticks=[1,10,100,1000,10000,25000]
    yticklabels=[str(t) for t in yticks]
    ylim=(1,100000)
    for ax in axs:
	ax.set(
	    xlim=(0.0001,0.1),
	    xlabel='Total delay x',
	    ylabel='Number of frames with delay < x',
	    ylim=ylim,
	    yscale='log',
	    xscale='log'
	)
	ax.set(
	    yticks=yticks,
	    yticklabels=yticklabels,
	    xticks=[0.0001, 0.001, 0.01, 0.1],
	    xticklabels=['0.1ms', '1ms', '10ms', '100ms']
	)
	ax.legend(loc='lower right')
	ax.grid()

    fig.show()
