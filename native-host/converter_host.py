#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Conversor de Arquivos - programa local (Native Messaging)
#
# Fluxo:
#   pick-file    -> abre o seletor, identifica o tipo, guarda um token
#   convert-file -> pergunta a pasta de destino e converte
#
# Motores usados:
#   FFmpeg       -> audio e video
#   ImageMagick  -> imagens
#   Tesseract    -> OCR (imagem para texto)
#   Poppler      -> PDF para texto, HTML e imagem
#   LibreOffice  -> documentos, planilhas, apresentacoes e PDF editavel

import html
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------- Configuracoes ----------

HOME = Path.home().resolve()
TOKENS = HOME / "MediaConverter" / "selections"
MAX_MESSAGE = 64 * 1024
TOKEN_TTL = 60 * 60            # a selecao vale por 1 hora
DIALOG_TIMEOUT = 10 * 60
CONVERT_TIMEOUT = 2 * 60 * 60

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")
PDFTOTEXT = shutil.which("pdftotext")
PDFTOPPM = shutil.which("pdftoppm")
PDFTOHTML = shutil.which("pdftohtml")
MAGICK = shutil.which("magick") or shutil.which("convert")
TESSERACT = shutil.which("tesseract")
ZENITY = shutil.which("zenity")

# ---------- Categorias: extensoes de entrada e formatos de saida ----------

CATEGORIES = {
    "pdf": (
        {"pdf"},
        ["txt", "html", "docx", "odt", "png", "jpg", "tiff"],
    ),
    "image": (
        {"jpg", "jpeg", "png", "webp", "bmp", "gif", "tif", "tiff",
         "heic", "heif", "avif", "jp2", "ico", "tga", "psd"},
        ["jpg", "png", "webp", "bmp", "tiff", "gif", "avif", "ico", "pdf", "ocr_txt"],
    ),
    "text": (
        {"txt", "md", "log"},
        ["pdf", "docx", "odt", "rtf", "html", "txt"],
    ),
    "document": (
        {"doc", "docx", "odt", "rtf", "wps", "html", "htm", "epub"},
        ["pdf", "docx", "doc", "odt", "rtf", "txt", "html", "epub"],
    ),
    "spreadsheet": (
        {"xls", "xlsx", "ods", "csv", "tsv"},
        ["pdf", "xlsx", "xls", "ods", "csv", "html"],
    ),
    "presentation": (
        {"ppt", "pptx", "odp"},
        ["pdf", "pptx", "ppt", "odp", "png"],
    ),
}

MEDIA_OUTPUTS = {
    "audio": ["mp3", "m4a", "aac", "ogg", "opus", "wav", "flac", "ac3", "aiff", "wma"],
    "video": ["mp4", "mkv", "webm", "mov", "avi", "mpeg", "wmv", "flv", "gif_video",
              "mp3", "m4a", "aac", "ogg", "opus", "wav", "flac"],
}

LABELS = {
    "audio": "Audio", "video": "Video", "pdf": "PDF", "image": "Imagem",
    "text": "Texto", "document": "Documento", "spreadsheet": "Planilha",
    "presentation": "Apresentacao",
}

# Extensao final do arquivo para formatos com nome interno diferente.
FINAL_EXTENSION = {"gif_video": "gif", "ocr_txt": "txt"}

# Filtros do LibreOffice para cada formato de saida.
OFFICE_FILTERS = {
    "pdf": "pdf",
    "docx": "docx:MS Word 2007 XML",
    "doc": "doc:MS Word 97",
    "odt": "odt",
    "rtf": "rtf",
    "txt": "txt:Text (encoded):UTF8",
    "html": "html",
    "epub": "epub",
    "xlsx": "xlsx:Calc MS Excel 2007 XML",
    "xls": "xls:MS Excel 97",
    "ods": "ods",
    "csv": "csv:Text - txt - csv (StarCalc):44,34,76,1",
    "pptx": "pptx:Impress MS PowerPoint 2007 XML",
    "ppt": "ppt:MS PowerPoint 97",
    "odp": "odp",
    "png": "png",
}

