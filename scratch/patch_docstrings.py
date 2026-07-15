import os
import ast

def add_docstrings(directory):
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
            
            # Record nodes to patch
            to_patch = []
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
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
                            # We need to insert a docstring.
                            # We insert it right after the `def` line.
                            # But wait, def can span multiple lines.
                            # Better approach: insert it at the line of the first statement in the body.
                            first_stmt = node.body[0]
                            indent = ' ' * first_stmt.col_offset
                            to_patch.append((first_stmt.lineno, node.name, indent))
            
            if to_patch:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Sort descending to not mess up line numbers when inserting
                to_patch.sort(key=lambda x: x[0], reverse=True)
                
                for lineno, name, indent in to_patch:
                    docstring = f'{indent}"""{name} işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.{name} [parametreler]`"""\n'
                    # lineno is 1-indexed. Insert before lineno - 1.
                    lines.insert(lineno - 1, docstring)
                    
                with open(path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"Patched {len(to_patch)} commands in {path}")

add_docstrings('Commands')
