"""Go-to-definition from a Python language server, at every position of a list: how pyright
and ty answer the names mypy recorded (bench/py_oracle/oracle.py). The standard library
only; the server is a command of its own environment.

    python lsp.py OUT.jsonl WORKSPACE POSITIONS-FILE PYTHON -- SERVER-COMMAND...

WORKSPACE is the workspace folder the server is given: the directory the top package
sits in, or one whose configuration file points there. POSITIONS-FILE lists
`FILE<TAB>LINE<TAB>COL` (an absolute path, a 1-based line, a 0-based UTF-16 column).
PYTHON is the interpreter whose site-packages hold the dependencies. Each position gets one
record, {"file", "line", "col", "defs": [[PATH, LINE, COL], ...]} with the absolute path
and the 1-based line and 0-based column a definition starts at, or {"error": ...} when
the server answered with one or not within the time out. A record also says whether the
position lies where the server's own diagnostics call the code unreachable
("unreachable", from a pull of the file's diagnostics), and, where it gave no definition,
what its hover says the name is ("hover": its first line, `Never` in ty's unreachable
code).
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

TIMEOUT = 300   # seconds for the answers of one file
UNNECESSARY = 1   # DiagnosticTag.Unnecessary: pyright and ty tag unreachable code so
# pyright: "Code is structurally unreachable", "Code is not analyzed because condition is
# statically evaluated as false"; ty: "Code is (always) unreachable"
UNREACHABLE = ("unreachable", "not analyzed")


class Server:
    def __init__(self, cmd: list[str], root: Path, python: str):
        env = dict(os.environ, VIRTUAL_ENV=str(Path(python).parent.parent))
        env["PATH"] = f"{Path(python).parent}{os.pathsep}{env.get('PATH', '')}"
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, cwd=root, env=env)
        self.python = python
        self.answers: queue.Queue = queue.Queue()
        self.next_id = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        out = self.proc.stdout
        while True:
            length = None
            while True:
                line = out.readline()
                if not line:
                    self.answers.put(None)
                    return
                line = line.strip()
                if not line:
                    break
                key, _, value = line.decode().partition(":")
                if key.lower() == "content-length":
                    length = int(value)
            msg = json.loads(out.read(length))
            if "method" in msg and "id" in msg:
                self._answer_request(msg)
            elif "id" in msg:
                self.answers.put(msg)

    def _answer_request(self, msg: dict) -> None:
        if msg["method"] == "workspace/configuration":
            result = [self._setting(item.get("section", "")) for item in msg["params"]["items"]]
        else:   # client/registerCapability, window/workDoneProgress/create, ...
            result = None
        self.send({"jsonrpc": "2.0", "id": msg["id"], "result": result})

    def _setting(self, section: str):
        if section == "python":
            return {"pythonPath": self.python, "analysis": self._setting("python.analysis")}
        if section == "python.analysis":
            return {"diagnosticMode": "openFilesOnly", "typeCheckingMode": "off",
                    "autoSearchPaths": False}
        return {}

    def send(self, msg: dict) -> None:
        data = json.dumps(msg).encode()
        self.proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(data) + data)
        self.proc.stdin.flush()

    def notify(self, method: str, params) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params) -> int:
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
        return self.next_id

    def wait(self, ids: set[int], timeout: float) -> dict[int, dict]:
        got: dict[int, dict] = {}
        end = time.monotonic() + timeout
        while ids - got.keys():
            try:
                msg = self.answers.get(timeout=max(0.0, end - time.monotonic()))
            except queue.Empty:
                break
            if msg is None:
                break
            got[msg["id"]] = msg
        return got


def within(line: int, col: int, rng: dict) -> bool:
    """Whether a 0-based position lies in an LSP range."""
    start, end = rng["start"], rng["end"]
    return (start["line"], start["character"]) <= (line, col) < (end["line"], end["character"])


def path_of(uri: str) -> str:
    return unquote(urlparse(uri).path)


def main() -> int:
    sep = sys.argv.index("--")
    out, root, positions, python = sys.argv[1:sep]
    cmd = sys.argv[sep + 1:]
    root_path = Path(root).resolve()
    by_file: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for line in Path(positions).read_text().splitlines():
        if line:
            f, ln, col = line.split("\t")
            by_file[f].append((int(ln), int(col)))

    server = Server(cmd, root_path, python)
    uri = root_path.as_uri()
    init = server.request("initialize", {
        "processId": os.getpid(), "rootUri": uri,
        "workspaceFolders": [{"uri": uri, "name": root_path.name}],
        "capabilities": {
            "general": {"positionEncodings": ["utf-16"]},
            "textDocument": {"definition": {"linkSupport": True},
                             "hover": {"contentFormat": ["plaintext"]},
                             "diagnostic": {"dynamicRegistration": False},
                             # pyright sends its hints of unreachable code only to a client
                             # that shows Unnecessary
                             "publishDiagnostics": {"tagSupport": {"valueSet": [UNNECESSARY]}}},
            "workspace": {"configuration": True, "workspaceFolders": True}},
        "initializationOptions": {}})
    if init not in server.wait({init}, 120):
        sys.exit(f"lsp: {cmd[0]} did not initialize")
    server.notify("initialized", {})

    records = []
    for rel, places in sorted(by_file.items()):
        path = Path(rel)
        doc = path.as_uri()
        server.notify("textDocument/didOpen", {"textDocument": {
            "uri": doc, "languageId": "python", "version": 1,
            "text": path.read_text(encoding="utf-8")}})
        ids = {server.request("textDocument/definition", {
            "textDocument": {"uri": doc}, "position": {"line": ln - 1, "character": col}}):
               (ln, col) for ln, col in places}
        pull = server.request("textDocument/diagnostic", {"textDocument": {"uri": doc}})
        got = server.wait({*ids, pull}, TIMEOUT)
        unreachable = [d["range"] for d in ((got.get(pull) or {}).get("result") or {}).get(
            "items", []) if UNNECESSARY in (d.get("tags") or [])
            and any(w in d["message"] for w in UNREACHABLE)]
        file_recs = []
        for i, (ln, col) in ids.items():
            rec = {"file": rel, "line": ln, "col": col}
            msg = got.get(i)
            if msg is None:
                rec["error"] = "no answer"
            elif "error" in msg:
                rec["error"] = msg["error"].get("message", "error")
            else:
                result = msg.get("result") or []
                if isinstance(result, dict):
                    result = [result]
                defs = []
                for loc in result:
                    target = loc.get("targetUri", loc.get("uri"))
                    rng = loc.get("targetSelectionRange") or loc.get("range")
                    defs.append([path_of(target), rng["start"]["line"] + 1,
                                 rng["start"]["character"]])
                rec["defs"] = defs
            rec["unreachable"] = any(within(ln - 1, col, r) for r in unreachable)
            file_recs.append(rec)
        # what a name with no definition is, as the server's hover says
        hovers = {server.request("textDocument/hover", {
            "textDocument": {"uri": doc}, "position": {"line": rec["line"] - 1,
                                                        "character": rec["col"]}}): rec
                  for rec in file_recs if rec.get("defs") == []}
        said = server.wait(set(hovers), TIMEOUT)
        for i, rec in hovers.items():
            contents = ((said.get(i) or {}).get("result") or {}).get("contents")
            if isinstance(contents, list):   # MarkedString[]
                contents = contents[0] if contents else ""
            value = contents.get("value", "") if isinstance(contents, dict) else str(contents or "")
            rec["hover"] = value.strip().split("\n", 1)[0]
        records += file_recs
        server.notify("textDocument/didClose", {"textDocument": {"uri": doc}})
    bye = server.request("shutdown", None)
    server.wait({bye}, 30)
    server.notify("exit", None)
    try:
        server.proc.wait(10)
    except subprocess.TimeoutExpired:
        server.proc.kill()
    Path(out).write_text("".join(json.dumps(r) + "\n" for r in records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
