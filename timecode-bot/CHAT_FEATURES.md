# TIMECODE: chat posts and daily games (1 October 2026)

The production source is `mityademon-rgb/media-center-bot`, branch `feature/timecode-media-bot`. Deploy targeted blocks through the workflows in `mityademon-rgb/news`, branch `boom-kadr-deploy`; keep production-only edits intact. Never replace the whole live checkout.

## Photos

At 16:00 Moscow the bot requests one photo and promises an immediate post in the bot chats of subscribers to the same messenger, including the teacher. `notification_delivery.install()` must delegate `instant_photo` to the original server handler: an old override incorrectly promised an evening collection.

`publish_daily_photo` critiques the actual picture when possible and passes its comment to `editorial_voice.photo_caption`. When vision fails, publish the actual attachment with the author's name and a natural invitation to look at the picture. Do not publish a technical failure message or invent photographic details.

`notification_photo_outbox` records a separate destination for every delivery. Only a successful API response marks it delivered. Daily-photo state `queued` becomes `done` when all corresponding destinations have been delivered. Telegram and MAX photo identifiers stay within their own messenger. Text posts go to both.

Check-in photos belong to morning/evening digests. The first compatible photo carries the story and identifies its author; remaining pictures carry author labels. Send the story photo before other images. Split a long story at a sentence boundary and deliver its continuation as text, preserving the full story. Subscribers without compatible photos receive the text digest.

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

Run `test_editorial_chat.py` and the targeted server tests `daily_photo_unreadable`, `admin_menu_has`, `checkin_photos`, `evening_digest_retries`. The deployment workflow `timecode-kimi-games-admin-deploy.yml` backs up files, patches only intended functions, compiles modules, restarts the service and verifies local health and the public mini app. It reports administrator panel acknowledgements, invitation deliveries by platform and daily game content sources without exposing tokens or children's answers.

`timecode-kimi-next-game.yml` prepares the next day's game cache with the live Kimi connection without sending another invitation. Watch `source='backup'`: this is expected for games already started during the rollout, but for a new date inspect Kimi transport and validation if no fresh generated content is present.
