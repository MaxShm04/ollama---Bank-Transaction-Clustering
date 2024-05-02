import glob

import requests
import subprocess
import json

INPUT_DATA_DIRECTORY = 'data/'
INPUT_DATA_FILE_PATTERN = '*.csv'


# Pulling the model
def pull_model():
    # Data to be sent in POST request
    data = {"model": "llama3"}
    # Convert dictionary to JSON string
    data_str = json.dumps(data)
    # Construct the curl command using proper shell arguments
    cmd = ['curl', '-X', 'POST', 'http://localhost:11434/api/pull', '-d', data_str]
    # Execute the curl command using subprocess with proper argument passing
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if error:
        print("Error:", error.decode())
    else:
        print("Output:", output.decode())
    print("Running llama3 successful")


# Pull the model

def nostream_request(prompt, model):
    print("start requesting")
    # URL for the POST request
    url = 'http://localhost:11434/api/generate'

    # Data for the POST request
    data = {
        "model": f"llama3:{model}",
        "prompt": prompt,
        "stream": False  # Setting 'stream' to False if you want to mimic a non-streaming request as typical in curl
    }

    # Headers to specify JSON content type
    headers = {'Content-Type': 'application/json'}

    # Sending the POST request
    response = requests.post(url, json=data, headers=headers)

    print("response status:", response.status_code)  # Check and print the status code of the response
    print("return response")
    # Print the response text
    return response.text


def stream_request(prompt, model):
    print("Start streaming request")
    # URL für den POST-Request
    url = 'http://localhost:11434/api/generate'

    # Daten für den POST-Request
    data = {
        "model": f"llama3:{model}",
        "prompt": prompt
        # 'stream': True ist default, daher muss es nicht explizit gesetzt werden.
    }

    # Header für den Request, um zu spezifizieren, dass es sich um JSON-Daten handelt
    headers = {'Content-Type': 'application/json'}

    # Schicken des POST-Requests mit Stream-Option
    with requests.post(url, json=data, headers=headers, stream=True) as response:
        # Überprüfen, ob der Request erfolgreich war
        if response.status_code == 200:
            for line in response.iter_lines():
                # Streamed lines filtern, die leer sind
                if line:
                    decoded_line = line.decode('utf-8')
                    json_response = json.loads(decoded_line)  # Die Zeile als JSON laden
                    print(json_response)  # JSON-Antwort ausgeben
        else:
            print(f"Error with status code: {response.status_code}")


def load_csv():
    data_folder_path = 'data/'
    csv_files = glob.glob(f'{data_folder_path}*.csv')
    print(csv_files)
    all_csv_content = ""

    # Loop through the list of CSV files and read their contents
    for csv_file in csv_files:
        with open(csv_file, 'r') as file:
            # Read the current CSV file's content and add it to the accumulator string
            all_csv_content += file.read() + "\n\n"  # Added newlines to separate content of different files
    return all_csv_content


def request(prompt, stream=False, model="8b"):
    pull_model()
    print(f"Request: {prompt}")
    if stream:
        stream_request(prompt, model)
    else:
        nostream_request(prompt, model)

request(f"Cluster and categorize all the provided data representing bank transfers into a suitable number of categories with appropriate names. The final result should contain the categorized data in categories more based on purpose of use like Living, Restaurants, Shopping, etc..., not in categories based on date or amount or type of transaction : {load_csv()}", True)
#request("Why is the sky blue? answer short", True)