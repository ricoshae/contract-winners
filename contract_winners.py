import requests
import csv
import re
from datetime import datetime, timedelta

# Same e-learning/LMS keyword list as rfqsearch
KEYWORDS = [
    # Core LMS platforms
    "moodle", "canvas lms", "blackboard lms", "learning management system",
    "lms", "totara", "brightspace", "d2l",
    # Broader e-learning terms
    "e-learning", "elearning", "online learning", "digital learning",
    "online course", "online training", "blended learning",
    # Development & Tech
    "h5p", "scorm", "xapi", "tin can", "articulate rise", "articulate storyline",
    "learning design", "instructional design", "course development",
    # Training & education services
    "training platform", "training system", "training portal",
    "education platform", "education technology", "edtech",
    "student management", "learning platform", "learning portal",
    # Broad terms (higher volume, lower precision)
    "training delivery", "training program", "training solution",
    "education resource", "education delivery",
    "curriculum", "professional development",
    "online module", "digital content", "interactive learning",
    # Specific problem states you solve
    "course migration", "lms migration", "course transformation",
    "learning resources", "content migration", "digital transformation learning",
    # Specific tech & compliance
    "accessibility compliance", "wcag", "section 508",
    "virtual classroom", "virtual learning environment",
    "learning analytics", "learner engagement",
    "competency framework", "micro-credential", "digital badge",
    "assessment platform", "online assessment", "e-assessment",
    # Code-adjacent opportunities
    "moodle plugin", "custom h5p", "html css development",
    "web development training", "interactive content",
    "web application", "web portal development",
    "content management system", "cms development",
]

API_BASE = "https://api.tenders.gov.au/ocds/findByDates/contractPublished"
CSV_FILE = "results.csv"

CSV_COLUMNS = [
    "Contract Title",
    "CN ID",
    "Value",
    "Currency",
    "Start Date",
    "End Date",
    "Supplier Name",
    "Supplier ABN",
    "Supplier Locality",
    "Supplier Region",
    "Supplier Postcode",
    "Supplier Email",
    "Buyer/Agency",
    "Matched Keyword",
    "AusTender Link",
]


def keyword_match(text):
    """Return the first matching keyword found in text, or None."""
    text = re.sub(r"\s+", " ", text).strip().lower()
    for kw in KEYWORDS:
        if kw in text:
            return kw
    return None


def find_party(parties, role):
    """Find the first party with the given role."""
    for party in parties:
        if role in party.get("roles", []):
            return party
    return None


def get_abn(party):
    """Extract ABN from a party's additionalIdentifiers."""
    for ident in party.get("additionalIdentifiers", []):
        if ident.get("scheme") == "AU-ABN":
            return ident.get("id", "")
    return ""


def extract_match(release, matched_keyword):
    """Extract contract details from an OCDS release."""
    contract = release.get("contracts", [{}])[0]
    parties = release.get("parties", [])

    supplier = find_party(parties, "supplier") or {}
    buyer = find_party(parties, "procuringEntity") or {}

    address = supplier.get("address", {})
    contact = supplier.get("contactPoint", {})
    value = contract.get("value", {})
    period = contract.get("period", {})

    cn_id = contract.get("id", "")

    return {
        "Contract Title": contract.get("description", contract.get("title", "")),
        "CN ID": cn_id,
        "Value": value.get("amount", ""),
        "Currency": value.get("currency", "AUD"),
        "Start Date": period.get("startDate", ""),
        "End Date": period.get("endDate", ""),
        "Supplier Name": supplier.get("name", ""),
        "Supplier ABN": get_abn(supplier),
        "Supplier Locality": address.get("locality", ""),
        "Supplier Region": address.get("region", ""),
        "Supplier Postcode": address.get("postalCode", ""),
        "Supplier Email": contact.get("email", ""),
        "Buyer/Agency": buyer.get("name", ""),
        "Matched Keyword": matched_keyword,
        "AusTender Link": f"https://www.tenders.gov.au/Cn/Show/{cn_id}" if cn_id else "",
    }


def scan_contracts():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    date_fmt = "%Y-%m-%dT%H:%M:%SZ"
    url = f"{API_BASE}/{start_date.strftime(date_fmt)}/{end_date.strftime(date_fmt)}"

    print(f"=== AusTender Contract Winners Scan ===")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Keywords: {len(KEYWORDS)} terms")
    print()

    matches = []
    page = 0
    total_checked = 0

    while url:
        page += 1
        print(f"Fetching page {page}...", end=" ", flush=True)

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"API error: {e}")
            break

        data = resp.json()
        releases = data.get("releases", [])
        print(f"{len(releases)} releases")

        if not releases:
            break

        for release in releases:
            total_checked += 1
            # Build searchable text from contract descriptions and titles
            contract = release.get("contracts", [{}])[0]
            searchable = " ".join(filter(None, [
                contract.get("title", ""),
                contract.get("description", ""),
                release.get("tender", {}).get("title", ""),
                release.get("tender", {}).get("description", ""),
            ]))

            matched_kw = keyword_match(searchable)
            if matched_kw:
                row = extract_match(release, matched_kw)
                matches.append(row)

        # Follow pagination
        url = data.get("links", {}).get("next")

    # Write CSV
    if matches:
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(matches)

    # Summary
    print()
    print(f"=== Results ===")
    print(f"Total contracts checked: {total_checked}")
    print(f"Matches found: {len(matches)}")
    if matches:
        print(f"Output written to: {CSV_FILE}")
        print()
        for i, m in enumerate(matches, 1):
            try:
                value_str = f"${float(m['Value']):,.2f} {m['Currency']}"
            except (ValueError, TypeError):
                value_str = "N/A"
            print(f"{i}. {m['Contract Title'][:80]}")
            print(f"   Supplier: {m['Supplier Name']} | Value: {value_str}")
            print(f"   Keyword: '{m['Matched Keyword']}' | {m['AusTender Link']}")
            print()
    else:
        print("No matching contracts found.")

    return matches


if __name__ == "__main__":
    scan_contracts()
