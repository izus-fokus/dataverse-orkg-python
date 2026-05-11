# dataverse-orkg-python

A Python tool that imports datasets from [DaRUS](https://darus.uni-stuttgart.de) (the University of Stuttgart data repository) into the [Open Research Knowledge Graph (ORKG)](https://orkg.org).

## What it does

`main.py` connects to both a Dataverse instance and the ORKG, fetches a dataset by its DOI, maps the Dataverse metadata fields to ORKG predicates, and creates the corresponding resource graph in ORKG — including authors, keywords, funding agencies, measurement methods, contributors, and linked publications.

Related publications found in the Dataverse record are resolved via Crossref and added as proper ORKG paper resources. Citations without a DOI are added as plain paper resources with their citation text as label.

## Field mapping

The mapping between Dataverse and ORKG fields is defined in `mapping-files/darus-orkg.csv`. `main.py` reads this file at startup to build four lookup tables — no hardcoded field logic in the code.

The `title` field is not in the mapping file; it is used directly as the ORKG dataset resource label.

| Dataverse field | `darusDatatype` | Darus subfield | ORKG predicate | Predicate ID | ORKG type |
|---|---|---|---|---|---|
| `publicationDate` | `data` | — | `datePublished` | P186072 | literal |
| `author` | `value` | `authorName` | `author` | P186069 | resource |
| `dsDescription` | `value` | `dsDescriptionValue` | `description` | P14 | literal |
| `publication` | `complex` | — | `citation` | P45087 | resource |
| `grantNumber` | `value` | `grantNumberAgency` | `funding` | P49051 | resource |
| `keyword` | `withsubvalue` | `keywordValue` | `keywords` | P3000 | resource |
| `keywordTermURI` | `keywordValue` | `keywordTermURI` | `keywords.SAME_AS` | SAME_AS | literal |
| `producer` | `value` | `producerName` | `Producer` | P45077 | resource |
| `processMethods` | `oneortwo` | `processMethodsName`, `processMethodsDescription` | `measurementMethod` | P188083 | literal |
| `contributor` | `value` | `contributorName` | `contributor` | P49016 | resource |
| `dateOfDeposit` | `fields` | — | `dateCreated` | P186079 | literal |
| `persistentUrl` | `data` | — | `identifier` | P186081 | literal |

### `darusDatatype` extraction strategies

The `darusDatatype` column (column 2) controls how `main.py` extracts the value for each row from the Dataverse API response:

| Value | Extraction behaviour |
|---|---|
| `data` | Read directly from the top-level `data` object in the Dataverse response (e.g. `data["publicationDate"]`). |
| `fields` | Read directly from the citation `fields` dict (e.g. `fields["dateOfDeposit"]`). |
| `value` | Compound field: iterate over all entries, extract the subfield named in the *Darus subfield* column and read its `.value`. HTML is stripped for `dsDescriptionValue`. |
| `oneortwo` | Compound field with one or two subfields listed in the *Darus subfield* column. The first subfield is required; if a second is present it is appended as `"name: description"`. |
| `withsubvalue` | Compound field whose primary value (the *Darus subfield*) is kept as the parent label, and whose URI is pulled from a paired sub-row whose `darusDatatype` equals the subfield name. Used for `keyword` ↔ `keywordTermURI` to build `{label: uri}` pairs for SAME_AS linking. |
| `complex` | Handled entirely outside the generic loop (currently `publication`, resolved via Crossref). |

### Supporting mapping files

| File | Description |
|---|---|
| `mapping-files/metadata_generic.csv` | ORKG name→ID index derived from `darus-orkg.csv` at generation time |
| `mapping-files/metadata_hardcoded.csv` | Same index as a hardcoded reference snapshot |
| `mapping-files/process_mapping.py` | Script that regenerates the two index CSVs from `darus-orkg.csv` |

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
main.py                                entry point and dataset import logic
orkgOperations.py                      ORKG client wrapper (connect, read, write); loads predicate mappings from CSV at startup
dataverseOperations.py                 Dataverse API client
create_missing_predicates.py           one-time sandbox predicate setup
mapping-files/darus-orkg.csv           primary field mapping (Dataverse → ORKG, with datatypes)
mapping-files/metadata_generic.csv     generated ORKG name→ID index (derived from darus-orkg.csv)
mapping-files/metadata_hardcoded.csv   hardcoded ORKG name→ID index (reference snapshot)
mapping-files/process_mapping.py       regenerates the two index CSVs from darus-orkg.csv
```

## License

This project is licensed under the [MIT License](LICENSE).
