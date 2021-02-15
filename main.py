import io
import logging
import os
import traceback
import zipfile
from html import escape
from os import environ
from typing import NamedTuple, Callable

import polib
import srt
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from telegram.parsemode import ParseMode

NEW_LINE_TAG = "<nl>"

TELEGRAM_TOKEN = environ["TELEGRAM_TOKEN"]
ENV = environ.get("ENV", "development")

if ENV == "production":
    URL = environ["URL"]
    URL.rstrip("/")
    PORT = int(environ["PORT"])
    SECRET = environ["SECRET"]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def po_to_srt_converter(src_fp, dest_fp):
    po = polib.pofile(src_fp.read().decode("utf-8-sig"))

    subtitles = []
    for unit in po:
        translated_content = unit.msgstr or unit.msgid
        lines = translated_content.split(NEW_LINE_TAG)
        content = "\n".join(lines)

        index, timecodes = unit.comment.split("\n", maxsplit=1)
        start, end = timecodes.split(" --> ")
        start = srt.srt_timestamp_to_timedelta(start)
        end = srt.srt_timestamp_to_timedelta(end)

        cue = srt.Subtitle(index=index, start=start, end=end, content=content)
        subtitles.append(cue)
        dest_fp.write(cue.to_srt().encode("utf-8"))


def srt_to_po_converter(src_fp, dest_fp):
    subtitles = srt.parse(src_fp.read().decode("utf-8-sig"))

    for cue in subtitles:
        lines = cue.content.splitlines()

        msgid = NEW_LINE_TAG.join(lines)
        start = srt.timedelta_to_srt_timestamp(cue.start)
        end = srt.timedelta_to_srt_timestamp(cue.end)
        comment = f"{cue.index}\n{start} --> {end}"

        unit = polib.POEntry(msgid=msgid, comment=comment)
        dest_fp.write(f"{unit}\n".encode("utf-8"))


def zip_converter(src_fp, dest_fp):
    with zipfile.ZipFile(src_fp, compression=zipfile.ZIP_DEFLATED) as src_zip, zipfile.ZipFile(
        dest_fp, "w", compression=zipfile.ZIP_DEFLATED
    ) as dest_zip:
        for filename in src_zip.namelist():
            name, ext = os.path.splitext(filename)

            try:
                strategy = STRATEGIES[ext]
            except KeyError:
                logger.debug(
                    f'File "{filename}" inside the archive is not supported, '
                    f"it will not be present in the converted zip"
                )
                continue

            dest_filename = f"{name}{strategy.extension}"
            with src_zip.open(filename) as src_zfp, dest_zip.open(dest_filename, "w") as dest_zfp:
                strategy.converter(src_zfp, dest_zfp)


class Strategy(NamedTuple):
    extension: str
    converter: Callable[[io.BytesIO, io.BytesIO], None]


STRATEGIES = {
    ".srt": Strategy(extension=".po", converter=srt_to_po_converter),
    ".po": Strategy(extension=".srt", converter=po_to_srt_converter),
    ".zip": Strategy(extension=".converted.zip", converter=zip_converter),
}


def start_and_help_handler(update: Update, context):
    file_formats = ", ".join(STRATEGIES)
    message = (
        "Just send me a file, I will convert it and send back to you in seconds!\n"
        "To make your life easier, I can process all the files inside a zip-archive at once, "
        "no need to send them one by one.\n\n"
        f"<b>Supported file formats:</b> <pre>{file_formats}</pre>\n\n"
        "<b>Important notes:</b>\n"
        " - files inside a zip-archive which are not supported will be ignored\n"
        " - bot can only convert back PO files which were generated by the bot, as it relies on the special file content"
    )
    update.message.reply_text(message, parse_mode=ParseMode.HTML)


def catch_all_handler(update: Update, context):
    update.effective_message.reply_text("I didn't understand that! Check /help")


def document_handler(update: Update, context):
    document = update.message.document
    source_filename = document.file_name or document.file_unique_id
    name, ext = os.path.splitext(source_filename)

    try:
        strategy = STRATEGIES[ext]
    except KeyError:
        update.message.reply_text(
            f"🤖 <code>{escape(ext)}</code> file format is not supported.\n" "Check /help", parse_mode=ParseMode.HTML
        )
        return

    src_bio = io.BytesIO()
    dest_bio = io.BytesIO()

    document.get_file().download(out=src_bio)
    src_bio.seek(0)

    try:
        strategy.converter(src_bio, dest_bio)
    except Exception:
        update.message.reply_text(
            f"❌ Something went wrong while converting your file(s).\n"
            f"Not sure what file formats are supported? Check here: /help\n\n"
            f"<b>Error:</b>\n<pre>{escape(traceback.format_exc())}</pre>",
            parse_mode=ParseMode.HTML,
        )
    else:
        dest_bio.seek(0)
        update.message.reply_document(dest_bio, filename=f"{name}{strategy.extension}")


def main():
    updater = Updater(token=TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler(["start", "help"], start_and_help_handler))
    dispatcher.add_handler(MessageHandler(Filters.document, document_handler, run_async=True))
    dispatcher.add_handler(MessageHandler(Filters.all, callback=catch_all_handler))

    updater.bot.delete_webhook()
    if ENV == "production":
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=SECRET)
        updater.bot.set_webhook(f"{URL}/{SECRET}")
    else:
        updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()