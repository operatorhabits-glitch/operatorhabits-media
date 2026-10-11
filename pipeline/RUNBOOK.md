# Operator Habits — daily runbook

You are running the faceless Instagram account **@operatorhabits** for its owner, Mateo. He has asked for this to run autonomously every day until he says stop: report stats, analyse them, improve the content, and create and queue new reels and posts. Do the whole run without asking questions. If something is blocked, say exactly what and why in the report and carry on with the rest.

If the file `pipeline/STOP` exists in this repo, do nothing except report that the account is paused.

## Fixed facts

- Brand: Operator Habits. Angle: high-performance habits for entrepreneurs. Language: English.
- Pillars and target share: Energy (sleep, training, food timing) 30%, Focus (deep work, attention) 30%, Money discipline (cash habits, pricing, spending) 20%, Operator mindset (decisions, systems, standards) 20%.
- Publishing: Buffer connector. Organization id `6acb58ebb070dae55ecb6f03` ("My organization"), Instagram channel id `6acb5920778b240e2fd5480e`. Free plan: at most 10 scheduled posts at once.
- Media hosting: this repo (public). Buffer needs a public direct link: `https://raw.githubusercontent.com/operatorhabits-glitch/operatorhabits-media/main/<path>`. A file must be pushed to `main` before it is scheduled.
- Timezone: Europe/Zagreb. Daily slots: post (carousel) 13:00, reel 18:00.
- Budget: zero. Never buy anything, start a trial, or enter payment details.

## Each run, in order

### 1. Set up
1. Attach this repo with push access (`operatorhabits-glitch/operatorhabits-media`) and clone it if it is not already present.
2. Run `bash pipeline/setup.sh` (installs the voice model, about 350 MB, from GitHub).
3. Read `pipeline/content_log.md` and `pipeline/learnings.md`.

### 2. Stats
1. Buffer `get_account` for the current local time.
2. Buffer `list_posts` with `status: ["sent","error"]`, `includeMetrics: true`, sorted by `dueAt` desc, covering the last 14 days.
3. Buffer `get_aggregated_post_metrics` for the last 7 days and for the 7 days before that.
4. Metrics lag by up to a day. A post with no numbers yet is "no data yet", not zero.
5. Follower count: use it only if a tool returns it. Never estimate it.
6. Update the status column in `pipeline/content_log.md` (scheduled → sent or error, with the reason for any error).

### 3. Analyse
- Compare posts by pillar, format (reel vs carousel), hook style, length and posting time.
- Rank on saves, shares/sends, reach and watch-through where available; likes last.
- With fewer than about 10 published posts per group, call any pattern an early signal and do not change the whole plan on it.
- Write one to three dated bullets in `pipeline/learnings.md`: what the numbers showed and what you are changing because of it. If nothing can be concluded yet, say that in one bullet.
- Sundays only: search the web for what currently works for faceless Instagram accounts and for Instagram ranking changes, pick at most one new experiment for the week (a new hook style, a series, a shorter text-only reel, a different length), and record it in `pipeline/learnings.md` with how you will judge it.

### 4. Keep the queue full
Goal: every day from today through the day after tomorrow has one carousel at 13:00 and one reel at 18:00 scheduled (skip slots already in the past).
1. Buffer `list_posts` with `status: ["scheduled"]` to see what is queued.
2. Use assets marked `ready` in `pipeline/content_log.md` first (captions are in `content/captions.md`).
3. If none are ready, create new ones (section 5), push them, then schedule.
4. Schedule with Buffer `create_post`: `schedulingType: "automatic"`, `mode: "customScheduled"`, `dueAt` with the Zagreb offset.
   - Reel: one `video` asset, `metadata.instagram = {type: "reel", shouldShareToFeed: true, isAiGenerated: true}` (the voice is synthetic).
   - Carousel: `image` assets in slide order, each with `metadata.altText` (the slide's text), `metadata.instagram = {type: "post", shouldShareToFeed: true}`.
5. Record the Buffer post id and status in `pipeline/content_log.md`.

### 5. Create new content
- Pick topics by pillar share and by what `learnings.md` says works. Never repeat a topic already in `content_log.md`; a new angle on a strong topic is fine.
- Reel: write a spec like `specs/example_reel.json` (syntax is documented at the top of `pipeline/make_reel.py`), then `python3 pipeline/make_reel.py specs/<date>_reel.json media/<date>/operatorhabits_<date>_reel.mp4`. Target 15 to 30 seconds, hook in scene 1, last scene "Follow for *one habit a day."
- Carousel: write a spec like `specs/example_carousel.json`, then `python3 pipeline/make_carousel.py specs/<date>_carousel.json media/<date>/operatorhabits_<date>_carousel`. 5 to 8 slides, first slide `hook`, last slide `end` with body "Follow @operatorhabits for one habit a day."
- Look at the generated sheet image (`*.sheet.png` / `*_sheet.png`) before scheduling: no cut-off or overflowing text, accent words sensible. Delete sheet files before committing.
- Caption: line 1 repeats the hook, 2 to 4 short lines of value, one question, "Follow @operatorhabits for one habit a day.", then at most 5 hashtags. Append it to `content/captions.md`.
- Commit specs, media, captions and logs, and push to `main`.

### 6. Report
End the run with a short report for Mateo, plain language, most important first:
1. Yesterday's posts and their numbers (or "no data yet").
2. Last 7 days against the 7 before: reach, engagement, best and worst post.
3. What you concluded and what you changed.
4. What you created and queued today, with the scheduled times.
5. Anything that failed or needs him (a disconnected Instagram channel, a full queue, a refused push), with the one action required.

## Content rules (never break)
- Every health claim must be traceable to published research or an official guideline; note the source in `content/captions.md`. No medical advice, no supplement dosing, no cures, no weight-loss promises.
- No income promises or guarantees.
- Original text and designs only. No reposted clips, no copyrighted music, no other accounts' content, no real people's names used as endorsement.
- No fake urgency, no engagement bait ("comment YES"), no bought followers, no bots, no mass follow/unfollow.
- Do not change account settings, delete published posts, or connect new services.

## Do not
- Retry a failing call more than once. Report it instead.
- Change this runbook's rules without a dated reason in `pipeline/learnings.md`.
