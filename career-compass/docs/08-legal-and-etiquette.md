# 08 — Legal posture and etiquette

This system reads other organizations' public content on a schedule. That
deserves an explicit posture rather than a shrug, both because it is right and
because a tool that gets an IP range blocked is a tool that stops working.

## Rules

1. **Public, unauthenticated content only.** No logging in, no session
   cookies, no accessing anything a signed-out visitor could not see.
2. **`robots.txt` is honored.** Checked before every fetch, cached per host,
   and a disallowed path is skipped and logged. No override flag exists,
   deliberately.
3. **Prefer the front door.** Official APIs, RSS/Atom feeds, and the public
   JSON endpoints that a site's own careers page calls, in that order. HTML
   scraping is a last resort; a JSON endpoint is both more stable and more
   clearly intended for programmatic use.
4. **Identify honestly.** A real User-Agent naming this tool and a contact
   address. Never a browser impersonation string.
5. **Be slow.** One request per second per host, jitter, conditional requests,
   and back off hard on 429/503 with `Retry-After` honored. The dataset is
   small and there is no deadline; there is never a reason to be fast.
6. **No defense circumvention.** No CAPTCHA solving, no headless-browser
   fingerprint evasion, no proxy rotation, no retrying a 403 from a different
   address. A block is an answer, and the answer is respected.
7. **Personal use only.** Nothing ingested here is redistributed, republished,
   or resold. This repo is private and stays private.
8. **No personal data.** Companies and documents, not people. No scraping of
   employee profiles, no building a dossier on a hiring manager, no social
   graph of who works where. If a name appears as a blog post's byline, that
   is incidental and it is not indexed or analyzed.

## When a source says no

That is what `manual/inbox/` is for. If a careers page is JS-rendered behind
bot protection, the answer is not a better scraper — it is that I open the
page like a person, copy the posting, and drop it in the inbox. Same pipeline,
zero adversarial engineering, and the resulting data is often better because
I've actually read it.

This is the real reason manual input is an adapter (ADR-0006) and not a
fallback: it makes the polite path the *convenient* path.

## Terms of service

Some sites' terms restrict automated access even to public pages. Rule 3
handles most of this in practice, but where a company's terms are explicit,
that company's sources are marked:

```yaml
- company: exampleco
  adapter: manual.inbox
  reason_no_automation: "ToS §4 prohibits automated collection"
```

The `reason_no_automation` field exists so the decision is recorded in the
config rather than remembered — and so a future me doesn't "fix" the missing
automation.

## Data retention

Raw payloads are kept indefinitely; they are small and they are the basis of
replay (ADR-0002). If that changes, `career prune --before <date>` should drop
raw bytes while keeping `document` rows, accepting the loss of replayability
for those documents and recording it in the ledger.
