# Sensirion SHDLC Python Driver  
Robust Data Logger for SLF3S-0600F  
**Raspberry Pi – Raspbian Bookworm**

---

## Overview

This project implements a **long-running data logger** for Sensirion SHDLC-based sensors (e.g. SLF3S-0600F) using:

- SHDLC over RS485 / USB (FTDI)
- Dual-threaded architecture (acquisition + logging)
- CSV + binary logging
- Persistent error logging with context
- Ring buffer for last measurements
- Graceful shutdown on SIGINT / SIGTERM

### Execution model (IMPORTANT)

- The logger is **started manually by the user via SSH**
- The logger **continues running after SSH disconnect**
- The logger **does NOT start automatically on reboot**
- No systemd service is used

This behavior is achieved using **`nohup`**, which detaches the process from the SSH session safely.

---

## 1. Connect to the Raspberry Pi

From your host machine connect via SSH to the Pi device:

```bash
ssh pi@<raspberry_pi_ip>
```

---

## 2. Verify USB device detection

Plug in the Sensirion SCC1-USB / RS485 adapter in the Raspberry Pi USB port.

Check that the FTDI driver is loaded automatically:

```bash
ls /dev/ttyUSB*
```

Expected output (example):

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

Correct timestamps require NTP synchronization.

Enable NTP:

```bash
sudo timedatectl set-ntp true
```

Verify:

```bash
timedatectl
timedatectl show -p NTPSynchronized
```

Expected:

```
NTPSynchronized=yes
```

---

## 4. Project structure

Example directory layout:

```
sensirion-SLF3S-0600F-python-driver/
├── README.md
└── raspberry/
    ├── main.py
    ├── shdlc_driver.py
    ├── core.py
    ├── interface.py
    ├── port.py
    ├── shdlc_command.py
    ├── i2c_command.py
    ├── driver_logger.py
    ├── sensor_info.py
    ├── serial_frame_builder.py
    ├── requirements.txt
    ├── Temp/ (Generated)
    │   ├── DataLog.csv
    │   └── DataLog.bin
    └── Logs/ (Generated)
        ├── logs.txt
        └── error_logs.txt
```

---


## 5. Running the data-acquisition system

This section describes how to start the Sensirion SLF3S-0600F data logger on a Raspberry Pi and keep it running in the background.

### 5.1 Clone the project

```bash
git clone https://github.com/OF306PUC/sensirion-SLF3S-0600F-python-driver.git
```

---

### 5.2 Go to the `raspberry/` directory

All scripts use implicit relative imports and **must be run from inside `raspberry/`**.

```bash
cd ~/sensirion-SLF3S-0600F-python-driver/raspberry
```

---

### 5.3 Install dependencies

```bash
pip install -r requirements.txt
```

---

### 5.5 Start the logger using `nohup`

The data logger can be executed in the background using `nohup`, allowing the process to continue running even after disconnecting from the SSH session.

```bash
nohup python3 main.py \
    --hours-to-log 12 \
    --sampling-ms 500 \
    > sensirion.log 2>&1 &
```

- All standard output and error messages are redirected to `sensirion.log`.
- The process **continues running after the SSH session is closed**.

---

### 5.6 Verify that the logger is running

```bash
pgrep -af main.py
```

Example output:

```
12345 python3 main.py --hours-to-log 12 --sampling-ms 500
```

---

### 5.7 Disconnect SSH safely

```bash
exit
```

The data logger will continue running on the Raspberry Pi until the specified logging time has elapsed.

---

## 6. Viewing logs and recorded data

### 6.1 View runtime log

```bash
tail -f sensirion.log
```

---

### 6.2 Access recorded data

Recorded CSV and binary files are stored in the generated `Temp/` directory:

```bash
ls Temp/
```

---

## 7. Command-line arguments configuration

| Argument | Type | Description | Default |
|--------|------|-------------|---------|
| `--port` | `str` | Serial port used to communicate with the SCC1-RS485 / SCC1-USB interface | `core.SERIAL_PORT` |
| `--baudrate` | `int` | Serial communication baud rate | `core.BAUDRATE` |
| `--slave-address` | `int` | SHDLC slave address of the SCC1 interface | `core.SLAVE_ADDRESS` |
| `--hours-to-log` | `float` | Total acquisition time, expressed in hours | `core.HOURS_TO_LOG` |
| `--sampling-ms` | `int` | Serial polling interval in milliseconds | `core.SAMPLING_INTERVAL` |

### Notes
- The serial polling interval `--sampling-ms` determines the effective serial read frequency  
  `f_rs = 1 / T_rs`.
- The effective sensor output rate is internally handled by the default command in the code `shdlc_command.py` and is configured by default to 10 Hz.