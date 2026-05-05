# Sensirion SHDLC Driver (Python)
Robust Data Logger for SLF3S-0600F  
**Raspberry Pi – Raspbian Bookworm**

---

## Overview

This project implements a **long-running data logger** for the Sensirion SLF3S-0600F flow sensor using:

- SHDLC over RS485 / USB (FTDI / SCC1 adapter)
- Dual-threaded architecture (acquisition thread + logger thread)
- Self-describing CSV (metadata header, `sample_index` column, COMPLETE/INTERRUPTED footer)
- Binary log with 16-byte magic header for independent recovery
- Structured event logging to terminal and `Logs/events.log`
- Ring buffer for last-N measurements
- Graceful shutdown on SIGINT / SIGTERM

### Execution model

- The logger runs inside a **Docker container**, started manually via SSH
- The container **continues running after SSH disconnect** (`restart: on-failure:3`)
- Data is written to host-mounted volumes (`./data/`, `./logs/`) and survives container restarts
- `docker compose down` sends SIGTERM → logger writes the `INTERRUPTED` footer before exiting

---

## 1. Connect to the Raspberry Pi

```bash
ssh pi@<raspberry_pi_ip>
```

---

## 2. Verify USB device detection

Plug in the Sensirion SCC1-USB / RS485 adapter.

```bash
ls /dev/ttyUSB*
```

Expected output:

```
/dev/ttyUSB0
```

Optional diagnostics:

```bash
lsmod | grep ftdi
dmesg | grep ttyUSB
```

> On **Raspbian Bookworm**, the `ftdi_sio` driver is loaded automatically.  
> No manual driver binding is required.

---

## 3. Ensure system time is synchronized

```bash
sudo timedatectl set-ntp true
timedatectl show -p NTPSynchronized   # expect: NTPSynchronized=yes
```

---

## 4. Project structure

```
sensirion-SLF3S-0600F-driver/
├── README.md
├── Dockerfile
├── docker-compose.yml
├── .env.template
├── .dockerignore
├── analysis/
│   └── analyse.py               ← post-experiment analysis script
└── raspberry/
    ├── main.py                  ← entry point
    ├── data_logger.py           ← CSV + binary logger (metadata, sample_index, footer)
    ├── shdlc_driver.py          ← device communication thread
    ├── core.py                  ← constants, scaling, binary format spec
    ├── utils.py                 ← Logger, MeasurementRingBuffer, EndOfInfusionDetector
    ├── recover.py               ← standalone binary-to-CSV recovery tool
    ├── BINARY_FORMAT.md         ← binary file format documentation
    ├── interface.py
    ├── port.py
    ├── shdlc_command.py
    ├── i2c_command.py
    ├── sensor_info.py
    ├── serial_frame_builder.py
    ├── command.py
    ├── requirements.txt
    ├── Temp/                    ← generated; mounted from ./data/ in Docker
    │   ├── {CONFIG}_{REP}.csv
    │   └── {CONFIG}_{REP}.bin
    └── Logs/                    ← generated; mounted from ./logs/ in Docker
        ├── events.log           ← structured event log (all INFO/WARNING/ERROR)
        ├── logs.txt             ← end-of-infusion records
        └── error_logs.txt       ← hardware error records with ring-buffer context
```

---

## 5. Running the data-acquisition system (Docker)

The logger runs inside a Docker container for process isolation, automatic
restart on failure, and clean log management. Data persists in `./data/`
and `./logs/` on the host regardless of container lifecycle.

> **Serial port access**: the `dialout` group grants access to `/dev/ttyUSB0`.
> The container user is already added to this group in the `Dockerfile`.
> On the host, ensure your user also belongs to `dialout`:
> `sudo usermod -aG dialout $USER` (log out and back in to apply).

### 5.1 Clone the project

```bash
git clone https://github.com/OF306PUC/sensirion-SLF3S-0600F-python-driver.git
cd sensirion-SLF3S-0600F-python-driver
```

---

### 5.2 Configure experiment parameters

Copy the template and fill in the values for each new experiment run:

```bash
cp .env.template .env
nano .env   # set CONFIG, EXPERIMENT_REP, PUMP_LOT, FLUID, HOURS, etc.
```