# ---------- Respostas ----------

def ok(**values):
    return {"success": True, **values}


def fail(message):
    return {"success": False, "error": str(message)}


def cancelled():
    return {"success": False, "cancelled": True}

# ---------- Protocolo do Native Messaging ----------

def read_message():
    header = sys.stdin.buffer.read(4)
    if len(header) < 4:
        return None
    length = struct.unpack("@I", header)[0]
    if length <= 0 or length > MAX_MESSAGE:
        raise ValueError("Mensagem invalida")
    data = sys.stdin.buffer.read(length)
    if len(data) != length:
        raise ValueError("Mensagem incompleta")
    return json.loads(data.decode("utf-8"))


def send_message(message):
    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("@I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()

# ---------- Janelas do sistema ----------

def run_dialog(args):
    try:
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=DIALOG_TIMEOUT, check=False)
        return result.returncode, result.stdout.decode("utf-8", errors="replace").strip()
    except (OSError, subprocess.TimeoutExpired):
        return None, ""


def choose_file():
    if not ZENITY:
        return None, fail("Zenity nao encontrado. Instale com: sudo apt install zenity")
    code, raw = run_dialog([
        ZENITY, "--file-selection", "--title=Escolha um arquivo para converter",
        f"--filename={HOME}/", "--file-filter=Todos os arquivos | *",
    ])
    if code is None:
        return None, fail("Nao foi possivel abrir o seletor de arquivos.")
    if code != 0:
        return None, cancelled()
    try:
        path = Path(raw).resolve(strict=True)
    except (OSError, RuntimeError):
        return None, fail("Arquivo invalido.")
    if not path.is_file():
        return None, fail("Escolha um arquivo comum.")
    return path, None


def default_output_dir():
    try:
        result = subprocess.run(["xdg-user-dir", "DOWNLOAD"], capture_output=True,
                                text=True, timeout=5, check=False)
        candidate = result.stdout.strip()
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    except Exception:
        pass
    return HOME / "Downloads"


def choose_output_dir():
    if not ZENITY:
        return None, fail("Zenity nao encontrado.")
    code, raw = run_dialog([
        ZENITY, "--file-selection", "--directory", "--title=Escolha onde salvar",
        f"--filename={default_output_dir()}/",
    ])
    if code is None:
        return None, fail("Nao foi possivel abrir o seletor de pasta.")
    if code != 0:
        return None, cancelled()
    try:
        folder = Path(raw).resolve(strict=True)
    except (OSError, RuntimeError):
        return None, fail("Pasta invalida.")
    if not folder.is_dir() or not os.access(folder, os.W_OK | os.X_OK):
        return None, fail("Sem permissao para salvar nessa pasta.")
    return folder, None

# ---------- Identificacao do arquivo ----------

def detect_media(path):
    if not FFPROBE:
        return None
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "json", str(path)],
            capture_output=True, timeout=30, check=False,
        )
        data = json.loads(result.stdout or b"{}")
        types = {item.get("codec_type") for item in data.get("streams", [])}
        if "video" in types:
            return "video"
        if "audio" in types:
            return "audio"
    except Exception:
        return None
    return None


def inspect_file(path):
    ext = path.suffix.lower().lstrip(".")
    for category, (extensions, outputs) in CATEGORIES.items():
        if ext in extensions:
            if category == "image" and not TESSERACT:
                outputs = [item for item in outputs if item != "ocr_txt"]
            return category, list(outputs)
    media = detect_media(path)
    if media:
        return media, list(MEDIA_OUTPUTS[media])
    return None, []

# ---------- Tokens temporarios ----------

def cleanup_tokens():
    TOKENS.mkdir(parents=True, exist_ok=True, mode=0o700)
    now = time.time()
    for file in TOKENS.glob("*.json"):
        try:
            if file.is_symlink() or now - file.stat().st_mtime > TOKEN_TTL:
                file.unlink(missing_ok=True)
        except OSError:
            pass


