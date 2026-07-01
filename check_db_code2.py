with open("core/database.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for i in range(346, 360):
        print(f"{i+1}: {lines[i].rstrip()}")
