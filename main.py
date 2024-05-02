import os
import glob
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import kmodes.kprototypes

import data.merchant_normalization_mapping_expressions

INPUT_DATA_DIRECTORY = 'data/'
INPUT_DATA_FILE_PATTERN = '*.csv'

COLUMN_NAMES = ['Buchungsdatum', 'Wertstellung', 'Status', 'Zahlungspflichtige', 'Zahlungsempfänger*in',
                'Verwendungszweck', 'Umsatztyp', 'IBAN', 'Betrag (€)', 'Gläubiger-ID', 'Mandatsreferenz',
                'Kundenreferenz']
COLUMNS_TO_USE = ['Zahlungsempfänger*in', 'Verwendungszweck']

NUMBER_OF_CLUSTERS = 6

os.chdir(INPUT_DATA_DIRECTORY)


def load_input_data():
    # Load each file in the input data directory into a dataframe.
    data_frames = [load_input_file_data_set(file_path=input_data_file) for input_data_file in
                   glob.glob(INPUT_DATA_FILE_PATTERN)]

    # Merge each files' dataframe into one.
    return pd.concat(
        data_frames,
        axis=0,  # Merge along row axis.
        ignore_index=True
    )


def load_input_file_data_set(file_path):
    data_frame = pd.read_csv(
        file_path,
        header=None,
        names=COLUMN_NAMES,
        usecols=COLUMNS_TO_USE,
        engine='python',
        sep=';',
        thousands='.',
        decimal=',',
        skiprows=1,
        encoding='utf-8'
    )

    # Files are in reverse chronological order; flip them.
    data_frame = data_frame.reindex(index=data_frame.index[::-1])

    return data_frame


# Returns two versions of the data frame, one with categorical features one-hot
# encoded, and one without. Use the former within the model, but keep the latter
# for inspecting the results, as it's more readable.
def pre_process_data_set(data_frame):
    data_frame['Zahlungsempfänger*in'].replace(
        regex=data.merchant_normalization_mapping_expressions.MERCHANT_NORMALIZATION_MAPPING_EXPRESSIONS,
        inplace=True
    )

    # Insert the Transaction Type feature.
    data_frame['Transaction Type'] = data_frame['Zahlungsempfänger*in'].map(
        data.merchant_normalization_mapping_expressions.MERCHANT_TRANSACTION_TYPE_MAPPINGS)

    # One-hot encode the Merchant and Transaction Type columns.
    categorized_data_frame = pd.get_dummies(
        data_frame,
        columns=['Zahlungsempfänger*in', 'Transaction Type', 'Verwendungszweck'],
        sparse=False
    )

    return data_frame, categorized_data_frame


data_frame = load_input_data()

data_frame, categorized_data_frame = pre_process_data_set(data_frame)

model = kmodes.kprototypes.KPrototypes(
    n_clusters=NUMBER_OF_CLUSTERS,
    init='Huang',
    verbose=1
)

clusters = model.fit_predict(
    categorized_data_frame,
    categorical=list(range(1, categorized_data_frame.shape[1]))
    # Index of columns that contain categorical data. All columns in the dataframe except the first.
)

# Insert the clusters into the dataframe.
data_frame = data_frame.assign(Cluster=pd.Series(clusters).values)

# Print the clusters and their transactions.
for cluster, cluster_data_frame in data_frame.groupby('Cluster'):
    print('Cluster: ' + str(cluster))
    for index, transaction in cluster_data_frame.iterrows():
        print(
            f"  Zahlungsempfänger: {transaction['Zahlungsempfänger*in']:<10} Verwendungszweck: {transaction['Verwendungszweck']:<30}  Transaction type: {transaction['Transaction Type']:<18}")

# Füllen Sie fehlende Werte im kategorisierten DataFrame mit Nullen aus, um Fehler bei der Verarbeitung zu vermeiden.
categorized_data_frame.fillna(0, inplace=True)

# Anwenden von t-SNE zur Dimensionsreduktion, um die Cluster in einem zweidimensionalen Raum darzustellen.
tsne = TSNE(n_components=2, perplexity=30, n_iter=300)
tsne_results = tsne.fit_transform(categorized_data_frame)
data_frame['t-SNE1'] = tsne_results[:, 0]
data_frame['t-SNE2'] = tsne_results[:, 1]

# Visualisierung der t-SNE-Ergebnisse.
plt.figure(figsize=(10, 8))
sns.scatterplot(x='t-SNE1', y='t-SNE2', hue='Cluster', data=data_frame, palette='hsv', legend='full', alpha=0.7)
plt.title('Visualisierung der Cluster mit t-SNE')
plt.xlabel('t-SNE Achse 1')
plt.ylabel('t-SNE Achse 2')
plt.show()

