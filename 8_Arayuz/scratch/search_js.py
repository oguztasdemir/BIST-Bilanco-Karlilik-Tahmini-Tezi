with open("static/script.js", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

# Search for function declarations
for i, line in enumerate(lines):
    if "function loadJigsawPerformance" in line or "function setup" in line or "function" in line[:30]:
        print(f"Line {i+1}: {line}")
