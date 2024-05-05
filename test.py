import csv
import glob
import re
import os

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
    #print("return response")
    # Print the response text
    #print(response.text)
    if response.status_code == 200:
        # Parse the JSON response
        response_data = response.json()
        # Access and return only the 'response' field from the JSON object
        response_text = response_data['response'] if 'response' in response_data else 'No response text found'
    else:
        response_text = f'Failed to get valid response, status code: {response.status_code}'

    print("return response")
    return response_text


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
    all_csv_content = ""  # Gesamter String mit allen Zeilen
    total_rows = 0  # Gesamtzahl der Zeilen in allen Dateien
    file_index = 1  # Beginne die Datei-Indexierung bei 1
    batches = {}  # Wörterbuch zum Speichern der 5er-Zeilen-Packs
    batch_index = 1  # Startindex für Batches

    # Durchlaufe die Liste der CSV-Dateien und lese deren Inhalt
    for csv_file in csv_files:
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)  # Verwende den CSV-Reader zum Verarbeiten der Datei
            header = next(reader)  # Speichere und überspringe den Header
            # Bestimme den Index der Spalte "Buchungstext"
            try:
                column_index = header.index('Buchungstext')
            except ValueError:
                column_index = None  # "Buchungstext" nicht gefunden

            current_batch = []  # Liste für das aktuelle 5er-Pack

            # Bearbeite jede Zeile, um die ID hinzuzufügen und "Buchungstext" zu ignorieren
            for line_number, row in enumerate(reader, start=1):
                if column_index is not None and column_index < len(row):
                    row.pop(column_index)  # Entferne die Spalte "Buchungstext"
                formatted_row = ','.join(row)
                id_line = f'{file_index}_{line_number}: {formatted_row}\n'
                all_csv_content += id_line  # Füge Zeile zum Gesamtstring hinzu
                current_batch.append(id_line)
                total_rows += 1

                # Wenn das aktuelle Batch 5 Zeilen erreicht, speichere es und beginne ein neues Batch
                if len(current_batch) == 5:
                    batches[batch_index] = current_batch
                    batch_index += 1
                    current_batch = []

            # Sicherstellen, dass auch das letzte Batch, das weniger als 5 Zeilen haben könnte, gespeichert wird
            if current_batch:
                batches[batch_index] = current_batch
                batch_index += 1

        file_index += 1  # Erhöhe die Datei-Indexierung für die nächste Datei

    print(f'Total rows across all files: {total_rows}')

    return all_csv_content, batches, total_rows


def single_request(prompt, stream=False, model="8b"):
    # print(f"Request: {prompt}")
    if stream:
        return stream_request(prompt, model)
    else:
        return nostream_request(prompt, model)


def request_clusters(content, model):
    output = single_request(
        f"{content}; each of these banktranctions has the format id|Auftragskonto|Buchungstag|Valutadatum|Buchungstext|Verwendungszweck|Glaeubiger ID|Mandatsreferenz|Kundenreferenz (End-to-End)|Sammlerreferenz|Lastschrift Ursprungsbetrag|Auslagenersatz Ruecklastschrift|Beguenstigter/Zahlungspflichtiger|Kontonummer/IBAN|BIC (SWIFT-Code)|Betrag|Waehrung|Info; use columns 'Beguenstigter/Zahlungspflichtiger' and 'Verwendungszweck' for categorizing the transactions in suitable kategories. give the categories; there are two type: income and expenses. focus on the expenses, for example shopping, restaurants, sport, etc..., create round about 20 categories and the tell me how many transactions are in each category, each transaction has to be in exactly one category, that means at the ende the summarized number of transaction each category has to be 486 ; just give me the categories, no further text",
        model=model)
    print(output)
    return output


'''def request_categorized_transactions(batches, model, categories):
    print(len(batches))
    print(batches.get(1))
    output = single_request(F"{batches.get(1)}; put each of those 5 banktransactions in the most suitable category of the following list: {categories}, ignore the numbers behing the caegories. one tránsaction has to be in exactly one category, give me as output 5 rows with category_id | transaction id (first value in each transactionstring, in the format int_int); give me no further text, begin and end my output with the string '*?*' so i can work with it; for example '*?*\n1|1_1\n2|1_2\n4|1_3\n17|1_4\n2|1_5\n*?*', give me exactly the same format )  ", model=model)
    print(output)
    
        for i in batches:
        print(batches.get(i))
    
'''


