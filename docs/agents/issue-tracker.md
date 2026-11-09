# Sonic Rift issue tracker

GitHub Issues is the authoritative planning and delivery ledger for this repository. Follow the repository's [Wayfinder map](https://github.com/Knapp-Kevin/sonic-rift/issues/149) for the multitrack-studio and local-agent program. Do not claim a branch, PR, test plan or closed decision is shipped or validated without the corresponding evidence.

## Wayfinding operations

These conventions follow [Matt Pocock's Wayfinder skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md). Wayfinder **plans** through questions whose resolutions are decisions; implementation work belongs in separate delivery issues and PRs.

1. **Map:** one canonical issue with label `wayfinder:map`. Its `Destination` is the scope boundary; `Decisions so far` links to closed ticket resolution comments without repeating full decisions; `Not yet specified` holds only fog that cannot yet be phrased as a question; `Out of scope` is explicit.
2. **Decision tickets:** questions, one per issue, labelled `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, or `wayfinder:task`. Never disguise build work as a Wayfinder decision. The assignee, when present, is the ticket claim. Research tickets can proceed independently; never silently answer on behalf of the human on a HITL ticket.
3. **Children and blocking:** prefer GitHub's native sub-issue/blocked-by relationships when the active authorized client supports **writes** to them. The ChatGPT GitHub connector used when this document was written does **not** provide those mutation actions. Its fallback is links in both issues and a `Blocked by` section, named with issue titles and URLs. This is **not** equivalent to native issue relations; do not claim it is. Backfill native relationships through GitHub UI or a client with explicit access, and verify through readback.
4. **Frontier:** query open, unassigned, unblocked **decision** tickets under the map. On native links, use child and blocked-by relationships; on fallback, inspect the `Blocked by` issue links as well as status. Delivery issues are not the Wayfinder frontier.
5. **Resolution:** claim only the selected ticket, gather evidence, post a decision as a resolution comment, close that ticket, then add a one-line titled link to the map's `Decisions so far`. Stop at one ticket per session except independent research. If a previously foggy question becomes precise, create a new ticket and remove that fog description from the map; do not duplicate it.
6. **Delivery:** after the map is decision-complete, hand off to a spec and delivery tickets with explicit prerequisites and acceptance tests. Owner-approved urgent work can execute in separately tracked issues while the decision map remains open. A draft PR is not a completed delivery.

## Canonical current program

- [Sonic Rift precision editing + safe agent control map](https://github.com/Knapp-Kevin/sonic-rift/issues/149)
- [Studio parent scope and acceptance](https://github.com/Knapp-Kevin/sonic-rift/issues/148)
- [MCP parent architecture and stages](https://github.com/Knapp-Kevin/sonic-rift/issues/130)
- [Existing composer and long-project render gate](https://github.com/Knapp-Kevin/sonic-rift/issues/71)
- [Windows application acceptance](https://github.com/Knapp-Kevin/sonic-rift/issues/61)

Use search by title and labels rather than copying a static issue number list into every document. Keep the map and GitHub issues current, especially when an architectural decision changes the delivery order.

## Safety and evidence

- Never trigger GitHub Actions just to update the planning ledger; prefer `[skip ci]` on planning/doc-only commits when CI budget is restricted.
- Model downloads, new cloud exposure and changes to user files require approval under their own acceptance gates. An external MCP agent never inherits file/system permissions from a localhost transport.
- A PR requiring a real Windows/SDK/GUI/audio acceptance gate remains draft/HOLD if that gate has not run on the exact head.
