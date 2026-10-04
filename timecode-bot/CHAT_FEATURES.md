# TIMECODE: chat posts and daily games (1 October 2026)

The production source is `mityademon-rgb/media-center-bot`, branch `feature/timecode-media-bot`. Deploy targeted blocks through the workflows in `mityademon-rgb/news`, branch `boom-kadr-deploy`; keep production-only edits intact. Never replace the whole live checkout.

## Unified reports and photos (2 October 2026)

The owner explicitly requested cross-platform sharing on 2 October: collect Telegram and MAX replies and publish one common morning/evening story with the same photos in both messengers. This supersedes the earlier same-messenger-only photo rule.

At 16:00 Moscow request one daily photo, store it with status `collected`, and acknowledge that it will appear in the 20:30 common evening report. Do not publish a standalone daily photo post. Morning reports attach morning check-in photos. Evening reports attach evening check-in photos AND daily 16:00 photos; retain two different pictures by the same author using periods `pm` and `pm-daily`. Identical photo/author pairs appear once in each edition.

`notification_delivery.digest` reads all participants without a platform filter. `editorial_voice.story` caches one Kimi story for each date/period. Queue the same text/captions and complete photo set for every enabled subscriber and the adult Telegram group. The first picture carries the story, the remaining attachments identify their authors. Longer text is split at a sentence boundary without dropping the continuation.

`shared_media.py` persists incoming MAX image URLs in `shared_photo_assets`. Telegram identifiers cannot be used in MAX: download with Telegram getFile, upload through MAX POST /uploads?type=image, and cache the returned image token. MAX images sent to Telegram are downloaded and uploaded with multipart sendPhoto; cache the returned Telegram file_id. Never put a Telegram download URL containing the bot token into MAX messages. Downloads validate provider domains, redirects and size. Add MAX CA certificates with `load_verify_locations` to the default system trust store; supplying only `cafile` to `create_default_context` drops public roots and breaks i.oneme.ru downloads. For already received daily MAX pictures use `daily_photos.photo_url` as a recovery source. Existing MAX check-in pictures received before URL capture may require retrieving original messages; never pretend an incompatible identifier is an image.

`notification_photo_outbox` retains failed deliveries for retries. Mark delivered only after API success. A lock prevents competing in-process retries from sending the same pending photo concurrently. Detect MAX recipients through `messenger_identities`; a negative Telegram group ID is still Telegram.

## Daily chat games

`chat_games.install(globals())` follows `notification_delivery.install(globals())`. It wraps both Telegram/MAX callbacks and private text handlers. At 17:00 Moscow `run_slot('chat-game', chat_game_invite)` sends a durable invitation. `/game` opens the two topics without the mini app.

Kimi creates five new short situations per topic per day from the principles of lessons 02 (interview) and 03 (plans/composition) in `news/boom-kadr-deploy/lessons.js`. Each has three choices, one correct answer and a clear explanation. Structural validation and a Kimi editorial check precede publication. Static questions are an emergency backup.

`chat_game_content(day,topic,body,source)` stores immutable daily content; `source` is `kimi` or `backup`. Dates in game tables/callbacks use YYYYMMDD. A rollout preserves questions of games already started that day. Do not change cached questions during a participant's run.

`chat_game_runs(user_id,day,topic,step,score,missed,answers)` stores progress, chosen responses and specific skills to practice. Updates require the expected step, so repeated buttons do not increase the score. MAX callbacks are acknowledged by the MAX webhook before the game handler.

After completion, send the personal score and concrete feedback, then queue one public post containing the participant's five answers and result for all enabled subscribers and the connected adult chat. The outbox key contains participant/date/topic to prevent duplicate public posts. Warn participants in the invitation that their answers will be shared.

The evening story reads game participants alongside check-in facts. Kimi names players, thanks everyone, praises their effort and suggests a shared skill to practice; it must not claim everyone answered correctly when they did not. `editorial_voice.story` caches the full finished story once per date/period in `daily_content`.

## Teacher panel

`admin_menu` sends Telegram a persistent reply keyboard under the message field: `📣 Написать всем`, `👥 Подписчики`, `🎛 Управление`, `❓ Вопросы`. An inline panel is also provided. MAX uses the inline panel. Do not promise a persistent MAX keyboard.

Only configured `ADMIN_IDS` receive administrative access. Signed internal MAX IDs can be configured explicitly; never guess a teacher's MAX identity from their name. `/publish` or the reply-keyboard button enables the existing `admin_publish` flow; `/stop` cancels it. `/questions` and its button open unanswered questions.

## Verification and deployment

Run `test_editorial_chat.py` and the targeted server tests `daily_photo_collected`, `admin_menu_has`, `checkin_photos`, `evening_digest_retries`. The deployment workflow `timecode-kimi-games-admin-deploy.yml` backs up files, patches only intended functions, compiles modules, restarts the service and verifies local health and the public mini app. It reports administrator panel acknowledgements, invitation deliveries by platform and daily game content sources without exposing tokens or children's answers.

`timecode-kimi-next-game.yml` prepares the next day's game cache with the live Kimi connection without sending another invitation. Watch `source='backup'`: this is expected for games already started during the rollout, but for a new date inspect Kimi transport and validation if no fresh generated content is present.