def request_categorized_transactions(batches, model, categories):
    final_output = ""  # String, der alle Ergebnisse sammelt
    for key, batch in batches.items():
        print(f"Processing batch {key}")
        formatted_batch = f"{batch}; put each of those 5 bank transactions in the most suitable category of the following list: {categories}, ignore the numbers behind the categories. one transaction has to be in exactly one category, transactions to the same destination should be in the same category except if it is a payment service as e.g. paypal, you can search for words in the purpose (6th and 13th value each time) of use which can give you a hint for the most suitable category, maybe the payee can also give you a hint, for example if it is a company, give me as output 5 rows with category_id | transaction id (first value in each transaction string, in the format int_int); give me no further text, begin and end my output with the string '*?*' so i can work with it; for example '*?*\n1|1_1\n2|1_2\n4|1_3\n17|1_4\n2|1_5\n*?*', give me exactly the same format."
        output = single_request(formatted_batch, model=model)  # Annahme, dass single_request die API-Anfrage handhabt
        cleaned_output = output.strip('*?*').strip()  # Entfernen der '*?*'
        final_output += cleaned_output + "\n"  # Hinzufügen des bereinigten Ergebnisses zum finalen String

    return final_output.strip()  # Rückgabe des finalen Strings ohne zusätzliche Leerzeilen am Ende


def result(categorized_string):
    # Entfernen aller Buchstaben (Groß- und Kleinbuchstaben)
    no_letters = re.sub(r'[a-zA-Z]', '', categorized_string)
    # Entfernen aller Inhalte nach einem Doppelpunkt (einschließlich des Doppelpunkts)
    no_colon_content = re.sub(r':.*', '', no_letters)
    # Entfernen von Klammern und deren Inhalten
    no_parentheses = re.sub(r'\(.*?\)', '', no_colon_content)
    # Entfernen aller unerwünschten Sonderzeichen, außer '|', '_'
    no_unwanted_chars = re.sub(r'[^|\d\n_]', '', no_parentheses)
    # Entfernen aller leeren Zeilen
    no_empty_lines = re.sub(r'\n\s*\n', '\n', no_unwanted_chars).strip()
    return no_empty_lines

def remove_before_first_number(text):
    # Suche nach der ersten Stelle, an der eine Zahl erscheint
    match = re.search(r'\d', text)
    if match:
        # Extrahiere alles ab dieser Stelle
        return text[match.start():]
    return text  # Falls keine Zahl gefunden wird, gebe den Originaltext zurück


def format_csv(categories_string, transactions_string, csv_data_string):
    # Kategorien extrahieren
    categories = {}
    for line in categories_string.split('\n'):
        match = re.match(r'(\d+)\.\s(.+)', line)
        if match:
            categories[match.group(1)] = match.group(2)

    # Transaktionszuordnungen extrahieren
    transaction_to_category_id = {}
    for line in transactions_string.split('\n'):
        if '|' in line:
            # Änderung hier, um sicherzustellen, dass die Zeile korrekt aufgeteilt wird
            cat_id, trans_id = line.split('|', 1)
            transaction_to_category_id[trans_id] = cat_id

    # CSV-Reader verwenden, um den CSV-String zu parsen und eine neue Spalte hinzuzufügen
    reader = csv.reader(csv_data_string.splitlines(), delimiter=';')
    result = []

    for row in reader:
        # Entferne den Präfix mit der ID (z.B. "1:")
        transaction_id = row[0].split(':')[0].strip()
        category_id = transaction_to_category_id.get(transaction_id, "Unknown")
        category_name = categories.get(category_id, "Unknown")
        # Füge die Kategorie als letztes Element hinzu
        row.append(category_name)
        result.append(';'.join(row))

    with open('output.csv', 'w', newline='') as file:
        writer = csv.writer(file, delimiter=';')
        for line in result:
            writer.writerow(line.split(';'))

    # Das Resultat als ein großer String
    result_string = '\n'.join(result)
    print(result_string)

if __name__ == '__main__':
    pull_model()
    csv_data = load_csv();
    model = "8b";
    categories = request_clusters(csv_data[0], model)
    cat = request_categorized_transactions(csv_data[1], model, categories);

    os.system('cls')  # Clear console
    print(categories)
    print('---------------------------------------' * 5)
    print(result(cat))
    print('---------------------------------------' * 5)
    format_csv(remove_before_first_number(categories), cat, csv_data[0])
#request(f"Cluster and categorize all the provided data representing bank transfers into a suitable number of categories with appropriate names. The final result should contain the categorized data in categories more based on purpose of use like Living, Restaurants, Shopping, etc..., not in categories based on date or amount or type of transaction : {load_csv()[0]}, just use columns 'Beguenstigter/Zahlungspflichtiger' and 'Verwendungszweck' for clustering; As Output first give me the categories whith each kategory_id and then give me all thransactions in the following format ordered by Kategory_id: Kategory_id | transaction_ID , the ID is the int at position 0 of each transaction string; do this for each of the {load_csv()[1]} transactions and give me the output for every transaction, every transaction has to be in exactly one category, you shouldnt simplify anything, dont short anything" , False, "8b")
#request("Why is the sky blue? answer short", True)
