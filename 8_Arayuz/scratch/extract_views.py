import os

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

with open("static/index.html", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

# Tab definitions: (filename, start_line_1_indexed, end_line_1_indexed)
tabs = [
    ("templates/analiz_paneli.html", 101, 483),
    ("templates/trend_analizi.html", 484, 556),
    ("templates/kar_tahmini.html", 557, 629),
    ("templates/kar_zarar_siniflandirma.html", 630, 721),
    ("templates/yon_siniflandirma.html", 722, 813),
    ("templates/rakip_analizi.html", 814, 905),
    ("templates/yonetici_paneli.html", 906, 1192),
]

for filename, start, end in tabs:
    # Extract lines (0-indexed)
    block_lines = lines[start - 1 : end]
    
    # Make sure the section has 'active' class so it is visible
    first_line = block_lines[0]
    if 'class="tab-pane"' in first_line:
        first_line = first_line.replace('class="tab-pane"', 'class="tab-pane active"')
        block_lines[0] = first_line
    elif 'class="tab-pane active"' not in first_line:
        # Just in case, force inject active class
        first_line = first_line.replace('class="tab-pane', 'class="tab-pane active')
        block_lines[0] = first_line
        
    block_content = "\n".join(block_lines)
    
    template_content = f"""{{% extends "base.html" %}}
{{% block content %}}
{block_content}
{{% endblock %}}
"""
    with open(filename, "w", encoding="utf-8") as out:
        out.write(template_content)
    print(f"Extracted {filename} successfully!")
