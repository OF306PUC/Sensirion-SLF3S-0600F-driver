from utils import EndOfInfusionDetector, Logger, MeasurementRingBuffer
from shdlc_driver import dual_logger, in_device_communication

import argparse
import signal 
import core
import queue as queue_module
import threading
import time

stop_logger_event = threading.Event()
stop_main_thread_event = threading.Event()
def handle_shutdown(signum, frame): 
    print("Shutdown signal received. Stopping threads...")
    stop_logger_event.set()
    stop_main_thread_event.set()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sensirion SHDLC data logger"
    )
    parser.add_argument("--port", type=str, default=core.SERIAL_PORT,
        help=f"Serial port (default: {core.SERIAL_PORT})"
    )
    parser.add_argument("--baudrate", type=int, default=core.BAUDRATE,
        help=f"Serial port baudrate (default: {core.BAUDRATE})"
    )
    parser.add_argument("--slave-address", type=int, default=core.SLAVE_ADDRESS,
        help=f"SHDLC slave address (default: {core.SLAVE_ADDRESS:#04x})"
    )
    parser.add_argument("--hours-to-log", type=float, default=core.HOURS_TO_LOG,
        help=f"Number of hours to log data (default: {core.HOURS_TO_LOG})"
    )
    parser.add_argument("--sampling-ms", type=int, default=core.SAMPLING_INTERVAL,
        help=f"Sampling interval in milliseconds (default: {core.SAMPLING_INTERVAL})"
    )
    return parser, parser.parse_args()


def main():
    parser, args = parse_args()

    serial_port = args.port
    baudrate = args.baudrate
    slave_address = args.slave_address
    hours_to_log = args.hours_to_log
    sampling_interval_ms = args.sampling_ms

    if hours_to_log <= 0: 
        parser.error("--hours-to-log must be a positive number.")
        return args
    if sampling_interval_ms <= 0: 
        parser.error("--sampling-ms must be a positive integer.")
        return args

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    queue_process = queue_module.Queue(maxsize=core.QUEUE_MAXSIZE)
    detector = EndOfInfusionDetector(
        window_size=core.EoI_WINDOW_SIZE, hold_sec=core.EoI_HOLD_SEC, 
        rms_flow_ulmin_threshold=core.EoI_RMS_FLOW_ULMIN_THRESHOLD
    )
    logger = Logger(path=core.LOGGER_PATH)
    ring_buffer = MeasurementRingBuffer(max_size=core.BUFF_QUEUE_MAXSIZE)

    t_comm = threading.Thread(
        target=in_device_communication,
        args=(
            serial_port, baudrate, queue_process, slave_address,
            logger, ring_buffer, stop_logger_event, stop_main_thread_event, 
            hours_to_log, sampling_interval_ms
        ),
        daemon=True,
    )
    t_logger = threading.Thread(
        target=dual_logger,
        args=("DataLog.csv", "DataLog.bin", queue_process, detector,
              logger, stop_logger_event, sampling_interval_ms),
        daemon=True,
    )

    t_comm.start()
    t_logger.start()

    while not stop_main_thread_event.is_set(): 
        time.sleep(1)


if __name__ == "__main__":
    main()
