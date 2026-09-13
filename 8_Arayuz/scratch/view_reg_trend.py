with open("static/script.js", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

# Print lines 1120 to 1138 to see the start of the regression trend section
for i in range(1115, 1145):
    if i < len(lines):
        print(f"Line {i+1}: {lines[i]}")
