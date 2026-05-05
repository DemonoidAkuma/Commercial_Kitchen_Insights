import re
from pdfminer.high_level import extract_text


# -----------------------------
# Revenue
# -----------------------------
def extract_revenue(pdf_path):

    from pdfminer.high_level import extract_text
    import re

    text = extract_text(pdf_path)
    clean_text = text.replace(",", "")

    # Look for line:
    # Total : $233723.62   $68361.38
    match = re.search(
        r"Total\s*:?\s*\$?\s*([0-9]+\.[0-9]{2})\s+\$?\s*([0-9]+\.[0-9]{2})",
        clean_text,
        re.IGNORECASE,
    )

    if match:
        # FIRST number is Revenue (ex GST)
        return float(match.group(1))

    # Fallback → take first currency value in document
    amounts = re.findall(r"\$?\s?([0-9]+\.[0-9]{2})", clean_text)

    if amounts:
        return float(amounts[0])

    return 0.0


def extract_cogs(pdf_path):

    from pdfminer.high_level import extract_text
    import re

    text = extract_text(pdf_path)
    clean_text = text.replace(",", "")

    # Look for line like:
    # Total : $233723.62   $68361.38
    match = re.search(
        r"Total\s*:?\s*\$?\s*([0-9]+\.[0-9]{2})\s+\$?\s*([0-9]+\.[0-9]{2})",
        clean_text,
        re.IGNORECASE,
    )

    if match:
        # SECOND number is Purchases
        return float(match.group(2))

    # Fallback: take last currency value
    amounts = re.findall(r"\$?\s?([0-9]+\.[0-9]{2})", clean_text)

    if amounts:
        return float(amounts[-1])

    return 0.0

# -----------------------------
# Stock Value
# -----------------------------
def extract_stock_value(pdf_path):

    text = extract_text(pdf_path)
    clean_text = text.replace(",", "")

    # Try to find "Total Stock Value"
    match = re.search(
        r"(Total.*?Stock.*?\$?\s?([0-9]+\.[0-9]{2}))",
        clean_text,
        re.IGNORECASE,
    )

    if match:
        return float(match.group(2))

    # Fallback to last currency value
    amounts = re.findall(r"\$?\s?([0-9]+\.[0-9]{2})", clean_text)

    return float(amounts[-1]) if amounts else 0.0


# -----------------------------
# Food Cost % (14 Day Reports)
# -----------------------------
def extract_food_cost_percent(pdf_path):

    text = extract_text(pdf_path)

    match = re.search(r"Food Cost.*?([0-9]+\.[0-9]+)%", text, re.IGNORECASE)

    if match:
        return float(match.group(1))

    return 0.0

# -----------------------------
# Waste Line Extraction
# -----------------------------

def clean_reason(reason):
    if not reason:
        return "Unknown"

    reason = reason.strip().lower()

    replacements = {
        "freezer broken": "Equipment Failure",
        "freezer brokem": "Equipment Failure",
        "brokem": "Equipment Failure",
        "broken": "Equipment Failure",
        "over cock": "Overcooked",
        "over cooked": "Overcooked",
        "overcooked": "Overcooked",
        "drp": "Dropped",
        "drop": "Dropped",
        "dropped/off": "Dropped",
        "o.o.d": "Out of Date",
        "ood": "Out of Date",
        "off": "Out of Date",
    }

    for key, value in replacements.items():
        if key in reason:
            return value

    return reason.title()


import pdfplumber
import re


def extract_waste_lines(file_path):

    waste_lines = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:

            tables = page.extract_tables()

            for table in tables:
                for row in table:

                    if not row:
                        continue

                    row = [cell.strip() if cell else "" for cell in row]

                    # Skip header row
                    if len(row) > 1 and "Item" in row[1]:
                        continue

                    if len(row) >= 5:

                        item = row[1]
                        qty = row[2]
                        value_raw = row[3]
                        reason = row[4]

                        if not value_raw:
                            continue

                        value_clean = re.sub(r"[^\d.]", "", value_raw)

                        try:
                            total = float(value_clean)
                        except:
                            continue

                        cleaned_reason = clean_reason(
                            reason.replace("\n", " ")
                        )

                        waste_lines.append({
                            "item": item.replace("\n", " "),
                            "qty": qty,
                            "total": total,
                            "reason": cleaned_reason
                        })

    return waste_lines