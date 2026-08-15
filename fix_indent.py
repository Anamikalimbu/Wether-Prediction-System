import re

def main():
    with open('app.py', 'r', encoding='utf-8') as f:
        code = f.read()

    def replacer(match):
        s = match.group(0)
        lines = s.split('\n')
        new_lines = []
        for line in lines:
            if 'st.markdown' in line or 'unsafe_allow_html' in line:
                new_lines.append(line)
            else:
                new_lines.append(line.lstrip())
        return '\n'.join(new_lines)

    new_code = re.sub(r'st\.markdown\([f]?(?:\"\"\"|\'\'\')(?:.*?)(?:\"\"\"|\'\'\'),\s*unsafe_allow_html=True\)', replacer, code, flags=re.DOTALL)
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_code)

if __name__ == '__main__':
    main()
