"""
Sensirion SHDLC Driver Module
- Runs a dual threaded architecture to handle SHDLC communication via serial port.
- Uses Sensirion SCC1-RS485 and SCC1-USB adapters for communication.
"""
from shdlc_command import ShdlcStartContinuousMeasurement, \
    ShdlcGetContinuousMeasurementStatus, ShdlcStopContinuousMeasurement
from i2c_command import ShdlcCmdI2cTransceive
from interface import ShdlcInterface
from port import ShdlcSerialPort
from utils import ErrorCodes

import os 
import time 
import struct
import core
import traceback
import queue as queue_module



def dual_logger(csv_filename, bin_filename, queue, end_of_infusion_detector, 
                logger, stop_logger_event, sampling_interval=core.SAMPLING_INTERVAL): 
    """
    Threaded CSV-binary logger for SHDLC sensor data.
    - Reads data from a queue and writes to CSV and binary files.
    - Integrates flow to compute volume in mL.
    """
    try: 
        flush_every_samples = core.FLUSH_EVERY 
        counter = 0
        integrated_volume = 0.0     # accumulated volume in uL

        start_t_utc = None
        end_t_utc = None

        os.makedirs(core.DATA_DIR, exist_ok=True)
        csv_path = os.path.join(core.DATA_DIR, csv_filename)
        bin_path = os.path.join(core.DATA_DIR, bin_filename)
        with open(csv_path, 'w') as f_csv, open(bin_path, 'wb') as f_bin: 
            f_csv.write("UTC_Time,Flow_ul_min,Volume_uL,DeviceTemperature_degC,"\
                    "Flag_Air,Flag_High_Flow,Exp_Smoothing,Flags_Value\n")
            
            while not stop_logger_event.is_set() or not queue.empty(): 
                try: 
                    item = queue.get(timeout=1.0)
                except queue_module.Empty:
                    continue
                timestamp, flow_raw, temp_raw, flags_raw = item

                if start_t_utc is None:
                    start_t_utc = timestamp
                
                flow_uL_min, temp_c = core.interpret_flow_temp_raw(flow_raw, temp_raw)
                flag_air, flag_high_flow, exp_smoothing, flags_value = core.interpret_flags_raw(flags_raw)
                integrated_volume += (flow_uL_min * core.MIN_TO_SEC) * (sampling_interval / 1000.0)

                flow_raw = core.u16_to_i16(flow_raw)
                temp_raw = core.u16_to_i16(temp_raw)

                if end_of_infusion_detector.update(timestamp=timestamp, flow_ulmin=flow_uL_min):
                    end_t_utc = timestamp
                    logger.log(
                        f"End-of-infusion detected. Stopping. "\
                        f"start_utc={start_t_utc}, end_utc={end_t_utc}, volume_uL={integrated_volume:.2f}", 
                        context={
                            "duration_s": end_t_utc - start_t_utc if start_t_utc and end_t_utc else None,
                            "integrated_volume_uL": integrated_volume
                        }
                    )
                    stop_logger_event.set()

                # Write CSV record:
                f_csv.write(f"{timestamp},{flow_uL_min:.4f},{integrated_volume:.4f},{temp_c:.4f}"
                        f",{flag_air},{flag_high_flow},{exp_smoothing},{flags_value}\n")
                # Write binary record: 
                f_bin.write(struct.pack(core.BIN_RECORD_FMT, timestamp, \
                                        flow_raw, temp_raw, flags_raw))
                counter += 1
                if counter % flush_every_samples == 0: 
                    f_csv.flush()
                    f_bin.flush()

    except Exception as e:
        logger.log_error(
            ErrorCodes.LOGGER_FAILURE, 
            f"Logger encountered an exception: {e}",
            context=traceback.format_exc(),
        )
        stop_logger_event.set()


