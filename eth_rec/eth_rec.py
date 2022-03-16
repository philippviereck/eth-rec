import argparse
from glob import glob
import signal
import time
import datetime
import subprocess
from uuid import uuid4
import os

do_exit = False


def check_ffmpeg(hard):
    ffmpeg_available = True
    try:
        subprocess.check_output(['which', 'ffmpeg'])
    except Exception as e:
        ffmpeg_available = False
    if not ffmpeg_available:
        if hard:
            raise FileNotFoundError(
                "ffmpeg is required to be installed and in PATH")
        else:
            print(
                f"{bcolors.FAIL}[Warning] ffmpeg is not installed on this system, but required for this script to work!{bcolors.ENDC}")


class bcolors:
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def valid_time(s):
    try:
        return datetime.datetime.combine(datetime.datetime.now().date(), datetime.datetime.strptime(s, "%H:%M:%S").time())
    except ValueError:
        msg = "not a valid time: {0!r}".format(s)
        raise argparse.ArgumentTypeError(msg)


def valid_duration(s):
    try:
        return datetime.datetime.strptime(s, "%H:%M:%S").time()
    except ValueError:
        msg = "not a valid duration: {0!r} - format HH:MM:SS".format(s)
        raise argparse.ArgumentTypeError(msg)


def record(room, duration, outfile, file_format):
    global do_exit
    print(f"{bcolors.FAIL}• recording{bcolors.ENDC}  > {outfile}.{file_format}")
    try:
        p = subprocess.Popen(
            ['ffmpeg', '-i', f"https://oc-vp-livestreaming.ethz.ch/hls/{room}/index.m3u8", "-c", "copy", "-t", duration, "-loglevel", "24", f"{outfile}.{file_format}"])
        p.communicate()
    except(KeyboardInterrupt):
        do_exit = True
        if p != None:
            p.send_signal(signal.SIGINT)
        print("(CTRL-C)")


def main():
    print(
        f"{bcolors.FAIL}[INFO] DON'T ABUSE THIS TOOL. ALWAYS RESPECT THE COPYRIGHT! I AM NOT RESPONSIBLE FOR YOUR ACTIONS.{bcolors.ENDC}")

    check_ffmpeg(False)
    parser = argparse.ArgumentParser(
        description='Record an ETH Livestream - Using ffmpeg under the hood to download the HLS stream. The stream is openly available but sill copyrighted material!')
    parser.add_argument(
        '--output_file', '-o', required=False, help="The output file - e.g. recording.mp4 or lecture.mkv (.mkv is recommended, use VLC to view)", default=f"{uuid4()}.mkv")
    parser.add_argument('--room', "-r", type=str, required=True,
                        help=r"The lecture room - e.g. 'hg-f-7' (the room must support livestreaming)")
    parser.add_argument('--starttime', "-st", type=valid_time,
                        required=False, help="At what time (today) to start recording - format HH:MM:SS (default:Now)", default=datetime.datetime.now())

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--duration', "-d", type=valid_duration,
                       help="The duration for how long to record - format HH:MM:SS (Set either duration or end-time)")
    group.add_argument('--endtime', "-et", type=valid_time,
                       help="The time at which the recording should stop - format HH:MM:SS (Set either duration or end-time)")

    args = parser.parse_args()
    check_ffmpeg(True)

    room = args.room
    file_name = args.output_file.split(".")[0]
    file_format = args.output_file.split(".")[-1]
    start_time_date = args.starttime

    if args.duration is not None:
        duration = args.duration.isoformat()
        delta = datetime.timedelta(0, args.duration.second, 0, 0,
                                   args.duration.minute, args.duration.hour)
        end_time_date = datetime.datetime.combine(
            datetime.datetime.now().date(), start_time_date.time()) + delta

    elif args.endtime > start_time_date:
        end_time_date = args.endtime
        duration = (datetime.datetime.min +
                    (end_time_date - start_time_date)).time().isoformat()

    else:
        raise ValueError(f"{args.endtime} must be after {start_time_date}")

    if (end_time_date - start_time_date) < datetime.timedelta(seconds=1):
        raise ValueError(
            f"Duration must be at least 00:00:20 seconds. Your input: {duration}.")

    if datetime.datetime.now().time() > end_time_date.time():
        raise ValueError(
            f"the requested time-period has already passed")

    start = 1
    i = start

    _file_name = file_name
    if os.path.exists(f"{_file_name}.{file_format}"):
        while(os.path.exists(f"{_file_name}.{file_format}")):
            i += 1
            _file_name = f"{file_name}_{i}"

        print(
            f"{bcolors.WARNING}[Warning] renaming to '{_file_name}.{file_format}' {bcolors.ENDC}")

    start = i

    print("recording room '%s' is scheduled to start at %s" %
          (room.replace("-", " ").upper(), start_time_date.strftime("%H:%M:%S")))

    while(datetime.datetime.now() < start_time_date):
        time.sleep(1)

    MAX_RESTART = 5
    while(True and not do_exit):
        now = datetime.datetime.now()
        if now < (end_time_date - datetime.timedelta(seconds=2)):
            if(i > start):
                print(
                    f"{bcolors.WARNING}[Warning] Stopped before desired end-time. Restarting...{bcolors.ENDC}")

            if(i > MAX_RESTART):
                print(
                    f"{bcolors.WARNING}[Warning] Aborting. Max restart reached... there is probably something wrong with your arguments{bcolors.ENDC}")
                break

            duration_str = (datetime.datetime.min +
                            (end_time_date - now + datetime.timedelta(seconds=1))).time().isoformat()

            if(i > start):
                record(room, duration_str,
                       f"{file_name}_{i}", file_format)
            else:
                record(room, duration_str,
                       _file_name, file_format)
            i += 1
        else:
            break
