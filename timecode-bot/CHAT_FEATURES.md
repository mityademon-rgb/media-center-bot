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
