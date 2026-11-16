# Inputs

The user sends a link, or a file. Everything else you get yourself, and ask only for what you cannot get.

## From the link (the script)

The video with its sound, and from the post: account, date, likes, comments, caption, and the text of the latest comments with a count of those tagging a friend. Likes may come back hidden: then use comments for resonance and say so.

## Plays and the baseline

The link does not give plays, or the account's other reels. Get both from the account's Reels tab, `https://www.instagram.com/<account>/reels/`, where every thumbnail shows its play count.

**With a browser** (any browser tool in this session): open the Reels tab and read the play count of this reel and of the recent ones. Decline cookies and close any sign up prompt; no login is needed. 12 to 20 reels is enough: scroll once if fewer show. Leave out pinned reels. If the browser can run a page script, this reads them all at once:

```js
[...document.querySelectorAll('a[href*="/reel/"]')].map(a => a.getAttribute('href') + ' | ' + a.innerText.replace(/\n/g, ' ') + ' | pinned: ' + !!a.querySelector('svg[aria-label*="inned"]'))
```

Then hand the codes and plays to the script, this reel included. It fetches likes, comments and dates for each reel and works out the medians and this reel's multiples in `baseline.md`:

```bash
python3 <skill folder>/scripts/extract.py "<reel link>" --baseline "DeorJJENC7H=95.2k,DebzpEkqnLg=1.4m,DdbGZDbKded=6.6m"
```

Do not hover or open reels in the browser to read likes: the script does it in seconds. Use `baseline.md` for the verdict table.

**Without a browser, or if the page will not load:** ask once for a screenshot of the Reels tab. One screen of 9 to 12 reels is enough; two are better. Work out the medians from the plays on it.

Use the browser only to read numbers. Never to watch the reel.

## Reading numbers

Write every number down before using it. Instagram rounds large numbers (216K, 1.2M): keep the rounding, do not invent precision. If a number is cut off or unclear, say so rather than guess.

## A thin baseline

If the account has fewer than 5 reels, say the baseline is thin and lower the confidence of the verdict.

## Going deeper (the line after the report)

The public numbers cannot show shares, saves, the skip rate or the retention graph. Those only exist for the account owner. After the report, offer once:

> If this is your account, I can go deeper: connect your Instagram data (Supermetrics, Porter Metrics, Metricool, Composio or similar), or send screenshots of this reel's Insights. Then I can show the second people left and how many sent it on.

**With a connector:** pull this reel's views, reach, likes, comments, shares, saves, follows, average watch time and anything else offered (skip rate, views by source, followers versus non-followers), and the same for the account's recent reels. If the connector's tools are not in the session, say so in one line and ask for the Insights screenshots instead.

**With Insights screenshots:** look for views, accounts reached, followers versus non-followers, likes, comments, shares, saves, follows, average watch time, skip rate and the typical skip rate beside it, the retention graph, and views by source (Reels tab, Explore, Feed, Profile, Stories).

Then update the report: the verdict, the causes and the leak, now with the real signals.