Unified report deployment: `timecode-unified-reports-deploy.yml`. Live media verification: `timecode-media-bridge-verify.yml`; successful run 37005619708 downloaded a real MAX photo and uploaded a real Telegram photo to MAX without broadcasting test messages. The latter workflow also deployed the combined TLS trust fix.

## Prize weekend quest: 3–4 October 2026

`weekend_quest.py` installs after `chat_schedule`. It wraps chat text/callbacks and `class_reminders`, called by the existing scheduler every 20 seconds. This is a dated campaign, not an endlessly recurring competition. Friday announcement is an explicit deployment action. Task releases: Saturday 10:00/14:00/18:00, Sunday 10:00/13:00/16:00 Moscow. Accept until Sunday 17:30; draw and common result at 18:00. `/weekend` or the inline buttons opens the available tasks in Telegram/MAX, no mini app required.

Six tasks: one mystery photo + movie title; an open-question quiz with retries; three distinct photographs showing general/medium/close plans; two opposite-angle photos + written choice; two presenter sentences; a three-sentence ending. Typed creative replies are not judged competitively. Kimi comments privately after completion when configured; vision comments use actual photos. Partial photos/text persist across sessions. Other bot callbacks and slash commands suspend active quest input, preserving partial answers, so check-ins can be completed independently.

`weekend_players` stores active task; `weekend_answers` stores submitted content and completion; `weekend_posts` freezes each release's day/text to prevent duplicate Saturday messages on Sunday; `weekend_draws` atomically stores one random winner plus eligible user IDs and frozen result text. Only enabled non-admin participants with six distinct completed tasks enter. No winner is invented when nobody finishes. A participant is asked to use one messenger; separately registered accounts cannot be proven to represent the same human without identity linking.

Common result includes finalists, the one winner, selected quoted news, and the first-task photographs with authors and movie titles. The shared-media bridge sends the same gallery to Telegram/MAX via durable photo outbox. Photos from other steps stay in the quest submission records. Never redraw an existing stored outcome on restart or retry. Do not reset tables when updating code. The prize is one TIMECODE keyring, delivered personally by Dmitry Vitalyevich at a lesson.

Deployment: `news/boom-kadr-deploy/.github/workflows/timecode-weekend-quest-deploy.yml`; patch only the module import in live server, preserve other server-only edits. Run `tests/test_weekend_quest.py` plus editorial, schedule, MAX and shared-media regressions. Announce once through the durable outbox and report acknowledgements by platform without logging tokens or student submissions.

## Week of 5–10 October: conversation, privacy, prizes

`week_plan.py` installs last, after `weekend_quest`. Each weekday has ONE featured five-question game, available all day and reminded at 17:00. Monday f/news, Tuesday i/interview, Wednesday f/missing plans, Thursday f/simple shooting mistakes, Friday i/opening a video. Kimi receives the day's actual context when generating questions; don't alter questions already shown to a player.

Owner changed public results: never publish selected options, question-by-question answers, or mistakes. `chat_games.finish` now queues only name, score and a short acknowledgement. Detailed answers, explanations and advice stay personal. Editorial game facts exclude `missed` and answers. Wednesday's quest also publishes completion only; its photo, power and slogan stay private.

Weekly prize rule is explicit in the morning: five weekday games, 5/5 each (25/25 total), first answer counts, each game closes at local midnight; prior-day buttons cannot be used for the reward. ALL qualifying enabled non-admin participants receive a TIMECODE-logo keyring from Dmitry Vitalyevich at the Saturday 10 October lesson. This replaces the earlier assistant suggestion to avoid a prize that week. `week_rewards` freezes the eligible recipients at Saturday 09:00 and notifies teacher privately; don't reset game progress or award based on mere participation. Separate platform accounts are not automatically proven to be one person; participants are asked to play in one messenger.

Wednesday 7 October 10:00–20:00 is a clear, single-day quest «Продай мне эту ложку»: one object photo, one invented superpower, slogan up to ten words. All instructions and an example appear at launch. Three sequential personal steps, pause/resume, reminder at 16:00, public completion at finish and shared summary at 20:15. This quest does not replace Wednesday's quiz or determine the keyring reward. Kimi comments on the creative copy privately.

`editorial_voice.story` now allows 500–1400-character authorial stories and uses Kimi as a fact checker returning ok/reason rather than rewriting the writer into a fixed five-sentence template. One targeted rewrite only if facts fail, then recheck. The Moscow date/day stays explicit. Stories use real check-in facts, and game summaries only names/scores. Existing reports remain cached; new editions use the new instructions.

`chat_reply(question,uid)` receives the student's last ten dialogue turns; stores at most twelve turns per user and purges after 48 hours. It must never use another participant's dialogue or broadcast it. Replies can develop an idea, explain a next step and ask a natural follow-up instead of being cut to 650 characters. Keep structured AI data as data, never executable output.

Deploy through `timecode-week-plan-deploy.yml`: patch only chat_reply/call sites/module import in live server, copy game/editorial/week modules, preserve local server edits and all SQLite records. Tests include per-platform privacy, per-day deadlines, reward exclusion for wrong answers/admins, quest closure and dialogue isolation.
