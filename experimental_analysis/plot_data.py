#%% Imports
import utils
import utils_mpl
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Params:
_FILE_PATH = '../Temp/15mL.csv'
_ml_hr = 60 / 1000  # uL/min to mL/hr

# Plotting params:
flow_rate_range = (0, 10)      # mL/hr
flow_rate_xzoom = (0.5, 1.0)   # Empirically set after plotting
flow_rate_yzoom = (5.0, 6.0)   # Empirically set after plotting
temp_range      = (19, 40)     # deg C
temp_xzoom      = (0.5, 1.0)   # Empirically set after plotting
temp_yzoom      = (24.75, 25.75)
vol_range       = (0, 350)     # mL

#%% Data Loading & Processing
utils_mpl.set_global()

sensirion_df = pd.read_csv(_FILE_PATH)
headers = sensirion_df.columns.tolist()
print(f"Headers:\n {headers}")

timestamp_utc = sensirion_df[headers[0]]
time_rel_s    = (timestamp_utc - timestamp_utc.iloc[0])
time          = time_rel_s.to_numpy()
Ts            = np.mean(np.diff(time))
time_h        = time / 3600.0
print(f"Average Sampling Time: {Ts:.3f} s")

N    = 10
flow = sensirion_df[headers[1]].to_numpy()
flow = np.nan_to_num(flow, nan=0.0)
mv_avg_flow = utils.moving_avg_nonzero(flow, N)    # uL/min

volume = sensirion_df[headers[2]].to_numpy()
volume = np.nan_to_num(volume, nan=0.0)
volume /= 1000.0                                   # uL → mL

temp = sensirion_df[headers[3]].to_numpy()
temp = np.nan_to_num(temp, nan=0.0)                # deg C

flow_ul_per_s   = flow / 60.0                      # uL/min → uL/s
integrated_flow = utils.integrate_flow_rate(time, flow_ul_per_s)
integrated_flow /= 1000.0                          # uL → mL


#%% Flow rate q[k]
fig_q, ax_q = utils_mpl.get_fig(size=(7.2, 4.5), dpi=300)
ax_q.step(time_h, flow * _ml_hr,        where='post', lw=1.0, label='Flow Rate',   color='steelblue')
ax_q.step(time_h, mv_avg_flow * _ml_hr, where='post', lw=1.5, label='Moving Avg',  color='crimson')
xticks = np.linspace(0, time_h[-1], 10)
yticks = np.linspace(flow_rate_range[0], flow_rate_range[1], 12)
utils_mpl.set_format(ax_q.xaxis, ticks=xticks, fmt=utils_mpl.make_formatter(".1f"))
utils_mpl.set_format(ax_q.yaxis, ticks=yticks, fmt=utils_mpl.make_formatter(".1f"))
ax_q.set_xlabel(r'Time (hours)')
ax_q.set_ylabel(r'$q(t)$ (mL/hr)')
utils_mpl.set_x_axis(ax_q, bnd=(0, time_h[-1]),              margin=0.02)
utils_mpl.set_y_axis(ax_q, bnd=(flow_rate_range[0], flow_rate_range[1]), margin=0.05)
utils_mpl.set_grid(fig_q, ax_q, major=True, minor=True)
ax_q.legend(loc='upper right')
utils_mpl.save_pdf(fig_q, 'flow_rate.pdf')
plt.show()


#%% Temperature T[k]
fig_T, ax_T = utils_mpl.get_fig(size=(7.2, 4.5), dpi=300)
ax_T.step(time_h, temp, where='post', lw=1.0, label='Temperature', color='darkorange')
xticks = np.linspace(0, time_h[-1], 10)
yticks = np.linspace(temp_range[0], temp_range[1], 9)
utils_mpl.set_format(ax_T.xaxis, ticks=xticks, fmt=utils_mpl.make_formatter(".1f"))
utils_mpl.set_format(ax_T.yaxis, ticks=yticks, fmt=utils_mpl.make_formatter(".1f"))
ax_T.set_xlabel(r'Time (hours)')
ax_T.set_ylabel(r'$T(t)$ ($^\circ$C)')
utils_mpl.set_x_axis(ax_T, bnd=(0, time_h[-1]), margin=0.02)
utils_mpl.set_y_axis(ax_T, bnd=temp_range,      margin=0.05)
utils_mpl.set_grid(fig_T, ax_T, major=True, minor=True)
ax_T.legend()
utils_mpl.save_pdf(fig_T, 'device_temperature.pdf')
plt.show()


#%% Volume V[k]
fig_V, ax_V = utils_mpl.get_fig(size=(7.2, 4.5), dpi=300)
ax_V.plot(time_h, volume,          lw=1.0, label='Volume',           color='steelblue')
ax_V.plot(time_h, integrated_flow, lw=1.0, label='Integrated flow',  color='seagreen')
ax_V.axhline(y=300,         color='k',   lw=0.8, ls='--', label=r'$V_b(0) = 300$ mL')
ax_V.axhline(y=volume[-1],  color='crimson', lw=0.8, ls='--',
             label=fr'$V(\mathrm{{end}}) = {volume[-1]:.1f}$ mL')
xticks = np.linspace(0, time_h[-1], 10)
yticks = np.linspace(vol_range[0], vol_range[1], 10)
utils_mpl.set_format(ax_V.xaxis, ticks=xticks, fmt=utils_mpl.make_formatter(".1f"))
utils_mpl.set_format(ax_V.yaxis, ticks=yticks, fmt=utils_mpl.make_formatter(".1f"))
ax_V.set_xlabel(r'Time (hours)')
ax_V.set_ylabel(r'$V(t)$ (mL)')
utils_mpl.set_x_axis(ax_V, bnd=(0, time_h[-1]),          margin=0.02)
utils_mpl.set_y_axis(ax_V, bnd=(vol_range[0], vol_range[1]), margin=0.05)
utils_mpl.set_grid(fig_V, ax_V, major=True, minor=True)
ax_V.legend(loc='best')
utils_mpl.save_pdf(fig_V, 'dispensed_volume.pdf')
plt.show()
