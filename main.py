import json
import os
import re
from html.parser import HTMLParser
from orkg.common import Hosts
from orkgOperations import OrkgOperations
from dataverseOperations import DataverseOperations


def strip_html(text: str) -> str:
    class _Stripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self._parts = []

        def handle_data(self, data):
            self._parts.append(data)

    stripper = _Stripper()
    stripper.feed(text)
    plain = " ".join(stripper._parts)
    return re.sub(r"\s+", " ", plain).strip()

pw = os.environ['pw']
mail = os.environ['mail']

# apikey = os.environ['apikey']
dataverseUrl = os.environ['dataverseUrl']

def print_orkg_datasets(client):
    # --- Retrieve recent papers ---
    print("\n=== Recent papers (first 5) ===")
    papers = client.get_papers(size=5)
    client.print_papers(papers)

    # --- Search papers by title keyword ---
    search_term = "machine learning"
    print(f"\n=== Papers matching '{search_term}' (first 5) ===")
    found = client.get_papers(title=search_term, size=5)
    client.print_papers(found)

    # --- Fetch a specific paper by ID ---
    # R3000 is a real paper in the production ORKG.
    paper_id = "R3000"
    print(f"\n=== Paper by ID: {paper_id} ===")
    paper = client.get_paper_by_id(paper_id)
    with open("paper.json", "a") as f:
        if paper:
            print(json.dumps(paper, indent=2, default=str))
            f.write(json.dumps(paper, indent=2, default=str))

    # --- Retrieve resources matching a label ---
    print("\n=== Resources matching 'neural network' (first 5) ===")
    resources = client.get_resources(query="neural network", size=5)
    for res in resources:
        print(f"  [{res.get('id')}] {res.get('label')}")

    # --- Stats ---
    # The statistics API uses a HATEOAS-style structure; fetch each count separately.
    print("\n=== ORKG Stats ===")
    import requests as _req
    _base = "https://orkg.org/api/statistics"
    for label, path in [("Papers", "content-types/paper-count"), ("Resources", "things/resource-count"),
        ("Statements", "things/statement-count"), ]:
        try:
            val = _req.get(f"{_base}/{path}", timeout=5).json().get("value", "?")
            print(f"  {label:<12}: {val:,}" if isinstance(val, int) else f"  {label:<12}: {val}")
        except Exception:
            print(f"  {label:<12}: (unavailable)")


def print_orkg_dataset(client, id, writefile):
    # --- Fetch a specific paper by ID ---
    # R3000 is a real paper in the production ORKG.
    resource_id = id
    print(f"\n=== Resource by ID: {resource_id} ===")
    dataset = client.get_resource_as_jsonld(resource_id)
    if writefile:
        with open("paper.json", "w") as f:
            if dataset:
                print(json.dumps(dataset, indent=2, default=str))
                f.write(json.dumps(dataset, indent=2, default=str))
    else:
        print(json.dumps(dataset, indent=2, default=str))


def print_dataverse_dataset(dataverse, pid, writefile):


    datasetJson = dataverse.get_dataset(pid)

    if writefile:
        with open("dataverse.json", "w") as f:
            if datasetJson:
                print(json.dumps(datasetJson, indent=2, default=str))
                f.write(json.dumps(datasetJson, indent=2, default=str))
    else:
        print(json.dumps(datasetJson, indent=2, default=str))

def add_dataset(client, dataverse, dvDOI, publication):
    dvJson = dataverse.get_dataset(dvDOI)
    data = dvJson.get("data", {})
    latest = data.get("latestVersion", {})
    citation_fields = latest.get("metadataBlocks", {}).get("citation", {}).get("fields", [])

    fields = {f["typeName"]: f["value"] for f in citation_fields}

    title = fields.get("title", "")

    descriptions = [
        item["dsDescriptionValue"]["value"]
        for item in fields.get("dsDescription", [])
        if item.get("dsDescriptionValue", {}).get("value")
    ]
    description = "\n".join(strip_html(d) for d in descriptions)

    authors = [
        {"name": item["authorName"]["value"].strip()}
        for item in fields.get("author", [])
        if item.get("authorName", {}).get("value", "").strip()
    ]

    keywords = [
        item["keywordValue"]["value"].strip()
        for item in fields.get("keyword", [])
        if item.get("keywordValue", {}).get("value", "").strip()
    ]

    funding = [
        {"agency": item["grantNumberAgency"]["value"].strip()}
        for item in fields.get("grantNumber", [])
        if item.get("grantNumberAgency", {}).get("value", "").strip()
    ]

    producers = [
        item["producerName"]["value"].strip()
        for item in fields.get("producer", [])
        if item.get("producerName", {}).get("value", "").strip()
    ]

    methods = []
    for item in fields.get("processMethods", []):
        name = item.get("processMethodsName", {}).get("value", "").strip()
        desc = item.get("processMethodsDescription", {}).get("value", "").strip()
        if name:
            methods.append(f"{name}: {desc}" if desc else name)

    contributors = [
        {"name": item["contributorName"]["value"].strip()}
        for item in fields.get("contributor", [])
        if item.get("contributorName", {}).get("value", "").strip()
    ]

    publication_date = data.get("publicationDate", "")
    deposit_date = fields.get("dateOfDeposit", "")
    identifier = data.get("persistentUrl", dvDOI)

    citations = []
    if publication is None:
        related_publications = []
        for item in fields.get("publication", []):
            citation_text = item.get("publicationCitation", {}).get("value", "").strip()
            url = item.get("publicationURL", {}).get("value", "").strip()
            id_type = item.get("publicationIDType", {}).get("value", "").strip()
            id_number = item.get("publicationIDNumber", {}).get("value", "").strip()
            if not citation_text:
                continue
            if id_type.lower() == "doi" and id_number:
                paper_id = client.add_paper_from_doi(id_number)
                if paper_id:
                    related_publications.append(paper_id)
                    continue
            citations.append({"citation": citation_text, "url": url, "id_type": id_type, "id_number": id_number})
        client.add_dataset({
            "title": title,
            "description": description,
            "identifier": identifier,
            "publication_date": publication_date,
            "deposit_date": deposit_date,
            "keywords": keywords,
            "authors": authors,
            "funding": funding,
            "producers": producers,
            "measurement_methods": methods,
            "contributors": contributors,
            "citations": citations,
            "related_publications": related_publications,
        })
    else:
        client.add_dataset(
            {"title": title, "description": description, "identifier": identifier, "publication_date": publication_date,
             "deposit_date": deposit_date, "keywords": keywords, "authors": authors, "funding": funding,
             "producers": producers, "measurement_methods": methods, "contributors": contributors,
             "related_publication": publication, })

def main():
    client = OrkgOperations(mail, pw, Hosts.SANDBOX)

    dataverse = DataverseOperations(dataverseUrl)

    add_dataset(client,dataverse,"doi:10.18419/DARUS-4620",None)

    # print_orkg_datasets(client)

    # print_orkg_dataset(client,"R2164143",True)
    #
    # print_dataverse_dataset(dataverse,"doi:10.18419/DARUS-5526",False)




if __name__ == "__main__":
    main()
