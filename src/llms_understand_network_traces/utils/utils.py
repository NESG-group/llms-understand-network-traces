import json
import subprocess
from datetime import datetime, timezone, timedelta

# Function to save data as JSON
def saveJsonToFile(data, file_name):
    with open(file_name, "w") as file:
        json.dump(data, file, indent=4) 

# Function to filter out a time range from a pcap file
def filter_pcap_time_range(input_file, start_time, end_time, output_file):
    """
    Filters packets from a pcap file based on a time range using tshark and writes them to a new pcap file.
    
    Parameters:
        input_file (str): Path to the input pcap file.
        start_time (float): Start time (inclusive) as a Unix epoch timestamp.
        end_time (float): End time (inclusive) as a Unix epoch timestamp.
        output_file (str): Path to the output pcap file.
    """
    # Construct the display filter using tshark’s syntax.
    # Note: frame.time_epoch represents the packet timestamp in seconds.
    display_filter = f"frame.time_epoch >= {start_time} and frame.time_epoch <= {end_time}"
    
    # Build the tshark command:
    # -r: input file
    # -Y: apply a display filter
    # -w: write the filtered packets to an output file
    cmd = [
        "tshark",
        "-r", input_file,
        "-Y", display_filter,
        "-w", output_file
    ]
    print("Executing command:", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("Command succeeded with output:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error executing command:")
        print("Return code:", e.returncode)
        print("Standard Output:", e.stdout)
        print("Standard Error:", e.stderr)

def convert_to_epoch(date_str):
    """
    Converts a date string in the format "Wed-14-02-2018 10:32" (UTC-5) to epoch time.

    Parameters:
        date_str (str): The date string in the format "%a-%d-%m-%Y %H:%M".
    
    Returns:
        float: The corresponding epoch time.
    """
    # Parse the date string. %a matches the abbreviated weekday (e.g., Wed),
    # %d is day, %m is month, %Y is year, %H:%M is hour:minute.
    dt = datetime.strptime(date_str, "%a-%d-%m-%Y %H:%M")
    
    # Define the timezone for UTC-5.
    utc_minus_5 = timezone(timedelta(hours=-5))
    
    # Attach the timezone information to the datetime object.
    dt = dt.replace(tzinfo=utc_minus_5)
    
    # Convert the datetime object to epoch time (timestamp in seconds).
    epoch_time = dt.timestamp()
    return epoch_time