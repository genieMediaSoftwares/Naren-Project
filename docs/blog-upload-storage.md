# Persistent blog uploads on Vercel

The production blog save failed with `OSError: [Errno 30] Read-only file system`
when Django tried to write a featured image under `/var/task/media/blog/`.

On Vercel (`VERCEL=1`), the default media storage now saves uploaded bytes in
the existing PostgreSQL database's `website_mediaasset` table. File names and
`/media/` URLs keep their existing format. Bundled images remain readable from
`MEDIA_ROOT`, and their names are reserved so new uploads cannot replace them.
Local development continues to use filesystem storage. An explicit
`DJANGO_MEDIA_STORAGE_BACKEND` setting takes precedence over the default.

This is intended for this site's modest image upload volume. Database usage
grows by the size of uploaded images. Object storage can be configured later
if upload volume grows; it requires migrating the stored files as well as
changing the backend.

## Release

1. Run `python manage.py test website --settings=naren_ultrasound.test_settings`.
   This uses an isolated SQLite database, never the production database.
2. Inspect `python manage.py migrate --plan`. Apply the additive
   `0015_mediaasset` migration before deploying the application. This creates
   a new table without modifying existing posts or their image references.
3. Deploy the code through the existing Vercel project.
4. Verify the homepage, existing blog pages and bundled images. Then save an
   unpublished test post with an image, confirm that image loads in a separate
   request, and check runtime logs for errors. Do not publish a test article.

The storage tests cover featured uploads, downloaded images, inline and bulk
photos, CKEditor uploads, legacy image reads, duplicate names, missing and
escaping paths, and transaction rollback after a failed admin save.

## Rollback

Rolling the code back does not delete the media table or its uploads. However,
the previous application cannot serve database-backed images and cannot upload
on Vercel. Retain the table and use a forward fix for storage-related failures.
Do not reverse `0015_mediaasset` after uploads have been saved: reversing it
would delete those bytes.
