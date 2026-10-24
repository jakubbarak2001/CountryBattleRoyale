# Round motion, sound, and performance

Direction: crisp and tactile, preserving the existing paper, ink, typography, and accent colors.

## First pass

- Reuse an indexed country snapshot in each worker. File metadata detects replacements; refreshes publish the complete file atomically. Keep the existing seven-day expiry policy.
- Reuse the comparison already calculated when creating or answering a round.
- Give selection an immediate visual response while the request runs. Allow one round request at a time, including the externally associated draw button.
- Keep result feedback below the cards and use the same mobile stat layout before and after answering.
- Present scoring as two small items, "More people +1" and "More land +1", with the tie hint beside the draw action. Remove the repeated instructions and numeric examples.
- Use green for the winning country's surface, rule, standing, and score, red for an incorrect country pick, and muted blue for draws and the draw action. An incorrect country pick during a draw stays red to identify the wrong choice. Unselected losing cards stay neutral. Keep words and icons alongside the color cues.
- Reveal population and area with a 65 ms stagger. Add a small winner emphasis and streak pulse. The longest reveal is 410 ms; next-round entrances finish within 330 ms. Fetching starts immediately and has no artificial minimum wait.
- Use native Web Animations for opacity and transforms. Reduced-motion preferences skip JS animations as well as CSS transitions, including when the preference changes during a reveal.
- Synthesize quiet selection, next-round, correct, and incorrect cues through Web Audio. Start muted, remember the sound preference, initialize audio on interaction, and stop queued cues when muted or the tab is hidden.
- Preserve keyboard continuity, announce round changes, and show recoverable errors inline. A lost answer response is treated as an uncertain save and is never automatically resubmitted.

## Evidence and limits

Before this change, an isolated check of the country helper call chains counted 10 JSON parses for a new matchup and 8 for an answer, with a fresh cache. Those counts describe server work, not elapsed time. The cache tests now require a single parse across repeated lookups and rounds until the file changes; subsequent warm calls reuse memory.

| Browser metric | Baseline | After change |
| --- | --- | --- |
| Largest Contentful Paint | Not measured | Not measured |
| Interaction to Next Paint | Not measured | Not measured |
| Cumulative Layout Shift | Not measured | Not measured |
| Round response time | Not measured | Not measured |

The round script was originally 2 KB, so script size was not evidence of a loading bottleneck. Browser traces and production latency measurements are still needed to quantify the improvement. No animation library or audio downloads are added.

## Next performance pass

1. Record cold and repeat page loads plus answer/next requests on the deployed app, using a mobile viewport and slower CPU/network settings. Separate country lookup, database connection, query, and template-rendering time.
2. Measure motion and scrolling on the target phone and desktop. Check long country names, draws, correct and incorrect results, repeated clicks, keyboard use, offline recovery, muted/blocked audio, and reduced motion.
3. If cache refresh dominates cold or expired-cache requests, move refresh to an explicit warm-up or scheduled task and define how long a last-good snapshot may be served. The three API requests currently remain synchronous when a download is needed.
4. If database connection setup dominates warm requests, evaluate a bounded connection pool against the deployment's worker count.
5. Check deployed static response compression, cache headers, and font loading before changing them. Cache static assets with versioned URLs; keep personalized rounds out of shared caches.

Do not prefetch the current next-round GET: it issues a database round and changes the session cookie. Any later prefetch design needs an explicit preparation/activation contract so it cannot invalidate the visible matchup.

## References

- [web.dev: performant animation properties](https://web.dev/articles/animations-guide)
- [MDN: Web Audio activation and user controls](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices)
- [web.dev: measure the loading path before optimizing it](https://web.dev/articles/optimize-lcp)