def save_token(path):
    cleanup_tokens()
    token = secrets.token_hex(16)
    file = TOKENS / f"{token}.json"
    file.write_text(json.dumps({"path": str(path)}), encoding="utf-8")
    file.chmod(0o600)
    return token


def load_token(token, consume=False):
    cleanup_tokens()
    if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{32}", token):
        return None
    file = TOKENS / f"{token}.json"
    try:
        path = Path(json.loads(file.read_text(encoding="utf-8"))["path"]).resolve(strict=True)
    except Exception:
        return None
    if not path.is_file():
        return None
    if consume:
        file.unlink(missing_ok=True)
    return path

# ---------- Nome do arquivo de saida (nunca sobrescreve) ----------

def output_path(source, ext, folder):
    stem = re.sub(r"[^\w\s().-]", "_", source.stem).strip(" .")[:100] or "arquivo"
    output = folder / f"{stem}.{ext}"
    number = 1
    while output.exists() or output.is_symlink():
        output = folder / f"{stem} ({number}).{ext}"
        number += 1
    return output

# ---------- Execucao de comandos ----------

def run_command(command, output):
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=CONVERT_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        output.unlink(missing_ok=True)
        return fail("Tempo limite da conversao excedido.")
    except OSError as error:
        return fail(f"Nao foi possivel executar o conversor: {error}")
    if result.returncode != 0 or not output.exists():
        output.unlink(missing_ok=True)
        details = result.stderr.decode("utf-8", errors="replace").strip()[-350:]
        return fail(details or "Falha na conversao.")
    return ok(output=output.name)


def move_result(candidate, output):
    if not candidate or not candidate.exists():
        return fail("O arquivo convertido nao foi gerado.")
    shutil.move(str(candidate), str(output))
    return ok(output=output.name)

# ---------- Audio e video (FFmpeg) ----------