All parameters are injected into the container at runtime, so the exact
command that ran is always visible in `docker compose logs`.

---

### 5.3 Start the logger

```bash
docker compose up --build -d
```

- `--build` rebuilds the image if `raspberry/` has changed (safe to omit on
  subsequent runs when the code is unchanged).
- `-d` runs in detached (background) mode.

---

### 5.4 Follow live events

```bash
docker compose logs -f
```

---

### 5.5 Check status

```bash
docker compose ps
```

---

### 5.6 Stop cleanly

```bash
docker compose down
```

Docker sends SIGTERM → logger writes the `INTERRUPTED` footer sentinel
before exiting.

---

### 5.7 Access recorded data

```bash
ls ./data/    # {CONFIG}_{REP}.csv  {CONFIG}_{REP}.bin
ls ./logs/    # events.log  logs.txt  error_logs.txt
```

---

## 6. Offline tools

### 6.1 Verify a binary log file

Quick integrity check — prints record count, expected vs actual size, and
first/last timestamp.  Does not modify any files.

```bash
python3 raspberry/main.py --verify-binary data/C0_rep_1.bin
```

### 6.2 Recover binary to CSV (no sensor required)

Standalone tool that converts any `.bin` file (including legacy files without
a magic header) back to a CSV with the same column schema as the live logger.

```bash
python3 raspberry/recover.py data/C0_rep_1.bin --output recovered.csv
```

See [raspberry/BINARY_FORMAT.md](raspberry/BINARY_FORMAT.md) for the full
binary format specification.

---

## 7. Post-experiment analysis

```bash
python3 analysis/analyse.py data/C0_rep_1.csv [data/C1_rep_1.csv ...] \
    --output-dir results/ \
    --plot-format pdf \
    --zero-drift-min 60 \
    --empty-pump-min 30
```

Per-experiment outputs (in `results/{experiment_rep}/`):

| File | Content |
|------|---------|
| `stats.json` | Zero-drift µ/σ/threshold, V_disp, T_eff, cross-correlation lag and r_max |
| `{REP}.pdf` | 3-panel figure: q(t), V_disp(t), T(t) with phase markers |
| `{REP}.png` | Same figure as PNG |

When more than one CSV is passed, a `comparison_q_profiles.pdf` overlay is
also produced at the root of `--output-dir`.

---

## 8. Command-line arguments

| Argument | Type | Description | Default |
|---|---|---|---|
| `--port` | `str` | Serial port for SCC1-RS485 / SCC1-USB | `/dev/ttyUSB0` |
| `--baudrate` | `int` | Serial baud rate | `115200` |
| `--slave-address` | `int` | SHDLC slave address | `0x00` |
| `--hours-to-log` | `float` | Acquisition duration in hours | `48` |
| `--sampling-ms` | `int` | Sampling interval in milliseconds | `500` |
| `--configuration` | `str` | Catheter config label: C0, C1a, C1b, C2, C3, C4 | `UNKNOWN` |
| `--experiment-rep` | `str` | Replicate identifier, e.g. `rep_1`, `rep_2` | `UNKNOWN` |
| `--pump-lot` | `str` | Pump manufacturing lot number | `UNKNOWN` |
| `--fluid` | `str` | Fluid description, e.g. `NaCl_240mL_bupiv_60mL` | `UNKNOWN` |
| `--raspberry-id` | `str` | Raspberry Pi identifier (2, 9, or 10) | `UNKNOWN` |
| `--dry-run` | flag | Generate synthetic data without a physical sensor | — |
| `--verify-binary` | `str` | Validate an existing `.bin` file and exit | — |

### Notes
- Output files are named `{CONFIG}_{REP}.csv` / `{CONFIG}_{REP}.bin` inside `Temp/`.
- `--sampling-ms` sets the serial polling interval; the sensor's internal
  measurement rate is set separately in `shdlc_command.py`
  (`ShdlcStartContinuousMeasurement._MEASUREMENT_INTERVAL_X_MS`).
- All events (INFO / WARNING / ERROR) are written to both stdout and
  `Logs/events.log` with millisecond-precision timestamps.
