import re
import os

API_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "api", "main.py"))

def refactor():
    with open(API_FILE, 'r', encoding='utf-8') as f:
        code = f.read()

    # Change to async def
    code = re.sub(r'(@app\.(?:get|post|put|delete|patch).*?\n)(def\s+\w+\()', r'\1async \2', code)
    
    code = code.replace("def verify_guild_access", "async def verify_guild_access")
    code = code.replace("def verify_write_access", "async def verify_write_access")
    code = code.replace("def verify_owner_access", "async def verify_owner_access")

    with open(API_FILE, 'w', encoding='utf-8') as f:
        f.write(code)

if __name__ == "__main__":
    refactor()
