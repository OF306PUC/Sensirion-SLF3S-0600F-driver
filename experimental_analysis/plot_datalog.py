#%% Imports
import utils
import utils_mpl
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Params:
_FILE_PATH      = 'DataLog/DataLog.csv'
_SKIP_ROWS      = 15             # metadata lines before the column headers
_ml_hr          = 60 / 1000      # uL/min → mL/hr
_nom_flow_rate  = 5              # mL/hr 

# Plotting params:
flow_rate_range = (-1, 10)    # mL/hr
temp_range      = (19, 40)    # deg C

#%% Data Loading & Processing
utils_mpl.set_global()

print("Loading DataLog.csv (large file, may take a moment)...")
# thousands=',' handles values like "1,000.4261" (comma as thousands separator)
df = pd.read_csv(_FILE_PATH, skiprows=_SKIP_ROWS, thousands=',')
headers = df.columns.tolist()
print(f"Headers:\n {headers}")
print(f"Rows loaded: {len(df):,}")
for col in headers:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df.dropna(subset=[headers[1], headers[2], headers[3]], inplace=True)
df.reset_index(drop=True, inplace=True)

time   = df[headers[1]].to_numpy()   # Relative Time [s] — monotonic
time_h = time / 3600.0               # → hours
Ts     = np.median(np.diff(time))
print(f"Median Sampling Time: {Ts*1000:.1f} ms")
print(f"Total recording time: {time[-1]/3600:.2f} h")

N    = 10000
flow = df[headers[2]].to_numpy()     # Flow linearized [uL/min]
flow = np.nan_to_num(flow, nan=0.0)
mv_avg_flow = utils.moving_avg_nonzero(flow, N)

temp = df[headers[3]].to_numpy()     # Temperature linearized [deg C]
temp = np.nan_to_num(temp, nan=0.0)

flow_ul_per_s   = flow / 60.0
integrated_flow = utils.integrate_flow_rate(time, flow_ul_per_s)
integrated_flow /= 1000.0            # uL → mL
nominal_flow_rate_s = _nom_flow_rate * (1 / _ml_hr) * (1 / 60)
nominal_flow_rate_s /= 1000.0
nominal_volume = utils.integrate_flow_rate(time, nominal_flow_rate_s * np.ones_like(time))


#%% Flow rate q[k]
fig_q, ax_q = utils_mpl.get_fig(size=(10.0, 4.5), dpi=150)
ax_q.step(time_h, flow * _ml_hr,        where='post', lw=0.6, label='Flow Rate',  color='steelblue', alpha=0.7)
ax_q.step(time_h, mv_avg_flow * _ml_hr, where='post', lw=1.2, label='Moving Avg', color='crimson')
xticks = np.linspace(0, time_h[-1], 10)
yticks = np.linspace(flow_rate_range[0], flow_rate_range[1], 12)
utils_mpl.set_format(ax_q.xaxis, ticks=xticks, fmt=utils_mpl.make_formatter(".1f"))
utils_mpl.set_format(ax_q.yaxis, ticks=yticks, fmt=utils_mpl.make_formatter(".1f"))
ax_q.set_xlabel(r'Time (hours)')
ax_q.set_ylabel(r'$q(t)$ (mL/hr)')
utils_mpl.set_x_axis(ax_q, bnd=(0, time_h[-1]),                          margin=0.02)
utils_mpl.set_y_axis(ax_q, bnd=(flow_rate_range[0], flow_rate_range[1]), margin=0.05)
utils_mpl.set_grid(fig_q, ax_q, major=True, minor=True)
ax_q.legend(loc='upper right')
#utils_mpl.save_pdf(fig_q, 'flow_rate_datalog.pdf')
plt.show()


#%% Temperature T[k]
fig_T, ax_T = utils_mpl.get_fig(size=(10.0, 4.5), dpi=150)
ax_T.step(time_h, temp, where='post', lw=0.8, label='Temperature', color='darkorange')
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
#utils_mpl.save_pdf(fig_T, 'temperature_datalog.pdf')
plt.show()


#%% Integrated volume V[k]

fig_V, ax_V = utils_mpl.get_fig(size=(10.0, 4.5), dpi=150)
ax_V.plot(time_h, integrated_flow, lw=1.0, label='Integrated Flow', color='seagreen')
ax_V.plot(time_h, nominal_volume, lw=1.0, label='Nominal Volume', color='black', linestyle='dashed')
ax_V.axhline(y=integrated_flow[-1], color='crimson', lw=0.8, ls='--',
             label=fr'$V(\mathrm{{end}}) = {integrated_flow[-1]:.1f}$ mL')
xticks = np.linspace(0, time_h[-1], 10)
vol_max = np.ceil(integrated_flow[-1] / 50) * 50 + 50
yticks  = np.linspace(0, vol_max, 10)
utils_mpl.set_format(ax_V.xaxis, ticks=xticks, fmt=utils_mpl.make_formatter(".1f"))
utils_mpl.set_format(ax_V.yaxis, ticks=yticks, fmt=utils_mpl.make_formatter(".0f"))
ax_V.set_xlabel(r'Time (hours)')
ax_V.set_ylabel(r'$V(t)$ (mL)')
utils_mpl.set_x_axis(ax_V, bnd=(0, time_h[-1]), margin=0.02)
utils_mpl.set_y_axis(ax_V, bnd=(0, vol_max),    margin=0.05)
utils_mpl.set_grid(fig_V, ax_V, major=True, minor=True)
ax_V.legend(loc='upper left')
#utils_mpl.save_pdf(fig_V, 'volume_datalog.pdf')
plt.show()
