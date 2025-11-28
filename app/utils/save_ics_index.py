from pathlib import Path

def append_ics_index(company: str, property_name: str, public_url: str, output_path="ics_index.txt"):
    line = f"{company} | {property_name} | {public_url}\n"
    with open(output_path, "a") as f:
        f.write(line)
