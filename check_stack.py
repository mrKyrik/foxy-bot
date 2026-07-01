import re

try:
    with open('Data/discord.log', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if "'sqlite3.Row' object has no attribute 'get'" in line:
            start = max(0, i - 15)
            end = min(len(lines), i + 5)
            print("--- STACK TRACE ---")
            for j in range(start, end):
                print(lines[j].strip())
            break
except Exception as e:
    print(e)
