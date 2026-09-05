# -*- coding: utf-8 -*-
"""Fix data quality issues: placeholder answers and double-encoded options."""
import json
import sqlite3

c = sqlite3.connect("exam_hub.db")
cur = c.cursor()

# 1. Fix questions with placeholder answer 'B' from crawler
cur.execute(
    "UPDATE questions SET answer='待核实', explanation='真实自考真题，答案待核实' "
    "WHERE source LIKE '%真实真题%' AND answer='B' AND explanation LIKE '%答案待补充%'"
)
print(f"Fixed placeholder answers: {cur.rowcount} questions")
c.commit()

# 2. Check and fix double-encoded options
# SQLite JSON column stores as text; check if value is a JSON string containing another JSON string
cur.execute("SELECT id, options FROM questions")
all_rows = cur.fetchall()
double_encoded = 0
for row_id, opts in all_rows:
    if opts is None:
        continue
    # If opts is already a Python string (from sqlite3)
    if isinstance(opts, str):
        stripped = opts.strip()
        # Double-encoded: the string starts with '"[' (a JSON-encoded JSON array)
        if stripped.startswith('"[') or stripped.startswith("'["):
            try:
                decoded = json.loads(stripped)
                if isinstance(decoded, str) and decoded.startswith("["):
                    # It was double-encoded, save the inner value
                    cur.execute("UPDATE questions SET options=? WHERE id=?", (decoded, row_id))
                    double_encoded += 1
            except (json.JSONDecodeError, ValueError):
                pass

c.commit()
print(f"Fixed double-encoded options: {double_encoded} questions")

# 3. Summary
cur.execute("SELECT count(*) FROM questions WHERE answer='待核实'")
print(f"Questions with '待核实' answer: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM questions WHERE answer != '待核实' AND source LIKE '%真实真题%'")
print(f"Real questions with actual answers: {cur.fetchone()[0]}")

c.close()
print("\n[OK] Data quality fixes complete.")
