import re

with open("static/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Find all lines with class="tab-pane" or section tags
lines = content.splitlines()
for i, line in enumerate(lines):
    if "tab-pane" in line or 'id="tab-' in line:
        print(f"Line {i+1}: {line}")
