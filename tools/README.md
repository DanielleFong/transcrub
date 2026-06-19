# tools — export your own Claude conversations (with thinking)

The official share/export of a Claude conversation **drops extended-thinking blocks**.
The *authenticated* conversation endpoint keeps them. These scripts drive **your own
already-logged-in browser** (over the Chrome DevTools Protocol) to pull **your own**
conversations as JSON, thinking intact — then `scan.py --type claude-json` turns them
into a co-reading index.

> ⚠️ **Use on your own account only.** This automates requests your browser already makes
> when you read your own history. Respect Anthropic's Terms of Service; this is for
> personal archival/research of your own data. No credentials live in this code — it
> reuses your existing browser session. Nothing is sent anywhere except to the service
> you're already logged into.

## Use
```sh
npm install                       # puppeteer-core
# launch a debuggable browser on a NON-default profile, log into the service:
open -na "Google Chrome" --args --remote-debugging-port=9444 \
  --user-data-dir=/tmp/cdp --remote-allow-origins='*'
# ...log in in that window, then:
node list-convs.mjs               # inventory -> output/_conversation-list.json
node pull-all.mjs                 # pull all (resumable). FROM=YYYY-MM-DD TO=... to window.
node scrape-auth.mjs <uuid> out.json   # one conversation
```
Then point `sources.json` at `tools/output/full` with `"type":"claude-json"` and run `python3 scan.py`.
