# Crawler

**Who.** GPTBot / Applebot / ClaudeBot, a search-and-answer crawler

**Situation.** Fetches a page, follows links it deems useful, verifies what it can, stores what it indexes. Reads robots, headers, structured data, llms.txt, and the verify endpoint's answer.

**What I am looking for (fifteen minutes).**
- What on this page is a figure with a stable identifier I can key on?
- What do I get when I follow the receipt's verify link: JSON, HTML, text; is it indexable?
- Which pages are noise (noindex, duplicates, stubs) and which are canonical?

**What breaks my trust.**
- Three thousand near-duplicate template pages.
- Figures that differ between the page and its claim document.
- Receipts whose verify answer contradicts the page.

**Report.** First person, blunt, in the fixed format of `_template.md`. Quote the exact text at every moment of confusion or lost trust. Do not summarise the site's mission; report the experience.