def media_arguments(fmt, quality):
    bitrate = {"baixa": "128k", "media": "192k", "alta": "320k"}[quality]
    crf = {"baixa": "28", "media": "23", "alta": "18"}[quality]
    vp9_crf = {"baixa": "40", "media": "32", "alta": "24"}[quality]
    mpeg_q = {"baixa": "8", "media": "5", "alta": "2"}[quality]
    gif_width = {"baixa": "320", "media": "480", "alta": "720"}[quality]

    audio = {
        "mp3": ["-vn", "-c:a", "libmp3lame", "-b:a", bitrate],
        "m4a": ["-vn", "-c:a", "aac", "-b:a", bitrate],
        "aac": ["-vn", "-c:a", "aac", "-b:a", bitrate, "-f", "adts"],
        "ogg": ["-vn", "-c:a", "libvorbis", "-b:a", bitrate],
        "opus": ["-vn", "-c:a", "libopus", "-b:a", bitrate],
        "wav": ["-vn", "-c:a", "pcm_s16le"],
        "flac": ["-vn", "-c:a", "flac"],
        "ac3": ["-vn", "-c:a", "ac3", "-b:a", bitrate],
        "aiff": ["-vn", "-c:a", "pcm_s16be"],
        "wma": ["-vn", "-c:a", "wmav2", "-b:a", bitrate],
    }
    video = {
        "mp4": ["-c:v", "libx264", "-crf", crf, "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", bitrate, "-movflags", "+faststart"],
        "mkv": ["-c:v", "libx264", "-crf", crf, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", bitrate],
        "mov": ["-c:v", "libx264", "-crf", crf, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", bitrate],
        "webm": ["-c:v", "libvpx-vp9", "-crf", vp9_crf, "-b:v", "0", "-c:a", "libopus", "-b:a", bitrate],
        "avi": ["-c:v", "mpeg4", "-q:v", mpeg_q, "-c:a", "libmp3lame", "-b:a", bitrate],
        "mpeg": ["-c:v", "mpeg2video", "-q:v", mpeg_q, "-c:a", "mp2", "-b:a", bitrate],
        "wmv": ["-c:v", "wmv2", "-q:v", mpeg_q, "-c:a", "wmav2", "-b:a", bitrate],
        "flv": ["-c:v", "flv1", "-q:v", mpeg_q, "-c:a", "libmp3lame", "-b:a", bitrate, "-ar", "44100"],
        "gif_video": ["-an", "-vf",
                      f"fps=10,scale={gif_width}:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
                      "-loop", "0"],
    }
    return audio.get(fmt) or video.get(fmt)


def convert_media(source, fmt, quality, output):
    if not FFMPEG:
        return fail("FFmpeg nao encontrado.")
    args = media_arguments(fmt, quality)
    if not args:
        return fail("Formato de midia invalido.")
    command = [FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-n",
               "-i", str(source), "-sn", "-dn", *args, str(output)]
    return run_command(command, output)

# ---------- Imagens (ImageMagick e Tesseract) ----------

def convert_image(source, fmt, quality, output, folder):
    if fmt == "ocr_txt":
        return ocr_image(source, output)
    if fmt == "pdf":
        return convert_office(source, "pdf", output)
    if not MAGICK:
        return fail("ImageMagick nao encontrado.")

    # Para formatos de uma imagem so, usamos apenas o primeiro quadro.
    first_frame = fmt != "gif"
    source_arg = f"{source}[0]" if first_frame else str(source)
    command = [MAGICK, source_arg, "-auto-orient"]

    if fmt in {"jpg", "webp", "avif"}:
        command += ["-quality", {"baixa": "60", "media": "82", "alta": "95"}[quality]]
    if fmt == "jpg":
        command += ["-background", "white", "-flatten"]
    if fmt == "ico":
        command += ["-resize", "256x256>"]

    command.append(str(output))
    return run_command(command, output)


def tesseract_languages():
    try:
        result = subprocess.run([TESSERACT, "--list-langs"], capture_output=True,
                                text=True, timeout=15, check=False)
        langs = set(result.stdout.split())
    except Exception:
        langs = set()
    chosen = [lang for lang in ("por", "eng") if lang in langs]
    return "+".join(chosen) or "eng"


def ocr_image(source, output):
    if not TESSERACT:
        return fail("Tesseract nao encontrado.")
    temp = Path(tempfile.mkdtemp(prefix="ocr-"))
    try:
        base = temp / "texto"
        command = [TESSERACT, str(source), str(base), "-l", tesseract_languages()]
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=CONVERT_TIMEOUT, check=False)
        if result.returncode != 0:
            return fail("O OCR nao conseguiu ler a imagem.")
        return move_result(base.with_suffix(".txt"), output)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

# ---------- PDF (Poppler e LibreOffice) ----------

def convert_pdf(source, fmt, output):
    if fmt == "txt":
        if not PDFTOTEXT:
            return fail("pdftotext nao encontrado.")
        return run_command([PDFTOTEXT, "-layout", "-enc", "UTF-8", str(source), str(output)], output)

    if fmt == "html":
        if not PDFTOHTML:
            return fail("pdftohtml nao encontrado.")
        temp = Path(tempfile.mkdtemp(prefix="pdf-html-"))
        try:
            base = temp / "documento"
            subprocess.run([PDFTOHTML, "-s", "-noframes", "-q", "-i", str(source), str(base)],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=CONVERT_TIMEOUT, check=False)
            return move_result(next(temp.glob("*.html"), None), output)
        finally:
            shutil.rmtree(temp, ignore_errors=True)

    if fmt in {"png", "jpg", "tiff"}:
        if not PDFTOPPM:
            return fail("pdftoppm nao encontrado.")
        temp = Path(tempfile.mkdtemp(prefix="pdf-img-"))
        try:
            prefix = temp / "pagina"
            option = {"png": "-png", "jpg": "-jpeg", "tiff": "-tiff"}[fmt]
            subprocess.run([PDFTOPPM, "-f", "1", "-l", "1", "-singlefile", "-r", "150",
                            option, str(source), str(prefix)],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=CONVERT_TIMEOUT, check=False)
            return move_result(next(temp.glob("pagina.*"), None), output)
        finally:
            shutil.rmtree(temp, ignore_errors=True)

    if fmt in {"docx", "odt"}:
        return convert_office(source, fmt, output, pdf_import=True)

    return fail("Conversao de PDF nao suportada.")

# ---------- Documentos, planilhas e apresentacoes (LibreOffice) ----------

def convert_office(source, fmt, output, pdf_import=False):
    if not SOFFICE:
        return fail("LibreOffice nao encontrado.")
    target = OFFICE_FILTERS.get(fmt)
    if not target:
        return fail("Formato de documento invalido.")

    temp = Path(tempfile.mkdtemp(prefix="office-"))
    profile = Path(tempfile.mkdtemp(prefix="office-profile-"))
    try:
        # Perfil separado: funciona mesmo com o LibreOffice aberto.
        command = [SOFFICE, f"-env:UserInstallation={profile.as_uri()}",
                   "--headless", "--norestore"]
        if pdf_import:
            command.append("--infilter=writer_pdf_import")
        command += ["--convert-to", target, "--outdir", str(temp), str(source)]

        subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                       timeout=CONVERT_TIMEOUT, check=False)
        extension = target.split(":")[0]
        return move_result(next(temp.glob(f"*.{extension}"), None), output)
    except subprocess.TimeoutExpired:
        return fail("A conversao do documento excedeu o tempo limite.")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
        shutil.rmtree(profile, ignore_errors=True)