# Anwenden von PCA auf das kategorisierte DataFrame zur weiteren Dimensionsreduktion.
pca = PCA(n_components=2)
pca_results = pca.fit_transform(categorized_data_frame)
data_frame['PCA1'] = pca_results[:, 0]
data_frame['PCA2'] = pca_results[:, 1]

# Visualisierung der PCA-Ergebnisse.
plt.figure(figsize=(10, 8))
sns.scatterplot(x='PCA1', y='PCA2', hue='Cluster', data=data_frame, palette='viridis', legend='full')
plt.title('PCA Visualisierung der Cluster')
plt.xlabel('Hauptkomponente 1')
plt.ylabel('Hauptkomponente 2')
plt.show()


def find_optimal_number_of_clusters(data):
    wcss = []
    silhouette_coefficients = []
    for k in range(2, 11):
        kproto = kmodes.kprototypes.KPrototypes(n_clusters=k, init='Huang', n_jobs=-1, verbose=1)
        kproto.fit_predict(data, categorical=list(range(1, data.shape[1])))
        wcss.append(kproto.cost_)
        silhouette_coefficients.append(silhouette_score(data, kproto.labels_))

    # Elbow-Plot zeichnen
    plt.figure(figsize=(10, 8))
    plt.plot(range(2, 11), wcss, marker='o', linestyle='-')
    plt.title('Elbow-Methode für die Bestimmung der optimalen Clusteranzahl')
    plt.xlabel('Anzahl der Cluster')
    plt.ylabel('WCSS')
    plt.show()

    # Silhouette-Plot zeichnen
    plt.figure(figsize=(10, 8))
    plt.plot(range(2, 11), silhouette_coefficients, marker='o', linestyle='-')
    plt.title('Silhouette-Koeffizienten für verschiedene Clusteranzahlen')
    plt.xlabel('Anzahl der Cluster')
    plt.ylabel('Silhouette-Koeffizient')
    plt.show()

    # Optimalen Wert zurückgeben basierend auf Silhouette-Koeffizienten
    optimal_k = range(2, 11)[silhouette_coefficients.index(max(silhouette_coefficients))]
    return optimal_k


# Anwenden der Funktion auf Ihre Daten
optimal_number_of_clusters = find_optimal_number_of_clusters(categorized_data_frame)

# Ausgeben der optimalen Clusteranzahl
print('Die optimale Anzahl an Clustern basierend auf der Elbow-Methode und Silhouette-Koeffizienten ist:',
      optimal_number_of_clusters)

# Führen Sie das K-Prototypes-Clustering mit der optimalen Anzahl von Clustern durch
optimal_model = kmodes.kprototypes.KPrototypes(
    n_clusters=optimal_number_of_clusters,
    init='Huang',
    verbose=1
)

# Fügen Sie diese Zeilen hinzu, um mit der optimalen Anzahl von Clustern zu arbeiten
optimal_clusters = optimal_model.fit_predict(
    categorized_data_frame,
    categorical=list(range(1, categorized_data_frame.shape[1]))
)

# Fügen Sie die optimalen Cluster dem DataFrame hinzu und visualisieren Sie die Ergebnisse
data_frame['Optimal_Cluster'] = optimal_clusters

# Visualisierung der PCA-Ergebnisse mit den optimalen Clustern.
plt.figure(figsize=(10, 8))
sns.scatterplot(x='PCA1', y='PCA2', hue='Optimal_Cluster', data=data_frame, palette='viridis', legend='full')
plt.title('PCA Visualisierung der optimalen Cluster')
plt.xlabel('Hauptkomponente 1')
plt.ylabel('Hauptkomponente 2')
plt.show()

#export csv
# Eine leere Liste, um die Daten aller Cluster zu sammeln
cluster_data = []

# Gruppieren der Daten nach dem Cluster und Bearbeitung jedes Clusters
for cluster, cluster_data_frame in data_frame.groupby('Cluster'):
    # Auswahl der relevanten Spalten
    selected_columns = cluster_data_frame.loc[:, ['Zahlungsempfänger*in', 'Verwendungszweck', 'Transaction Type']]
    # Hinzufügen der Cluster-Spalte zum DataFrame
    selected_columns['Cluster'] = cluster
    # Hinzufügen des bearbeiteten DataFrames zur Liste
    cluster_data.append(selected_columns)

# Zusammenführen aller Cluster-Daten in einem einzigen DataFrame
all_clusters_data_frame = pd.concat(cluster_data, ignore_index=True)

# Speichern in CSV
csv_path = "../Clustered_Transactions.csv"
all_clusters_data_frame.to_csv(csv_path, index=False, sep=';', encoding='utf-8')


print('Die optimale Anzahl an Clustern basierend auf der Elbow-Methode und Silhouette-Koeffizienten ist:',
      optimal_number_of_clusters)