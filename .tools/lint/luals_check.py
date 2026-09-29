#!/usr/bin/env python3
"""Run lua-language-server --check and gate on NEW diagnostics only.

The codebase predates any type annotations, so a full check reports thousands
of existing findings. Instead of failing on those, every finding is reduced to
a line-independent fingerprint (file, diagnostic code, message) and compared
against the committed baseline (.tools/lint/luals-baseline.json). The check
fails only when a fingerprint's count goes UP -- a ratchet: existing debt is
tolerated, new debt is not, and fixed debt is locked in with --update-baseline.

Usage:
  .tools/lint/luals_check.py                    # check against the baseline
  .tools/lint/luals_check.py --update-baseline  # accept the current state
"""
import argparse
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LUALS = os.path.join(ROOT, ".tools", "cache", "luals", "bin", "lua-language-server")
BASELINE = os.path.join(ROOT, ".tools", "lint", "luals-baseline.json")
# Only diagnostics that do not depend on type inference can fail the build:
# LuaLS inference is not perfectly stable between runs, so a type-driven finding
# can appear in code nobody touched. Everything else is reported as advisory.
BLOCKING = {
    "undefined-global",        # typo, or an API that does not exist
    "lowercase-global",        # missing `local`: leaks into _G (taint risk)
    "global-element",
    "duplicate-index",         # same key twice in a table constructor
    "duplicate-set-field",     # method defined twice, first silently lost
    "unbalanced-assignments",
    "redundant-value",
    "count-down-loop",
    "newline-call",
    "newfield-call",
    "code-after-break",
    "unreachable-code",
}


def run_luals():
    logdir = tempfile.mkdtemp(prefix="luals-")
    try:
        subprocess.run(
            [LUALS, f"--check={ROOT}", "--checklevel=Information",
             "--check_format=json", f"--logpath={logdir}"],
            check=False, stdout=subprocess.DEVNULL,
        )
        out = os.path.join(logdir, "check.json")
        if not os.path.exists(out):  # LuaLS < 3.9 writes nothing on a clean run
            return {}
        with open(out, encoding="utf-8") as f:
            return json.load(f)
    finally:
        shutil.rmtree(logdir, ignore_errors=True)


def collect(raw):
    """-> list of (fingerprint, line, severity) with repo-relative paths."""
    found = []
    for uri, items in raw.items():
        path = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        for it in items:
            fp = (rel, it["code"], it["message"])
            found.append((fp, it["range"]["start"]["line"] + 1, it.get("severity", 2)))
    return found


def key(fp):
    return "\x1f".join(fp)


def load_baseline():
    if not os.path.exists(BASELINE):
        return collections.Counter()
    with open(BASELINE, encoding="utf-8") as f:
        data = json.load(f)
    counts = collections.Counter()
    for rel, entries in data.items():
        for e in entries:
            counts[key((rel, e["code"], e["message"]))] = e["count"]
    return counts


def write_baseline(found):
    counts = collections.Counter(key(fp) for fp, _, _ in found)
    by_file = collections.defaultdict(list)
    for k, n in counts.items():
        rel, code, msg = k.split("\x1f")
        by_file[rel].append({"code": code, "message": msg, "count": n})
    data = {rel: sorted(v, key=lambda e: (e["code"], e["message"])) for rel, v in sorted(by_file.items())}
    with open(BASELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return sum(counts.values())


def gh_escape(s):
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update-baseline", action="store_true", help="rewrite the baseline from the current state")
    args = ap.parse_args()

    if not os.path.exists(LUALS):
        sys.exit("lua-language-server not found -- run .tools/lint/fetch-tools.sh first")

    found = collect(run_luals())

    if args.update_baseline:
        total = write_baseline(found)
        print(f"Baseline updated: {total} known findings in {os.path.relpath(BASELINE, ROOT)}")
        return 0

    baseline = load_baseline()
    current = collections.Counter(key(fp) for fp, _, _ in found)
    grown = {k: current[k] - baseline[k] for k in current if current[k] > baseline[k]}
    blocking = {k: n for k, n in grown.items() if k.split("\x1f")[1] in BLOCKING}
    shrunk = sum(baseline[k] - current[k] for k in baseline if baseline[k] > current[k])

    # Report every occurrence of a fingerprint that grew: with a line-independent
    # fingerprint we cannot tell which of N identical findings is the new one.
    new = [(fp, line, sev) for fp, line, sev in found if key(fp) in grown]
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    for (rel, code, msg), line, sev in sorted(new):
        if in_ci:
            level = "error" if code in BLOCKING else "warning"
            print(f"::{level} file={rel},line={line},title={code}::{gh_escape(msg)}")
        else:
            tag = "BLOCKING" if code in BLOCKING else "advisory"
            print(f"{rel}:{line}: [{code}] ({tag}) {msg.splitlines()[0]}")

    summary = [f"LuaLS: {sum(current.values())} findings, baseline {sum(baseline.values())}."]
    advisory = sum(grown.values()) - sum(blocking.values())
    if blocking:
        summary.append(f"FAIL: {sum(blocking.values())} new blocking finding(s) above the baseline (listed above).")
        summary.append("Fix them, or if they are intentional/false positives run "
                       ".tools/lint/luals_check.py --update-baseline and commit the result.")
    else:
        summary.append("OK: no new blocking findings.")
    if advisory:
        summary.append(f"{advisory} new advisory (type-inference) finding(s) -- worth a look, not failing.")
    if shrunk:
        summary.append(f"{shrunk} baseline finding(s) are fixed -- run --update-baseline to lock that in.")
    print("\n".join(summary))
    if in_ci and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n\n".join(summary) + "\n")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
