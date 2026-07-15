import os, re

mapping = {
    "Moderasyon": "🛡️",
    "Gelişim ve Ekonomi": "🪙",
    "Topluluk ve Etkileşim": "👥",
    "Eğlence ve Araçlar": "🛠️",
    "Yönetim ve Ayarlar": "⚙️",
    "Yönetim": "⚙️"
}

for root, _, files in os.walk('Commands'):
    if '__pycache__' in root: continue
    for file in files:
        if not file.endswith('.py'): continue
        path = os.path.join(root, file)
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "forums.py" in file:
            content = content.replace('category = "Yönetim"', 'category = "Yönetim ve Ayarlar"')
            
        for cat_name, emoji in mapping.items():
            pattern = re.compile(r'(^[ \t]*category\s*=\s*["\']' + re.escape(cat_name) + r'["\'].*?\n)', re.MULTILINE)
            
            def repl(match):
                cat_line = match.group(1)
                indent = cat_line[:len(cat_line) - len(cat_line.lstrip())]
                emoji_line = f'{indent}category_emoji = "{emoji}"\n'
                return cat_line + emoji_line
            
            if 'category_emoji =' not in content:
                content = pattern.sub(repl, content)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Processed {path}")
