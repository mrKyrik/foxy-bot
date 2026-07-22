import re
import json

def extract_strings(db_path, out_path):
    with open(db_path, "rb") as f:
        data = f.read()

    # Find printable ASCII strings of length >= 8
    # This might match JSON data, IDs, etc.
    strings = re.findall(b"[ -~]{8,}", data)
    
    with open(out_path, "w", encoding="utf-8") as f:
        for s in set(strings):
            try:
                f.write(s.decode("ascii") + "\n")
            except:
                pass

if __name__ == "__main__":
    extract_strings("kumiho_corrupt.db", "recovered_strings.txt")
    print("Strings extracted to recovered_strings.txt")
