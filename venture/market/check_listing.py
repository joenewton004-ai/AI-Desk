"""Check an Etsy title (and optional tags) against LISTING_RULES.md. Usage: check_listing.py "title" [tag ...]"""
import re, sys
title, tags = sys.argv[1], sys.argv[2:]
caps = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9&'-]*", title) if len(re.sub(r"[^A-Za-z]", "", w)) > 1 and w.isupper()]
ok = True
def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg); ok &= cond
check(len(title) <= 140, f"title length {len(title)} <= 140")
check(len(caps) <= 3, f"all-caps words {len(caps)} <= 3 {caps}")
for ch in "%&:":
    check(title.count(ch) <= 1, f"'{ch}' used {title.count(ch)} times <= 1")
if tags:
    check(len(tags) <= 13, f"{len(tags)} tags <= 13")
    for t in tags: check(len(t) <= 20, f"tag '{t}' {len(t)} <= 20")
sys.exit(0 if ok else 1)