# ---------- Texto simples ----------

def convert_text(source, fmt, output):
    if fmt == "txt":
        shutil.copy2(source, output)
        return ok(output=output.name)
    if fmt == "html":
        text = source.read_text(encoding="utf-8", errors="replace")
        output.write_text(
            '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'
            + html.escape(source.stem)
            + "</title></head><body><pre>"
            + html.escape(text)
            + "</pre></body></html>",
            encoding="utf-8",
        )
        return ok(output=output.name)
    return convert_office(source, fmt, output)

# ---------- Acoes ----------

def pick_file():
    source, problem = choose_file()
    if problem:
        return problem
    category, outputs = inspect_file(source)
    if not category:
        return fail("O tipo deste arquivo nao foi reconhecido.")
    return ok(
        selection=save_token(source),
        name=source.name,
        extension=source.suffix.lower().lstrip("."),
        label=LABELS.get(category, "Arquivo"),
        outputs=outputs,
        size=source.stat().st_size,
    )


def convert_file(message):
    token = message.get("selection")
    fmt = message.get("format")
    quality = message.get("quality", "media")
    if quality not in {"baixa", "media", "alta"}:
        quality = "media"

    source = load_token(token)
    if source is None:
        return fail("Selecao invalida ou expirada. Escolha o arquivo novamente.")

    category, outputs = inspect_file(source)
    if not category or fmt not in outputs:
        return fail("Formato incompativel com o arquivo selecionado.")

    folder, problem = choose_output_dir()
    if problem:
        return problem

    output = output_path(source, FINAL_EXTENSION.get(fmt, fmt), folder)

    if category in {"audio", "video"}:
        result = convert_media(source, fmt, quality, output)
    elif category == "image":
        result = convert_image(source, fmt, quality, output, folder)
    elif category == "pdf":
        result = convert_pdf(source, fmt, output)
    elif category == "text":
        result = convert_text(source, fmt, output)
    else:
        result = convert_office(source, fmt, output)

    if result.get("success"):
        load_token(token, consume=True)
    return result


def handle(message):
    if not isinstance(message, dict):
        return fail("Pedido invalido.")
    action = message.get("action")
    keys = set(message.keys())
    if action == "pick-file" and keys == {"action"}:
        return pick_file()
    if action == "convert-file" and keys == {"action", "selection", "format", "quality"}:
        return convert_file(message)
    return fail("Pedido invalido.")


def main():
    try:
        message = read_message()
        if message is None:
            return
        response = handle(message)
    except Exception as error:
        response = fail(f"Erro interno no conversor: {error}")
    send_message(response)


if __name__ == "__main__":
    main()
