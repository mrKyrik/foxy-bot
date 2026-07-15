import os
import ast

def find_undocumented_commands(directory):
    for root, dirs, files in os.walk(directory):
        if '__pycache__' in root:
            continue
        for file in files:
            if not file.endswith('.py'):
                continue
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
                    is_command = False
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Call):
                            if isinstance(dec.func, ast.Attribute) and dec.func.attr in ('command', 'group'):
                                is_command = True
                        elif isinstance(dec, ast.Attribute) and dec.attr in ('command', 'group'):
                            is_command = True
                            
                    if is_command:
                        docstring = ast.get_docstring(node)
                        if not docstring:
                            print(f"{path}: Command '{node.name}' has no docstring.")

find_undocumented_commands('Commands')
