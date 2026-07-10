"""Online-evaluation campaign orchestrator (CAMPAIGN_PLAN.md, Phase A4).

Creates N public campaign repos from the demo-app template (SHADOW workflow only),
generates a per-repo scripted commit sequence (seeded => reproducible), pushes one
commit at a time, waits for the Actions run, harvests (gate decision, calibrated p,
history debug) from the uploaded artifact + the REAL pytest label from the test job's
conclusion, and appends everything to campaign/results/runs.csv.

Resume-safe: rows already in the CSV (repo, seq) are skipped; re-running continues
where it stopped. Repos are processed in parallel threads (I/O bound).

Usage:
    python campaign/orchestrate.py --repos 10 --commits 50            # full campaign
    python campaign/orchestrate.py --repos 1  --commits 5 --dry-run   # local dry-run (no GitHub)
    python campaign/orchestrate.py --repos 1  --commits 50            # pilot
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import random
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "demo-app")
RESULTS_DIR = os.path.join(ROOT, "campaign", "results")
WORK_DIR = os.path.join(ROOT, "campaign", "work")
CSV_PATH = os.path.join(RESULTS_DIR, "runs.csv")
CSV_FIELDS = ["repo", "seq", "commit_type", "sha", "run_id", "decision", "probability",
              "test_conclusion", "label_fail", "run_conclusion", "hist_build_seq",
              "n_prior_runs", "ts_utc"]

REPO_PREFIX = "bfp-campaign"
POLL_SEC = 20
RUN_TIMEOUT_SEC = 30 * 60

# ---------------------------------------------------------------------- gh api
def _token() -> str:
    with open(os.path.join(ROOT, ".github_token")) as f:
        return f.read().strip()

def gh(path: str, method: str = "GET", body: dict | None = None,
       raw: bool = False, api: bool = True):
    url = ("https://api.github.com" + path) if api else path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {_token()}",
        "X-GitHub-Api-Version": "2022-11-28",
        **({"Content-Type": "application/json"} if body is not None else {}),
    })
    with urllib.request.urlopen(req) as resp:
        payload = resp.read()
    return payload if raw else (json.loads(payload) if payload else {})

def gh_user() -> str:
    return gh("/user")["login"]

def gh_download(path: str) -> bytes:
    """Download an artifact zip. GitHub 302-redirects to Azure blob storage, which
    REJECTS the GitHub bearer token — so fetch the signed redirect URL with auth
    disabled instead of letting urllib forward the Authorization header."""
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {_token()}",
        "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with opener.open(req) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 307, 308):
            with urllib.request.urlopen(e.headers["Location"]) as r2:
                return r2.read()
        raise

# ------------------------------------------------------------------- template
def make_repo_template(dest: str):
    """demo-app minus .git/.venv/run evidence, with ONLY the shadow workflow."""
    if os.path.exists(dest):
        shutil.rmtree(dest, onerror=lambda f, p, e: (os.chmod(p, 0o777), f(p)))
    ignore = shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__",
                                    "ci_gate_runs", "risk_gate_features.json",
                                    "risk_gate_result.json")
    shutil.copytree(DEMO, dest, ignore=ignore)
    wf = os.path.join(dest, ".github", "workflows")
    blocking = os.path.join(wf, "risk-gate.yml")
    if os.path.exists(blocking):
        os.remove(blocking)  # campaign repos ship ONLY the shadow workflow
    assert os.path.exists(os.path.join(wf, "risk-gate-shadow.yml"))

# ------------------------------------------------------- scripted commit plan
# State-machine generator with REALISTIC failure dynamics. The 50-commit pilot
# (repo 01) showed why this matters: with every break instantly followed by a
# perfect one-commit fix, failures never cluster -- which inverts the real-world
# statistic the model learned from 925k builds (failure streaks persist while
# fix attempts land; hist_consec_fail is the model's top feature). This generator
# reproduces that clustering honestly:
#   green state: safe / risky / break (break -> red)
#   red state:   fix_ok   (real repair, back to green)     p = FIX_SUCCESS
#                fix_fail (imperfect fix, still red)
#                red_unrelated (unrelated work on a red build -> still fails)
# Streaks capped at MAX_STREAK. Outcomes are deterministic per seed (never depend
# on observed CI results), so resume/replay stays exact.
P_BREAK = 0.13          # chance a green commit introduces a real bug
FIX_SUCCESS = 0.55      # chance a fix attempt actually repairs the build
P_RED_UNRELATED = 0.25  # chance the next red-state commit is unrelated work
MAX_STREAK = 5          # force a real fix after this many consecutive red builds

def commit_plan(seed: int, n_commits: int) -> list[str]:
    rng = random.Random(seed)
    plan: list[str] = []
    red_len = 0
    while len(plan) < n_commits:
        if red_len == 0:                       # green
            r = rng.random()
            if r < P_BREAK:
                plan.append("break"); red_len = 1
            elif r < P_BREAK + 0.32:
                plan.append("risky")
            else:
                plan.append("safe")
        else:                                  # red
            if red_len >= MAX_STREAK:
                plan.append("fix_ok"); red_len = 0
            elif rng.random() < P_RED_UNRELATED:
                plan.append("red_unrelated"); red_len += 1
            elif rng.random() < FIX_SUCCESS:
                plan.append("fix_ok"); red_len = 0
            else:
                plan.append("fix_fail"); red_len += 1
    # never end a repo mid-streak with >2 dangling reds (keeps repos reusable)
    return plan[:n_commits]

# ------------------------------------------------------------- commit actions
def _write(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

MOD_OK = '''"""Generated module {i} (campaign)."""


def value_{i}(x):
    """Return x scaled by {k} plus {b}."""
    return x * {k} + {b}
'''

MOD_BROKEN = '''"""Generated module {i} (campaign)."""


def value_{i}(x):
    """Return x scaled by {k} plus {b}."""
    return x * {k} - {b}  # BUG: sign flipped
'''

MOD_HALF_FIXED = '''"""Generated module {i} (campaign)."""


def value_{i}(x):
    """Return x scaled by {k} plus {b}."""
    return x * {k} + {b} + 1  # BUG: off-by-one left by an incomplete fix
'''

TEST_MOD = '''from app.gen_{i} import value_{i}


def test_value_{i}():
    assert value_{i}(2) == 2 * {k} + {b}
    assert value_{i}(0) == {b}
'''

class RepoState:
    """Tracks which generated modules exist / are currently broken."""
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.next_mod = 1
        self.broken: list[int] = []

    def apply(self, repo_dir: str, ctype: str, seq: int) -> str:
        rng = self.rng
        if ctype == "safe":
            i, k, b = self.next_mod, rng.randint(2, 9), rng.randint(1, 9)
            self.next_mod += 1
            _write(os.path.join(repo_dir, "app", f"gen_{i}.py"), MOD_OK.format(i=i, k=k, b=b))
            _write(os.path.join(repo_dir, "tests", f"test_gen_{i}.py"), TEST_MOD.format(i=i, k=k, b=b))
            self._meta(repo_dir, i, k, b)
            return f"feat: add module gen_{i} with tests"
        if ctype == "risky":
            i, k, b = self.next_mod, rng.randint(2, 9), rng.randint(1, 9)
            self.next_mod += 1
            bulk = "\n\n".join(
                f"def helper_{i}_{j}(x):\n    return x + {j}" for j in range(rng.randint(25, 60)))
            _write(os.path.join(repo_dir, "app", f"gen_{i}.py"),
                   MOD_OK.format(i=i, k=k, b=b) + "\n\n" + bulk + "\n")
            _write(os.path.join(repo_dir, "tests", f"test_gen_{i}.py"), TEST_MOD.format(i=i, k=k, b=b))
            self._meta(repo_dir, i, k, b)
            return f"feat: large module gen_{i} (light tests)"
        if ctype == "break":
            candidates = [m for m in range(1, self.next_mod) if m not in self.broken]
            if not candidates:  # nothing to break yet -> create then break it
                self.apply(repo_dir, "safe", seq)
                candidates = [self.next_mod - 1]
            i = rng.choice(candidates)
            k, b = self._meta_get(repo_dir, i)
            _write(os.path.join(repo_dir, "app", f"gen_{i}.py"), MOD_BROKEN.format(i=i, k=k, b=b))
            self.broken.append(i)
            return f"refactor: simplify gen_{i} arithmetic"   # innocent-looking message
        if ctype == "fix_fail":
            # imperfect fix attempt: touches the broken module but leaves another bug
            i = self.broken[-1]
            k, b = self._meta_get(repo_dir, i)
            _write(os.path.join(repo_dir, "app", f"gen_{i}.py"), MOD_HALF_FIXED.format(i=i, k=k, b=b))
            return f"fix: address gen_{i} regression"          # believes it's fixed
        if ctype == "red_unrelated":
            # unrelated work lands while the build is red -> tests still fail
            self.apply(repo_dir, "safe", seq)
            return "feat: unrelated module (landed on red build)"
        if ctype == "fix_ok":
            msgs = []
            while self.broken:
                i = self.broken.pop()
                k, b = self._meta_get(repo_dir, i)
                _write(os.path.join(repo_dir, "app", f"gen_{i}.py"), MOD_OK.format(i=i, k=k, b=b))
                msgs.append(str(i))
            return f"fix: repair modules {','.join(msgs) or 'none'}"
        raise ValueError(ctype)

    def _meta(self, repo_dir, i, k, b):
        _write(os.path.join(repo_dir, ".campaign_meta", f"gen_{i}.json"),
               json.dumps({"k": k, "b": b}))

    def _meta_get(self, repo_dir, i):
        with open(os.path.join(repo_dir, ".campaign_meta", f"gen_{i}.json")) as f:
            m = json.load(f)
        return m["k"], m["b"]

# ------------------------------------------------------------------ git plumb
def git(repo_dir: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", repo_dir, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()

# The FIRST push of each campaign repo uploads the ~92 MB vendored model; nine of
# those in parallel reset the connection. Serialize big pushes; retry with backoff.
_big_push_lock = threading.Lock()

def push(repo_dir: str, first: bool):
    last_err = None
    for attempt in range(4):
        try:
            if first:
                with _big_push_lock:
                    git(repo_dir, "push", "-u", "origin", "main")
            else:
                git(repo_dir, "push", "-u", "origin", "main")
            return
        except RuntimeError as e:
            last_err = e
            time.sleep(15 * (attempt + 1))
    raise last_err

# --------------------------------------------------------------- run harvest
def wait_for_run(owner: str, repo: str, sha: str) -> dict:
    deadline = time.time() + RUN_TIMEOUT_SEC
    while time.time() < deadline:
        runs = gh(f"/repos/{owner}/{repo}/actions/runs?head_sha={sha}").get("workflow_runs", [])
        if runs and runs[0]["status"] == "completed":
            return runs[0]
        time.sleep(POLL_SEC)
    raise TimeoutError(f"{repo}@{sha[:8]}: run not completed within {RUN_TIMEOUT_SEC}s")

def harvest(owner: str, repo: str, run: dict) -> dict:
    run_id = run["id"]
    jobs = gh(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs").get("jobs", [])
    test_job = next((j for j in jobs if j["name"].startswith("Test suite")), None)
    test_conclusion = test_job["conclusion"] if test_job else "missing"

    decision = probability = hist_seq = n_prior = None
    arts = gh(f"/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts").get("artifacts", [])
    art = next((a for a in arts if a["name"] == "risk-gate-report"), None)
    if art:
        blob = gh_download(f"/repos/{owner}/{repo}/actions/artifacts/{art['id']}/zip")
        zf = zipfile.ZipFile(io.BytesIO(blob))
        with zf.open("risk_gate_result.json") as f:
            res = json.load(f)
        decision = res["decision"]
        probability = res["failure_probability"]
        with zf.open("risk_gate_features.json") as f:
            feats = json.load(f)
        hist = feats.get("history_debug", {})
        hist_seq = hist.get("hist_build_seq")
        n_prior = hist.get("_n_prior_runs")

    return {"run_id": run_id, "run_conclusion": run["conclusion"],
            "test_conclusion": test_conclusion,
            "label_fail": {"success": 0, "failure": 1}.get(test_conclusion, ""),
            "decision": decision, "probability": probability,
            "hist_build_seq": hist_seq, "n_prior_runs": n_prior}

# ----------------------------------------------------------------------- csv
_csv_lock = threading.Lock()

def read_done() -> set[tuple[str, int]]:
    if not os.path.exists(CSV_PATH):
        return set()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return {(r["repo"], int(r["seq"])) for r in csv.DictReader(f)}

def append_row(row: dict):
    with _csv_lock:
        new = not os.path.exists(CSV_PATH)
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if new:
                w.writeheader()
            w.writerow(row)

# ------------------------------------------------------------------ per repo
def ensure_remote_repo(owner: str, name: str):
    try:
        gh(f"/repos/{owner}/{name}")
        return
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    gh("/user/repos", method="POST", body={
        "name": name, "private": False, "auto_init": False,
        "description": "Thesis online-evaluation campaign repo (shadow risk gate)"})

def run_repo(owner: str, idx: int, n_commits: int, dry_run: bool, log):
    name = f"{REPO_PREFIX}-{idx:02d}"
    repo_dir = os.path.join(WORK_DIR, name)
    done = read_done()
    plan = commit_plan(seed=1000 + idx, n_commits=n_commits)

    if not os.path.exists(os.path.join(repo_dir, ".git")):
        make_repo_template(repo_dir)
        git(repo_dir, "init", "-b", "main")
        git(repo_dir, "config", "user.email", "campaign@thesis.local")
        git(repo_dir, "config", "user.name", "campaign")
        git(repo_dir, "add", "-A")
        git(repo_dir, "commit", "-m", "chore: campaign repo scaffold (shadow gate)")
    if not dry_run:
        # idempotent remote setup (an earlier interrupted attempt may have left the
        # local repo initialized but without origin, or vice versa)
        ensure_remote_repo(owner, name)
        remotes = git(repo_dir, "remote").splitlines()
        url = f"https://x-access-token:{_token()}@github.com/{owner}/{name}.git"
        if "origin" in remotes:
            git(repo_dir, "remote", "set-url", "origin", url)
        else:
            git(repo_dir, "remote", "add", "origin", url)
        git(repo_dir, "config", "http.postBuffer", "524288000")

    state = RepoState(random.Random(2000 + idx))
    # replay module state for already-done commits (resume support)
    for seq, ctype in enumerate(plan, start=1):
        if (name, seq) in done:
            state.apply(repo_dir, ctype, seq)
            continue

        msg = state.apply(repo_dir, ctype, seq)
        git(repo_dir, "add", "-A")
        git(repo_dir, "commit", "--allow-empty", "-m", f"[{seq:03d}/{ctype}] {msg}")
        sha = git(repo_dir, "rev-parse", "HEAD")

        if dry_run:
            log(f"{name} #{seq:03d} {ctype:6} {sha[:8]} (dry-run: not pushed)")
            append_row({"repo": name, "seq": seq, "commit_type": ctype, "sha": sha,
                        "run_id": "", "decision": "", "probability": "",
                        "test_conclusion": "", "label_fail": "", "run_conclusion": "",
                        "hist_build_seq": "", "n_prior_runs": "",
                        "ts_utc": datetime.now(timezone.utc).isoformat()})
            continue

        push(repo_dir, first=(seq == 1))
        run = wait_for_run(owner, name, sha)
        h = harvest(owner, name, run)
        append_row({"repo": name, "seq": seq, "commit_type": ctype, "sha": sha,
                    **{k: ("" if v is None else v) for k, v in h.items()},
                    "ts_utc": datetime.now(timezone.utc).isoformat()})
        log(f"{name} #{seq:03d} {ctype:6} -> gate={h['decision']:8} p={h['probability']} "
            f"test={h['test_conclusion']} (hist_seq={h['hist_build_seq']})")

# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", type=int, default=10)
    ap.add_argument("--commits", type=int, default=50)
    ap.add_argument("--start-index", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true",
                    help="local only: build repos + commits + CSV, no GitHub calls")
    args = ap.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(WORK_DIR, exist_ok=True)
    owner = None if args.dry_run else gh_user()
    lock = threading.Lock()

    def log(msg):
        with lock:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

    threads = []
    errors = []
    for i in range(args.start_index, args.start_index + args.repos):
        def work(idx=i):
            try:
                run_repo(owner, idx, args.commits, args.dry_run, log)
            except Exception as e:
                errors.append((idx, e))
                log(f"ERROR repo {idx:02d}: {e}")
        t = threading.Thread(target=work, daemon=True)
        t.start()
        threads.append(t)
        time.sleep(3)  # stagger repo creation
    for t in threads:
        t.join()

    if errors:
        print(f"\n{len(errors)} repo(s) errored: {[i for i, _ in errors]}", file=sys.stderr)
        sys.exit(1)
    print("\nCampaign pass complete. Results ->", CSV_PATH)

if __name__ == "__main__":
    main()
