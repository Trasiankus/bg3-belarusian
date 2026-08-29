"""Build the Belarusian .xml files in raw_xmls/ from translatable_jsons/.

translatable_jsons/ is the source you edit: one .json per .xml, same folder
structure, each entry holding the Belarusian line next to the English,
Russian and Ukrainian source lines for the same contentuid.

raw_xmls/ is generated from it, and is what LSLib converts to .loca to build
the .pak. Only the "bel" field is written out; en/ru/ua are reference only.

A file too large to keep whole may be split into NAME_part1.json,
NAME_part2.json and so on; the parts are merged back into one NAME.xml.

    python tools/build_xmls_from_json.py           # write raw_xmls/
    python tools/build_xmls_from_json.py --check    # verify, write nothing

Output matches the game's own loca-export format exactly: uid-sorted,
tab-indented, CRLF line endings, no trailing newline.
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "translatable_jsons")
OUT = os.path.join(REPO, "raw_xmls")

HEADER = "<?xml version='1.0' encoding='utf-8'?>\r\n<contentList>\r\n"
FOOTER = "</contentList>"


def render(entries):
    """entries: {uid: {"version": str, "bel": str, ...}} -> xml text"""
    parts = [HEADER]
    for uid in sorted(entries):
        e = entries[uid]
        # line breaks inside an entry are \n in json but CRLF in the xml
        text = e.get("bel", "").replace("\r\n", "\n").replace("\n", "\r\n")
        parts.append('\t<content contentuid="%s" version="%s">%s</content>\r\n'
                     % (uid, e.get("version", "1"), text))
    parts.append(FOOTER)
    return "".join(parts)


PART = re.compile(r"^(.*)_part\d+$")


def sources():
    """Map each output .xml (relative path) to the .json file(s) feeding it."""
    groups = {}
    for root, _, files in os.walk(SRC):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            rel = os.path.relpath(os.path.join(root, f), SRC)
            stem = rel[:-5]
            m = PART.match(stem)
            groups.setdefault((m.group(1) if m else stem) + ".xml", []).append(rel)
    return dict(sorted(groups.items()))


def main():
    check = "--check" in sys.argv
    failed = written = 0
    for rel_xml, parts in sources().items():
        entries = {}
        for rel in parts:
            with open(os.path.join(SRC, rel), encoding="utf-8") as fh:
                for uid, e in json.load(fh).items():
                    if uid in entries:
                        raise SystemExit("duplicate contentuid %s across parts of %s" % (uid, rel_xml))
                    entries[uid] = e
        text = render(entries).encode("utf-8")
        dst = os.path.join(OUT, rel_xml)
        label = "%s%s" % (rel_xml, "" if len(parts) == 1 else " (%d parts)" % len(parts))

        if check:
            old = open(dst, "rb").read() if os.path.exists(dst) else None
            status = "ok" if old == text else "DIFFERS"
            if old != text:
                failed += 1
            print("%-8s %-42s %d entries" % (status, label, len(entries)))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(text)
            written += 1
            print("wrote    %-42s %d entries" % (label, len(entries)))

    if check:
        print("\n%s" % ("raw_xmls/ is up to date" if not failed
                        else "%d file(s) out of date - run without --check" % failed))
        return 1 if failed else 0
    print("\nwrote %d files" % written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
