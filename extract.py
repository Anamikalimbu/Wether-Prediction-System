import re

with open('generate_notebook.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all new_code_cell calls
code_blocks = re.findall(r'nbf\.v4\.new_code_cell\(\"\"\"(.*?)\"\"\"\)', content, flags=re.DOTALL)
print(f'Found {len(code_blocks)} code blocks. Executing...')

full_code = '\n'.join(code_blocks)

with open('train_models.py', 'w', encoding='utf-8') as f:
    f.write(full_code)

print('Saved to train_models.py')
