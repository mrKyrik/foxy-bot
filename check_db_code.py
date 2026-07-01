with open("core/database.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for i in range(325, 345):
        print(f"{i+1}: {lines[i].rstrip()}")
