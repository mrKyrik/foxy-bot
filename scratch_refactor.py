import os
import re
import json

category_map = {
    'Db_settings': 'Yönetim ve Ayarlar',
    'Settings': 'Yönetim ve Ayarlar',
    'Permissions': 'Yönetim ve Ayarlar',
    'Role_sync': 'Yönetim ve Ayarlar',
    'Owner': 'Yönetim ve Ayarlar',
    'Forms': 'Topluluk ve Etkileşim',
    'Tickets': 'Topluluk ve Etkileşim',
    'Suggestions': 'Topluluk ve Etkileşim',
    'Giveaways': 'Topluluk ve Etkileşim',
    'Economy': 'Gelişim ve Ekonomi',
    'Leveling': 'Gelişim ve Ekonomi',
    'Automod': 'Moderasyon',
    'Moderation': 'Moderasyon',
    'Fun': 'Eğlence ve Araçlar',
    'Utils': 'Eğlence ve Araçlar',
    'Nsfw': 'Eğlence ve Araçlar',
    'Private_voice': 'Eğlence ve Araçlar'
}

def improve_desc(cmd_name, old_desc, new_cat):
    usage = ''
    if 'Usage:' in old_desc:
        usage = old_desc.split('Usage:')[1].strip().replace('`', '')
    
    if 'set' in cmd_name or 'ayarla' in cmd_name:
         base = f'Sistemdeki {cmd_name} ayarını yapılandırır.'
         if not usage: usage = f'f.{cmd_name} <parametre>'
    elif 'add' in cmd_name or 'ekle' in cmd_name:
         base = f'Sisteme yeni bir {cmd_name} verisi ekler.'
         if not usage: usage = f'f.{cmd_name} <değer>'
    elif 'remove' in cmd_name or 'delete' in cmd_name:
         base = f'Sistemden belirtilen {cmd_name} verisini siler.'
         if not usage: usage = f'f.{cmd_name} <hedef>'
    elif 'toggle' in cmd_name or 'anti' in cmd_name:
         base = f'{cmd_name} korumasını/özelliğini açıp kapatır.'
         if not usage: usage = f'f.{cmd_name} <aç|kapat>'
    elif 'clear' in cmd_name:
         base = f'Sistemdeki {cmd_name} kayıtlarını tamamen temizler.'
         if not usage: usage = f'f.{cmd_name}'
    elif 'info' in cmd_name or 'show' in cmd_name or 'list' in cmd_name:
         base = f'{cmd_name} hakkında detaylı bilgi gösterir.'
         if not usage: usage = f'f.{cmd_name}'
    else:
         base = f'{cmd_name} işlemini güvenli bir şekilde gerçekleştirir.'
         if not usage: usage = f'f.{cmd_name} [parametreler]'
         
    return f'{base} Kullanım: `{usage}`'

with open('web/api/commands_list.json', encoding='utf-8') as f:
    commands_data = json.load(f)

# Flatten command data to a fast lookup dictionary
cmd_lookup = {}
for old_cat, cmds in commands_data.items():
    new_cat = category_map.get(old_cat, 'Diğer')
    for c in cmds:
        cmd_lookup[c['name']] = improve_desc(c['name'], c.get('desc', ''), new_cat)

def process_file(filepath, cog_name, category_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Add self.category to __init__
    if 'def __init__(self' in content and 'self.category =' not in content:
        content = re.sub(
            r'(def __init__\(self.*?:\s+)',
            fr'\1self.category = "{category_name}"\n        ',
            content,
            count=1
        )
    
    # 2. Replace docstrings for commands
    lines = content.split('\n')
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out_lines.append(line)
        
        # Check if line is async def
        match = re.match(r'(\s+)async def (\w+)\(self,\s*ctx', line)
        if match:
            indent = match.group(1)
            func_name = match.group(2)
            
            # Check if this function is a command
            is_cmd = False
            for back_i in range(i-1, max(-1, i-5), -1):
                if '@' in lines[back_i] and 'command' in lines[back_i]:
                    is_cmd = True
                    break
            
            if is_cmd and i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if next_line.startswith('"""') or next_line.startswith("'''"):
                    end_idx = i + 1
                    if not (next_line.endswith('"""') and len(next_line) > 3) and not (next_line.endswith("'''") and len(next_line) > 3):
                        for j in range(i+2, len(lines)):
                            if '"""' in lines[j] or "'''" in lines[j]:
                                end_idx = j
                                break
                    
                    actual_cmd_name = func_name
                    for back_i in range(i-1, max(-1, i-5), -1):
                        name_match = re.search(r'name=["\']([^"\']+)["\']', lines[back_i])
                        if name_match:
                            actual_cmd_name = name_match.group(1)
                            break
                            
                    new_desc = cmd_lookup.get(actual_cmd_name)
                    if new_desc:
                        out_lines.append(f'{indent}"""{new_desc}"""')
                        i = end_idx
                        i += 1
                        continue
        i += 1
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))

import glob
for root, _, files in os.walk('Commands'):
    for file in files:
        if file.endswith('.py') and file != '__init__.py':
            path = os.path.join(root, file)
            filename = file.replace('.py', '').capitalize()
            if filename.lower() == 'db_settings': cat = 'Db_settings'
            elif filename.lower() == 'role_sync': cat = 'Role_sync'
            elif filename.lower() == 'private_voice': cat = 'Private_voice'
            else: cat = filename
            
            mapped_cat = category_map.get(cat, 'Diğer')
            process_file(path, filename, mapped_cat)

print("Refactoring complete.")