def in_device_communication(
        port, baudrate, queue, slave_address, logger, ring_buffer, stop_logger_event,
        stop_main_thread_event, hours_to_log=core.HOURS_TO_LOG, sampling_interval=core.SAMPLING_INTERVAL): 
    """
    Threaded SHDLC device communication via serial port.
    - Reads data from the SHDLC device and puts it into a queue.
    """
    with ShdlcSerialPort(port=port, baudrate=baudrate) as shdlc_port:
        interface = ShdlcInterface(port=shdlc_port)

        # Stopping continuous measurement 
        i2c_transceive_stop_cmd = ShdlcStopContinuousMeasurement(
            stop_code=ShdlcStopContinuousMeasurement._I2C_STOP_CODE
        )
        _, error  = interface.execute(slave_address, i2c_transceive_stop_cmd)
        print("--- (1) Stopping continuous measurement ---")
        if error: 
            print("Error state from stop command:", error)
        print("")
        time.sleep(1)

        # I2C Transceive command to start continuous measurement
        i2c_transceive_start_cmd = ShdlcStartContinuousMeasurement(
            measurement_interval=ShdlcStartContinuousMeasurement._MEASUREMENT_INTERVAL_100_MS,
            i2c_medium_command=ShdlcStartContinuousMeasurement._I2C_MEAS_CMD_MEDIUM_WATER
        )
        _, error  = interface.execute(slave_address, i2c_transceive_start_cmd)
        print("--- (2) Starting continuous measurement ---")
        if error: 
            print("Error state from start command:", error)
        print("")
        time.sleep(1)

        # I2C Transceive command to check continuous measurement status
        i2c_transceive_status_cmd = ShdlcGetContinuousMeasurementStatus()
        status_data, error  = interface.execute(slave_address, i2c_transceive_status_cmd)
        print("--- (3) Continuous Measurement Status ---")
        print("Status data received - measurement interval [ms]:", status_data)
        if error: 
            print("Error state from status command:", error)
        print("")
        time.sleep(1)

        # Read measurement data in a loop
        i2c_header = (ShdlcCmdI2cTransceive._I2C_ADDRESS << 1) | \
                ShdlcCmdI2cTransceive._READ_BIT 
        transceive_cmd = ShdlcCmdI2cTransceive(
            i2c_addr=ShdlcCmdI2cTransceive._I2C_ADDRESS,
            i2c_timeout=ShdlcCmdI2cTransceive._I2C_TIMEOUT_MS,
            tx_data=[i2c_header],       # Read measurement command
            rx_length=9,                # 9 bytes max for SLF3S-0600F sensor
            max_response_time=0.1
        )  

        seconds_to_log = 3600 * hours_to_log
        num_measurements = int(seconds_to_log * 1000 // sampling_interval)
        print(f"Logging for {hours_to_log} hours, sampling interval: {sampling_interval} ms,"\
              f" total measurements: {num_measurements}")
        measurement_count = 0
        time.sleep(1)

        try: 

            deadline = time.time()
            while not stop_logger_event.is_set(): 
                if measurement_count > num_measurements:
                    stop_logger_event.set()
                
                deadline += sampling_interval / 1000
                # reading data from sensor: 
                # data is: (flow_ul_min, temp_c, flag_air, flag_high_flow, exp_smoothing)
                data, error = interface.execute(slave_address, transceive_cmd)    
                if error: 
                    logger.log_error(
                        ErrorCodes.SHDLC_ERROR_STATE,
                        "Error state received during measurement read.",
                        context=ring_buffer.snapshot()
                    )
                    print("Error state received during measurement read.")
                    continue

                flow_raw, temp_raw, flags_raw = data
                timestamp = time.time()
                item = (float(timestamp), int(flow_raw), int(temp_raw), int(flags_raw))
                ring_buffer.push(item)

                try: 
                    queue.put(item, timeout=1.0)
                except queue_module.Full:
                    logger.log_error(
                        ErrorCodes.QUEUE_FULL,
                        "Data queue is full. Dropping measurement.", 
                        context=ring_buffer.snapshot()
                    )
                    print("Warning: Data queue is full. Dropping measurement.")

                t_now = time.time()
                sleep_time = deadline - t_now
                missed = 0
                if sleep_time > 0: 
                    time.sleep(sleep_time)
                else:
                    missed = int(-sleep_time / (sampling_interval / 1000)) + 1
                    deadline += missed * (sampling_interval / 1000)
                    logger.log_error(
                        ErrorCodes.COMMUNICATION_FAILURE,
                        f"Sampling overrun: {-sleep_time*1000:.1f} ms late, missed {missed} sample(s)",
                    )

                measurement_count += (1 + missed)

        except Exception as e:
            logger.log_error(
                ErrorCodes.COMMUNICATION_FAILURE,
                f"Exception in device communication thread (crashed): {e}",
                context=traceback.format_exc(),
            )

        finally: 
            # Send stop command before ending
            _, error  = interface.execute(slave_address, i2c_transceive_stop_cmd)
            print("--- Stopping continuous measurement (shutdown) ---")
            if error: 
                print("Error state from stop command:", error)
            stop_main_thread_event.set()        
            
