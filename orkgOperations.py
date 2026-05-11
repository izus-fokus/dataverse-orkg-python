import csv
import json
import sys
import requests
from orkg import ORKG
DATASET_PREDICATES = {}
with open('mapping-files/darus-orkg.csv', newline='') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    for row in csvreader:
        DATASET_PREDICATES[row[3]] = row[4]

DATASET_TYPE_PREDICATES = {}
with open('mapping-files/darus-orkg.csv', newline='') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    for row in csvreader:
        DATASET_TYPE_PREDICATES[row[3]] = row[5]

DATASET_PREDICATES_SUBFIELDS = {}
with open('mapping-files/darus-orkg.csv', newline='') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    for row in csvreader:
        DATASET_PREDICATES_SUBFIELDS[row[3]] = row[6]

class OrkgOperations:

    def __init__(self, email, password, host) -> None:
        self.orkg = self.connect(email, password, host)

    def connect(self, email: str = None, password: str = None, host: str = None) -> ORKG:
        """
        Connect to self.orkg. Credentials are optional — read-only queries work unauthenticated.
        Pass credentials to enable write operations.
        """
        creds = None
        if email and password:
            creds = (email, password)

        orkg = ORKG(host=host, creds=creds)

        if not orkg.ping():
            print("Warning: ORKG host did not respond to ping.", file=sys.stderr)

        if orkg.session:
            print(f"Authenticated as: {email}")
        else:
            print("Connected anonymously (read-only).")

        return orkg


    def get_papers(self, title: str = None, size: int = 5) -> list:
        """
        Retrieve a page of papers, optionally filtered by title keyword.
        Returns the list of paper dicts.
        """
        if title:
            response = self.orkg.papers.get(title=title, size=size)
        else:
            response = self.orkg.papers.get(size=size)

        if not response.succeeded:
            print(f"Failed to retrieve papers: {response.content}", file=sys.stderr)
            return []

        content = response.content
        # The API returns a paginated envelope: {"content": [...], "page": {...}}
        if isinstance(content, dict) and "content" in content:
            return content["content"]
        if isinstance(content, list):
            return content
        return []


    def get_paper_by_id(self, paper_id: str) -> dict | None:
        """Retrieve a single paper by its ORKG resource ID (e.g. 'R123456')."""
        response = self.orkg.papers.by_id(paper_id)
        if not response.succeeded:
            print(f"Paper '{paper_id}' not found: {response.content}", file=sys.stderr)
            return None
        return response.content


    def get_resources(self, query: str = None, size: int = 5) -> list:
        """
        Retrieve generic resources, optionally filtered by label keyword.
        Returns the list of resource dicts.
        """
        if query:
            response = self.orkg.resources.get(q=query, size=size)
        else:
            response = self.orkg.resources.get(size=size)

        if not response.succeeded:
            print(f"Failed to retrieve resources: {response.content}", file=sys.stderr)
            return []

        content = response.content
        if isinstance(content, dict) and "content" in content:
            return content["content"]
        if isinstance(content, list):
            return content
        return []

    def get_resource(self, id: str) -> dict | None:
        """
        Fetch a resource by ID and print all its metadata, including every statement
        where the resource is the subject.  Returns the resource dict, or None on failure.
        """
        resource_resp = self.orkg.resources.by_id(id)
        if not resource_resp.succeeded:
            print(f"Resource '{id}' not found: {resource_resp.content}", file=sys.stderr)
            return None

        resource = resource_resp.content
        label = resource.get("label", "(no label)")
        classes = ", ".join(resource.get("classes") or []) or "(none)"
        print(f"Resource: {id}")
        print(f"  Label  : {label}")
        print(f"  Classes: {classes}")

        stmts_resp = self.orkg.statements.get_by_subject_unpaginated(subject_id=id)
        statements = stmts_resp.content if stmts_resp.all_succeeded else []

        if not statements:
            print("  Statements: (none)")
        else:
            print(f"  Statements ({len(statements)}):")
            for stmt in statements:
                predicate = stmt.get("predicate", {})
                obj = stmt.get("object", {})
                pred_label = predicate.get("label") or predicate.get("id", "?")
                obj_label = obj.get("label", "?")
                obj_id = obj.get("id", "")
                obj_class = obj.get("_class", "")
                suffix = f" [{obj_id}]" if obj_id and obj_class != "literal" else ""
                print(f"    {pred_label}: {obj_label}{suffix}")

        return resource


    def get_resource_as_jsonld(self, id: str) -> dict | None:
        """Fetch a resource by ID and print it as a JSON-LD document."""
        resource_resp = self.orkg.resources.by_id(id)
        if not resource_resp.succeeded:
            print(f"Resource '{id}' not found: {resource_resp.content}", file=sys.stderr)
            return None

        resource = resource_resp.content
        host = self.orkg.host.rstrip("/")

        context = {
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "label": "rdfs:label",
        }

        doc = {
            "@context": context,
            "@id": f"{host}/resource/{id}",
            "@type": resource.get("classes") or [],
            "label": resource.get("label", ""),
        }

        stmts_resp = self.orkg.statements.get_by_subject_unpaginated(subject_id=id)
        statements = stmts_resp.content if stmts_resp.all_succeeded else []

        for stmt in statements:
            predicate = stmt.get("predicate", {})
            obj = stmt.get("object", {})
            pred_id = predicate.get("id", "?")
            pred_label = predicate.get("label") or pred_id
            obj_class = obj.get("_class", "")
            obj_id = obj.get("id", "")
            obj_label = obj.get("label", "")

            context.setdefault(pred_label, f"{host}/predicate/{pred_id}")

            if obj_class == "literal":
                value = {"@value": obj_label}
            else:
                value = {"@id": f"{host}/resource/{obj_id}", "label": obj_label}

            if pred_label in doc:
                existing = doc[pred_label]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    doc[pred_label] = [existing, value]
            else:
                doc[pred_label] = value

        print(json.dumps(doc, indent=2, ensure_ascii=False))
        return doc


    def print_papers(self, papers: list) -> None:
        if not papers:
            print("  (no results)")
            return
        for i, paper in enumerate(papers, 1):
            title = paper.get("title") or paper.get("label") or "(no title)"
            pid = paper.get("id", "?")
            doi = ""
            identifiers = paper.get("identifiers") or {}
            if "doi" in identifiers:
                doi_list = identifiers["doi"]
                doi = f"  DOI: {doi_list[0]}" if doi_list else ""
            year = ""
            pub_info = paper.get("publication_info") or {}
            if pub_info.get("published_year"):
                year = f"  Year: {pub_info['published_year']}"
            print(f"  {i}. [{pid}] {title}{doi}{year}")


    def add_paper_from_doi(self, doi: str, research_field: str = "R11") -> str | None:
        """
        Fetch paper metadata from Crossref and create a proper ORKG paper resource.
        Returns the new ORKG resource ID, or None on failure.
        """
        doi_bare = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")

        try:
            resp = requests.get(
                f"https://doi.org/{doi_bare}",
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except Exception as e:
            print(f"Network error fetching DOI {doi_bare}: {e}", file=sys.stderr)
            return None

        if resp.status_code != 200:
            print(f"Crossref returned HTTP {resp.status_code} for DOI {doi_bare}", file=sys.stderr)
            return None

        try:
            meta = resp.json()
        except Exception as e:
            print(f"Failed to parse Crossref response for DOI {doi_bare}: {e}", file=sys.stderr)
            return None

        title_raw = meta.get("title", "")
        title = (title_raw[0] if isinstance(title_raw, list) else title_raw) or "Untitled"

        authors = []
        for a in meta.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip() or a.get("name", "").strip()
            if name:
                authors.append({"label": name})

        date_parts = meta.get("published", {}).get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        month = date_parts[0][1] if date_parts and len(date_parts[0]) > 1 else None

        publisher = meta.get("publisher")
        publication_info: dict = {
            "published_year": year,
            "published_month": month,
            "published_in": publisher,
            "url": None,
        }

        v2_authors = [{"name": a["label"]} for a in authors]

        response = self.orkg.papers.add_v2(
            title=title,
            research_fields=[research_field],
            identifiers={"doi": [doi_bare]},
            publication_info=publication_info,
            authors=v2_authors,
            contents={"contributions": [], "resources": {}, "literals": {}, "predicates": {}, "lists": {}},
            organizations=[],
            observatories=[],
            extraction_method="AUTOMATIC",
        )
        if not response.succeeded:
            raw = response.content or {}
            if isinstance(raw, (bytes, bytearray)):
                try:
                    import json
                    raw = json.loads(raw.decode("utf-8"))
                except Exception:
                    raw = {}
            content = raw if isinstance(raw, dict) else {}
            if content.get("type") == "orkg:problem:paper_already_exists":
                lookup = self.orkg.papers.by_doi(doi_bare)
                if lookup.succeeded:
                    papers = lookup.content
                    if isinstance(papers, dict) and "content" in papers:
                        papers = papers["content"]
                    if papers:
                        paper_id = papers[0].get("id")
                        print(f"Paper already exists: {paper_id}  (DOI: {doi_bare})")
                        return paper_id
            print(f"Failed to create ORKG paper for DOI {doi_bare}: {response.content}", file=sys.stderr)
            return None

        paper_id = response.content.get("id")
        print(f"Created paper resource: {paper_id}  (DOI: {doi_bare})")
        return paper_id


    def _add_literal(self, value: str) -> str | None:
        resp = self.orkg.literals.add(label=value)
        if not resp.succeeded:
            print(f"Failed to create literal '{value}': {resp.content}", file=sys.stderr)
            return None
        return resp.content["id"]


    def _add_statement(self, subject_id: str, predicate_id: str, object_id: str) -> bool:
        resp = self.orkg.statements.add(
            subject_id=subject_id,
            predicate_id=predicate_id,
            object_id=object_id,
        )
        if not resp.succeeded:
            print(f"Failed to add statement ({subject_id} -{predicate_id}-> {object_id}): {resp.content}", file=sys.stderr)
        return resp.succeeded


    def add_dataset(self, dataset: dict) -> dict | None:
        """
        Create a dataset resource in ORKG from a JSON object and attach metadata statements.

        Expected keys:
          title                (required) human-readable dataset name
          description          (optional) free-text description
          identifier           (optional) persistent identifier / DOI
          datePublished        (optional) date the dataset was published (YYYY-MM-DD)
          dateCreated          (optional) date the dataset was deposited
          keywords             (optional) list of keyword strings
          author               (optional) list of {"name": str} dicts
          funding              (optional) list of {"agency": str} dicts
          Producer             (optional) list of producer name strings
          measurementMethod    (optional) list of method/process description strings
          contributor          (optional) list of {"name": str} dicts
          citation             (optional) list of {"citation": str, "url": str, "id_type": str, "id_number": str}
          related_publication  (optional) ORKG resource ID of a single linked paper (e.g. "R123456")
          related_publications (optional) list of ORKG resource IDs of linked papers

        Returns the created resource dict on success, None on failure.
        """
        title = dataset.get("title")
        if not title:
            print("Dataset must contain a 'title' field.", file=sys.stderr)
            return None

        response = self.orkg.resources.add(label=title, classes=["Dataset"])
        if not response.succeeded:
            print(f"Failed to create dataset resource: {response.content}", file=sys.stderr)
            return None

        dataset_id = response.content["id"]
        print(f"Created dataset resource: {dataset_id}")

        for field in dataset.keys():
            if DATASET_TYPE_PREDICATES.get(field) == "literal":
                if DATASET_PREDICATES[field] == "SAME_AS":
                    continue
                value = dataset.get(field)
                if isinstance(value, list):
                    for item in value:
                        if item:
                            if len(str(item)) > 8164:
                                item = str(item)[:8160] + "..."
                                lit_id = self._add_literal(str(item))
                                if lit_id:
                                    self._add_statement(dataset_id, DATASET_PREDICATES[field], lit_id)
                            else:
                                lit_id = self._add_literal(str(item))
                                if lit_id:
                                    self._add_statement(dataset_id, DATASET_PREDICATES[field], lit_id)
                elif isinstance(value, str):
                    if value:
                        if len(str(value)) > 8164:
                            value = str(value)[:8160] + "..."
                            lit_id = self._add_literal(str(value))
                            if lit_id:
                                self._add_statement(dataset_id, DATASET_PREDICATES[field], lit_id)
                        else:
                            lit_id = self._add_literal(str(value))
                            if lit_id:
                                self._add_statement(dataset_id, DATASET_PREDICATES[field], lit_id)
            elif DATASET_TYPE_PREDICATES.get(field) == "resource":
                for value in dataset.get(field, []):
                    if isinstance(value, list):
                        for item in value:
                            if not item:
                                continue
                            value_resp = self.orkg.resources.add(label=item)
                            if value_resp.succeeded:
                                self._add_statement(dataset_id, DATASET_PREDICATES[field], value_resp.content["id"])
                                subfields = [
                                    subfield
                                    for subfield in DATASET_PREDICATES_SUBFIELDS.get(field).split(",")
                                    if DATASET_PREDICATES_SUBFIELDS.get(field, "") is not None
                                ]
                                if "SAME_AS" in subfields:
                                    same_as = dataset.get(field+".SAME_AS", [])
                                    for subitem in same_as:
                                        subvalue = subitem.get(item)
                                        if not subvalue:
                                            continue
                                        lit_id_subvalue = self._add_literal(str(subvalue))
                                        if lit_id_subvalue:
                                            self._add_statement(value_resp.content["id"], "SAME_AS", lit_id_subvalue)
                    elif isinstance(value, str):
                        if not value:
                            continue
                        value_resp = self.orkg.resources.add(label=value)
                        if value_resp.succeeded:
                            self._add_statement(dataset_id, DATASET_PREDICATES[field], value_resp.content["id"])
                            subfields = [subfield
                                         for subfield in DATASET_PREDICATES_SUBFIELDS.get(field).split(",")
                                         if DATASET_PREDICATES_SUBFIELDS.get(field, "") is not None
                            ]
                            if "SAME_AS" in subfields:
                                same_as = dataset.get(field + ".SAME_AS", [])
                                for subitem in same_as:
                                    subvalue = subitem.get(value)
                                    if not subvalue:
                                        continue
                                    lit_id_subvalue = self._add_literal(str(subvalue))
                                    if lit_id_subvalue:
                                        self._add_statement(value_resp.content["id"], "SAME_AS", lit_id_subvalue)


        # Citations → one Paper resource per entry
        for cite in dataset.get("citation", []):
            citation_text = cite.get("citation", "").strip()
            if not citation_text:
                continue
            paper_resp = self.orkg.resources.add(label=citation_text, classes=["Paper"])
            if not paper_resp.succeeded:
                print(f"Failed to create citation resource: {paper_resp.content}", file=sys.stderr)
                continue
            paper_id = paper_resp.content["id"]
            url = cite.get("url", "").strip()
            if url:
                url_lit = self._add_literal(url)
                if url_lit:
                    self._add_statement(paper_id, DATASET_PREDICATES["identifier"], url_lit)
            id_number = cite.get("id_number", "").strip()
            id_type = cite.get("id_type", "").strip()
            if id_number:
                label = f"{id_type}:{id_number}" if id_type else id_number
                id_lit = self._add_literal(label)
                if id_lit:
                    self._add_statement(paper_id, DATASET_PREDICATES["identifier"], id_lit)
            self._add_statement(dataset_id, DATASET_PREDICATES["citation"], paper_id)

        # Link to related paper resource(s)
        related_pub = dataset.get("related_publication")
        if related_pub:
            self._add_statement(dataset_id, DATASET_PREDICATES["citation"], related_pub)

        for pub_id in dataset.get("related_publications", []):
            self._add_statement(dataset_id, DATASET_PREDICATES["citation"], pub_id)

        return response.content