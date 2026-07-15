with open('web/api/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('MAIN_MAIN_DB_PATH', 'MAIN_DB_PATH')

with open('web/api/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed MAIN_MAIN_DB_PATH')
