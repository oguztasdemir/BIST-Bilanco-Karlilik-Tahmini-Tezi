with open("static/script.js", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

for i, line in enumerate(lines):
    if "addEventListener" in line:
        # Check context
        print(f"Line {i+1}: {line.strip()}")
