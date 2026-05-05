# dataverse-orkg-python

A Python tool that imports datasets from [DaRUS](https://darus.uni-stuttgart.de) (the University of Stuttgart data repository) into the [Open Research Knowledge Graph (ORKG)](https://orkg.org).

## What it does

`main.py` connects to both a Dataverse instance and the ORKG, fetches a dataset by its DOI, maps the Dataverse metadata fields to ORKG predicates, and creates the corresponding resource graph in ORKG — including authors, keywords, funding agencies, measurement methods, contributors, and linked publications.

Related publications found in the Dataverse record are resolved via Crossref and added as proper ORKG paper resources. Citations without a DOI are added as plain paper resources with their citation text as label.

## Field mapping

The mapping between Dataverse and ORKG fields is defined in `mapping-files/darus-orkg.csv`:

| Dataverse field | ORKG predicate | Predicate ID |
|---|---|---|
| `publicationDate` | `datePublished` | P186072 |
| `title` | `title` | P184072 |
| `author` | `author` | P186069 |
| `dsDescription` | `description` | P14 |
| `publication` | `citation` | P45087 |
| `grantNumber` | `funding` | P49051 |
| `keyword` | `keywords` | P186076 |
| `producer` | `Producer` | P45077 |
| `processMethods` | `measurementMethod` | P188083 |
| `contributor` | `contributor` | P49016 |
| `dateOfDeposit` | `dateCreated` | P186079 |
| `persistentUrl` | `identifier` | P186081 |

## Setup

```bash
# Install dependencies (requires Python 3.13+)
uv sync
# or
pip install -r requirements.txt
```

Set the required environment variables:

```bash
export mail=your@email.com
export pw=yourpassword
export dataverseUrl=darus.uni-stuttgart.de
```

## Usage

Edit the `main()` call in `main.py` to point at the dataset DOI and an optional linked ORKG paper ID, then run:

```bash
python main.py
```

Example — import a DaRUS dataset and link it to an existing ORKG paper:

```python
add_dataset(client, dataverse, "doi:10.18419/DARUS-5015", "R2165000")
```

Pass `None` as the last argument to have the tool resolve related publications from the Dataverse record automatically via Crossref:

```python
add_dataset(client, dataverse, "doi:10.18419/DARUS-5015", None)
```

### Utility functions

| Function | Description |
|---|---|
| `print_orkg_datasets(client)` | List recent ORKG papers, search by keyword, and print statistics |
| `print_orkg_dataset(client, id, writefile)` | Fetch a single ORKG resource as JSON-LD |
| `print_dataverse_dataset(dataverse, pid, writefile)` | Fetch and print raw Dataverse dataset JSON |

## Sandbox setup

Some ORKG predicates used by this tool exist in production but may be missing from the sandbox. Run the helper script once to create them:

```bash
mail=your@email.com pw=yourpassword python create_missing_predicates.py
```

This creates predicates P186069, P186072, P186076, P186079, and P186081 in the ORKG sandbox if they are not already present.

## Project structure

```
main.py                       entry point and dataset import logic
orkgOperations.py             ORKG client wrapper (connect, read, write)
dataverseOperations.py        Dataverse API client
create_missing_predicates.py  one-time sandbox predicate setup
mapping-files/darus-orkg.csv  field mapping reference
```

## License

This project is licensed under the [MIT License](LICENSE).
