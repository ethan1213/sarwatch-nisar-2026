"""Bounded, resumable HTTP download with official size and MD5 validation.

Credentials belong to the caller's authenticated session and are never stored here.
Partial files have stable names; publication is atomic only after checksum succeeds.
"""
import errno
import hashlib
import re
import time
from pathlib import Path


def download_verified(session, url, target, expected_size, expected_md5, *, progress=None, retries=12, retry_delay=5):
    target = Path(target)
    partial = target.with_suffix(target.suffix + '.part')
    target.parent.mkdir(parents=True, exist_ok=True)
    if expected_size <= 0 or not re.fullmatch(r'[0-9a-fA-F]{32}', expected_md5):
        raise ValueError('Tamaño o MD5 oficial inválido')
    if target.exists():
        if target.stat().st_size != expected_size:
            raise ValueError('El archivo final existente tiene tamaño incorrecto; no se modifica automáticamente')
        partial = target
    attempts = 0
    while not partial.exists() or partial.stat().st_size < expected_size:
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {'Accept-Encoding': 'identity'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
        try:
            with session.get(url, headers=headers, stream=True, timeout=(30, 60)) as response:
                if response.status_code in (401, 403, 404):
                    raise ValueError(f'El servidor rechazó la descarga (HTTP {response.status_code}); se conserva el parcial')
                response.raise_for_status()
                if response.status_code == 206:
                    content_range = response.headers.get('Content-Range', '')
                    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', content_range)
                    if not match or int(match[1]) != offset or int(match[3]) != expected_size:
                        raise ValueError('Content-Range incompatible con el archivo oficial; no se concatena')
                elif response.status_code == 200:
                    # A server ignoring Range must overwrite, never append an entire file to a partial.
                    offset = 0
                else:
                    raise ValueError('Respuesta HTTP no apta para datos binarios')
                with partial.open('ab' if offset else 'wb') as handle:
                    downloaded = offset
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        if downloaded + len(chunk) > expected_size:
                            raise ValueError('La respuesta excede el tamaño oficial')
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if progress:
                            progress(downloaded, expected_size)
                if downloaded < expected_size:
                    raise OSError('Respuesta truncada; se conserva el parcial')
        except OSError as exc:
            if exc.errno == errno.ENOSPC:
                raise
            attempts += 1
            if attempts > retries:
                raise RuntimeError('Conexión interrumpida repetidamente; el archivo parcial se conserva para reanudar') from exc
            if progress:
                progress(partial.stat().st_size if partial.exists() else 0, expected_size)
            time.sleep(retry_delay)
    if partial.stat().st_size != expected_size:
        raise ValueError('Tamaño final distinto al oficial')
    digest = hashlib.md5()
    with partial.open('rb') as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected_md5.lower():
        raise ValueError('Checksum oficial no coincide; se conserva el archivo para inspección, sin publicarlo')
    if partial != target:
        partial.replace(target)
    return target
