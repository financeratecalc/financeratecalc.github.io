"""schema.org Dataset markup for the generated data pages, in the shape Google Dataset Search reads
(name, description 50-5000 characters, creator, license, distribution as DataDownload, temporalCoverage, isBasedOn).
One function; every value is passed in by the page builder from the data it already holds."""
import json

ORG = {"@type": "Organization", "name": "FinanceRateCalc", "url": "https://financeratecalc.com"}
CATALOG = {"@type": "DataCatalog", "name": "FinanceRateCalc data catalog", "url": "https://financeratecalc.com/data-catalog.html"}
FMT = {"json": "application/json", "csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def dataset_script(name, description, url, downloads, temporal, based_on=(), variables=(), keywords=(), modified=None, license_url="https://creativecommons.org/licenses/by/4.0/"):
    description = " ".join(description.split())
    assert 50 <= len(description) <= 5000, f"description length {len(description)}"
    d = {"@context": "https://schema.org", "@type": "Dataset", "name": name, "description": description, "url": url, "creator": ORG, "publisher": ORG,
         "license": license_url, "isAccessibleForFree": True, "includedInDataCatalog": CATALOG, "temporalCoverage": temporal,
         "spatialCoverage": {"@type": "Place", "name": "United States"},
         "distribution": [{"@type": "DataDownload", "contentUrl": u, "encodingFormat": FMT[u.rsplit(".", 1)[-1]]} for u in downloads]}
    if based_on:
        d["isBasedOn"] = list(based_on)
    if variables:
        d["variableMeasured"] = list(variables)
    if keywords:
        d["keywords"] = list(keywords)
    if modified:
        d["dateModified"] = modified
    return '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "</script>"
