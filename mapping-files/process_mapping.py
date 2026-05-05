import csv

DATASET_PREDICATES = {
    "datePublished": "P186072",
    "author": "P186069",
    "description": "P14",
    "citation": "P45087",
    "funding": "P49051",
    "keywords": "P186076",
    "Producer": "P45077",
    "measurementMethod": "P188083",
    "contributor": "P49016",
    "identifier": "P186081",
    "dateCreated": "P186079",
}

with open('metadata_hardcoded.csv', 'w', newline='') as csvwritefile:
    writer = csv.writer(csvwritefile, delimiter='#')
    for key in DATASET_PREDICATES:
        print(key + ": " + DATASET_PREDICATES[key])
        writer.writerow([key, DATASET_PREDICATES[key]])

DATASET_PREDICATES = {}

with open('darus-orkg.csv', newline='') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    for row in csvreader:
        DATASET_PREDICATES[row[3]] = row[4]

print("############## MAPPING ##############")

for key in DATASET_PREDICATES:
    print(key + ": " + DATASET_PREDICATES[key])

with open('metadata_generic.csv', 'w', newline='') as csvwritefile:
    writer = csv.writer(csvwritefile, delimiter='#')
    for key in DATASET_PREDICATES:
        print(key + ": " + DATASET_PREDICATES[key])
        writer.writerow([key, DATASET_PREDICATES[key]])
