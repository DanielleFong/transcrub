#!/usr/bin/env python3
"""
transcrub scanner — build data/index.json from YOUR transcript sources.

Configure sources in sources.json (see sources.example.json), each:
  {"corpus":"cli","klass":"operator-own","type":"claude-code","path":"~/.claude/projects"}
  {"corpus":"web","klass":"operator-own","type":"claude-json","path":"./export"}
  {"corpus":"community","klass":"testimony","type":"text","path":"./uploads"}

types:
  claude-code  — Claude Code .jsonl session transcripts (recursive)
  claude-json  — conversation JSON with a chat_messages[] array (export / API shape),
                 including extended-thinking blocks when present
  text         — plain-text transcripts, best-effort turn split

Output: data/index.json (chronological; each conversation contiguous). The bundled
data/example-index.json is loaded as a fallback by the UI when index.json is absent.
"""
import json, os, glob, re, sys, datetime

ELL = "…"
def clip(s, n):
    s = (s or "").replace("\x00", "")
    return s if len(s) <= n else s[: n - 1] + ELL

# ---- claude-code .jsonl ----
def load_claude_code(corpus, klass, root):
    out = []
    for f in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        if "/subagents/" in f or "/tool-results/" in f:
            continue
        recs = []
        for line in open(f, errors="ignore"):
            line = line.strip()
            if line:
                try: recs.append(json.loads(line))
                except Exception: pass
        sid = os.path.basename(f)[:-6]
        cur = None
        for r in recs:
            m = r.get("message", {}) or {}
            role = m.get("role")
            c = m.get("content")
            if role == "user" and not r.get("isMeta"):
                text = c if isinstance(c, str) else " ".join(
                    b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text") if isinstance(c, list) else ""
                if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                    continue
                if not text or text.strip().startswith(("<command-", "<local-command", "Caveat:", "<system-reminder")):
                    continue
                if cur: out.append(cur)
                cur = {"corpus": corpus, "klass": klass, "source": r.get("sessionId") or sid,
                       "title": "session " + (r.get("sessionId") or sid)[:8], "ts": r.get("timestamp", ""),
                       "model": "", "prompt": text.strip(), "thinking": "", "reply": "", "tools": [], "speaker": "user"}
            elif role == "assistant" and cur is not None:
                cur["model"] = m.get("model") or cur["model"]
                if isinstance(c, list):
                    for b in c:
                        if not isinstance(b, dict): continue
                        if b.get("type") == "text": cur["reply"] = (cur["reply"] + "\n" + b.get("text", "")).strip()
                        elif b.get("type") == "thinking": cur["thinking"] = (cur["thinking"] + "\n" + b.get("thinking", "")).strip()
                        elif b.get("type") == "tool_use": cur["tools"].append(b.get("name", "tool"))
        if cur: out.append(cur)
    return out

# ---- claude-json (chat_messages[] with thinking) ----
def load_claude_json(corpus, klass, root):
    out = []
    for f in sorted(glob.glob(os.path.join(root, "**", "*.json"), recursive=True)):
        try: conv = json.load(open(f))
        except Exception: continue
        conv = conv.get("conv", conv); conv = conv.get("json", conv)
        msgs = conv.get("chat_messages")
        if not isinstance(msgs, list): continue
        name = conv.get("name", os.path.basename(f)); model = (conv.get("model") or "").replace("claude-", "")
        src = conv.get("uuid", os.path.basename(f)[:-5]); cur = None
        for m in msgs:
            blocks = m.get("content") or []
            text = "\n".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text").strip()
            if not text and isinstance(m.get("text"), str): text = m["text"].strip()
            if m.get("sender") == "human":
                if cur: out.append(cur)
                cur = {"corpus": corpus, "klass": klass, "source": src, "title": name,
                       "ts": m.get("created_at", conv.get("created_at", "")), "model": model,
                       "prompt": text, "thinking": "", "reply": "", "tools": [], "speaker": "user"}
            else:
                if cur is None:
                    cur = {"corpus": corpus, "klass": klass, "source": src, "title": name,
                           "ts": m.get("created_at", ""), "model": model, "prompt": "", "thinking": "",
                           "reply": "", "tools": [], "speaker": "assistant"}
                th = "\n\n".join(b.get("thinking", "") for b in blocks if isinstance(b, dict) and b.get("type") == "thinking").strip()
                if th: cur["thinking"] = (cur["thinking"] + "\n\n" + th).strip()
                if text: cur["reply"] = (cur["reply"] + "\n\n" + text).strip()
                cur["tools"] += [b.get("name", "tool") for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
        if cur: out.append(cur)
    return out

# ---- plain text, best-effort ----
def load_text(corpus, klass, root):
    out = []
    for f in sorted(glob.glob(os.path.join(root, "**", "*.txt"), recursive=True)):
        name = os.path.basename(f)[:-4]
        body = open(f, errors="ignore").read().strip()
        if body:
            out.append({"corpus": corpus, "klass": klass, "source": name, "title": name, "ts": "",
                        "model": "", "prompt": "", "thinking": "", "reply": body, "tools": [], "speaker": "assistant"})
    return out

LOADERS = {"claude-code": load_claude_code, "claude-json": load_claude_json, "text": load_text}

def main():
    cfg = "sources.json"
    if not os.path.exists(cfg):
        print("no sources.json — copy sources.example.json and point it at your transcripts.", file=sys.stderr)
        sys.exit(1)
    turns = []
    for src in json.load(open(cfg)):
        fn = LOADERS.get(src["type"])
        if not fn: print("unknown type:", src["type"], file=sys.stderr); continue
        path = os.path.expanduser(src["path"])
        got = fn(src.get("corpus", src["type"]), src.get("klass", "operator-own"), path)
        print("  %-12s %-10s %5d turns  (%s)" % (src.get("corpus"), src["type"], len(got), path), file=sys.stderr)
        turns += got
    for t in turns:
        t["prompt"] = clip(t["prompt"], 2400); t["reply"] = clip(t["reply"], 4000)
        t["thinking"] = clip(t["thinking"], 2500); t["tools"] = t["tools"][:40]; t["ntools"] = len(t["tools"])
    # chronological, conversations contiguous (stable sort on source start-date)
    DEF = "9999"; sd = {}
    for t in turns:
        s0, ts = t["source"], (t.get("ts") or "")
        if ts and (s0 not in sd or ts < sd[s0]): sd[s0] = ts
    turns.sort(key=lambda t: (sd.get(t["source"], DEF) or DEF, t["source"]))
    for i, t in enumerate(turns): t["gid"] = i
    counts = {"total": len(turns),
              "operator_own": sum(1 for t in turns if t["klass"] != "testimony"),
              "testimony": sum(1 for t in turns if t["klass"] == "testimony")}
    os.makedirs("data", exist_ok=True)
    json.dump({"counts": counts, "turns": turns}, open("data/index.json", "w"), ensure_ascii=False)
    print("wrote data/index.json — %d turns" % len(turns), file=sys.stderr)

if __name__ == "__main__":
    main()
