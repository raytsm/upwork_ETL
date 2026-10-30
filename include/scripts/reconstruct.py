from pathlib import Path
import csv
import io
import re
import time


# reconstruct.py is in include/scripts/, so parents[1] is the include/ folder.
INCLUDE_DIR = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = INCLUDE_DIR / "data" / "raw_data"
RECONSTRUCTED_DATA_DIR = INCLUDE_DIR / "data" / "reconstructed_data"

csv.field_size_limit(100_000_000)

RECORD_START = re.compile(
    r"^\d+,https?://(?:www\.)?upwork\.com/"
)

TIMESTAMP = (
    r"\d{4}-\d{2}-\d{2}"
    r"[T ]"
    r"\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})?"
)

MIDDLE_BOUNDARY = re.compile(
    rf'\}}",({TIMESTAMP}),({TIMESTAMP}),"\{{'
)

END_BOUNDARY = re.compile(
    rf'\}}",({TIMESTAMP}),({TIMESTAMP})$'
)

HEADERS = [
    "id",
    "url",
    "title",
    "description",
    "budget",
    "budget_type",
    "hourly_rate_min",
    "hourly_rate_max",
    "work_type",
    "experience_level",
    "duration",
    "location",
    "category",
    "skills",
    "proposals",
    "client_info",
    "posted_date",
    "crawled_date",
    "raw_data",
    "created_at",
    "updated_at",
]

def candidate_record(file):
    "One record at a time that begins with line matching RECORD_START"
    parts = []
    start_line = None
    for line_number, line in enumerate(file, start=1):
        if RECORD_START.match(line):
            if parts:
                yield start_line, "".join(parts)

            parts = [line]
            start_line = line_number

        else:
            parts.append(line)

    if parts:
        yield start_line, "".join(parts)

def parse_prefix(prefix):
    "Get all 15 records before the first json obj."
    variants = [
        prefix,
        prefix.replace('\'"', '\'""'),
    ]
    for candidate in variants:
        try:
            rows = list(
                csv.reader(
                    io.StringIO(candidate, newline=""),
                    strict=True
                )
            )
        except csv.Error:
            continue

        if len(rows) == 1 and len(rows[0]) == 15:
            return rows[0]

    return None

def repair_record(raw_record):
    "parse each candidate record into 21 columns"

    # first step: remove the line ending \n and/or \r
    if raw_record.endswith("\r\n"):
        record = raw_record[:-2]
    elif raw_record.endswith("\n") or raw_record.endswith("\r"):
        record = raw_record[:-1]
    else:
        record = raw_record

    # fow rows that is good, convert use normally
    try:
        parsed_records = list(
            csv.reader(
                io.StringIO(record, newline=""),
                strict=True,
            )
        )

        if (len(parsed_records) == 1 and len(parsed_records[0]) == 21):
            return parsed_records[0]

    except csv.Error:
        pass

    # for records with empty json columns fix the quotation mark
    adjusted_record = record.replace('\'"', '\'""')
    try:
        adjusted_rows = list(
            csv.reader(
                io.StringIO(adjusted_record, newline=""),
                strict=True,
            )
        )

        if len(adjusted_rows) == 1:
            adjusted_row = adjusted_rows[0]

            if(
                len(adjusted_row) == 21
                and adjusted_row[0].isdigit()
                and adjusted_row[15] == ""
                and adjusted_row[18] == ""
                and re.fullmatch(TIMESTAMP, adjusted_row[19])
                and re.fullmatch(TIMESTAMP, adjusted_row[20])
            ):
                return adjusted_row
    except csv.Error:
        pass

    # for broken json columns with unescaped quotes
    end_matches = list(END_BOUNDARY.finditer(record))
    end_match = end_matches[0]
    possible_splits = []

    for start_match in re.finditer(r',"\{',record):
        prefix = record[:start_match.start()]
        prefix_columns = parse_prefix(prefix)

        if prefix_columns is None: # calls parse_prefix for everything before "{ characters, if it returns 15 columns & not None then we know it's start of json obj.
            continue

        first_object_start = start_match.start() + 2

        for middle_match in MIDDLE_BOUNDARY.finditer(record, first_object_start): # Now it searches for }", timestamp, timestamp, "{
            if middle_match.start() >= end_match.start():
                continue

            first_object = record[first_object_start:middle_match.start() + 1] # first json obj. including the closing }

            second_object_start = middle_match.end() - 1
            second_object = record[second_object_start:end_match.start() + 1] # second json obj. including the closeing }

            row = (
                prefix_columns + [
                    first_object, # first json
                    middle_match.group(1), # timestamps
                    middle_match.group(2),
                    second_object, # second json
                    end_match.group(1),
                    end_match.group(2),
                ]
            )

            if len(row) == 21:
                possible_splits.append(row)

    return possible_splits[0]

def reconstruct(file_name):
    input_file = RAW_DATA_DIR / file_name
    output_file = RECONSTRUCTED_DATA_DIR / "upwork_reconstructed.csv"
    rejects_file = RECONSTRUCTED_DATA_DIR / "upwork_rejected.txt"

    accepted = rejected = 0

    start_time = time.time()
    with (
        input_file.open("r", encoding="utf-8-sig", newline="") as src,
        output_file.open("w", encoding="utf-8", newline="") as out,
        rejects_file.open("w", encoding="utf-8", newline="") as rej,
    ):
        writer = csv.writer(out)
        writer.writerow(HEADERS)
        for start_line, raw_record in candidate_record(src):
            try:
                row = repair_record(raw_record)
                writer.writerow(row)
                accepted += 1
                print(f"Accepted: {accepted}, Row: {row}")
            except:
                rejected += 1
                rej.write(
                    f"\n--- Rejected record starting at line {start_line} ---\n"
                    f"Record:\n{raw_record.rstrip()}\n"
                )
    end_time = time.time()
    elapsed_seconds = end_time - start_time
    minutes, seconds = divmod(elapsed_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    print(f"Hours: {hours}, Minutes: {minutes}, seconds: {seconds}")
    print(f"\nFinished | Accepted: {accepted:,} | Rejected: {rejected:,}")
    return str(output_file)

reconstruct("upwork_combined_data.csv")