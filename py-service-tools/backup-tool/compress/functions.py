# Copiado de compressing_files/functions.py
import os
import tarfile
import zipfile
import lzma
from typing import Iterable, Optional, List
import shutil
import subprocess
import sys

SUPPORTED_FORMATS = ("xz", "zip", "gz")


def _matches_filters(filename: str, include_ext: Optional[Iterable[str]] = None, exclude_ext: Optional[Iterable[str]] = None) -> bool:
    if include_ext:
        return any(filename.lower().endswith(e.lower()) for e in include_ext)
    if exclude_ext:
        return not any(filename.lower().endswith(e.lower()) for e in exclude_ext)
    return True


def create_archive(source_path: str,
                   dest_path: Optional[str] = None,
                   fmt: str = "xz",
                   compress_level: int = 9,
                   include_ext: Optional[List[str]] = None,
                   exclude_ext: Optional[List[str]] = None) -> str:
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {fmt}. Supported: {SUPPORTED_FORMATS}")

    source_path = os.path.abspath(source_path)
    if dest_path is None:
        base = os.path.basename(source_path.rstrip(os.sep)) or "archive"
        dest_path = os.path.join(os.getcwd(), f"{base}.{ 'tar.xz' if fmt == 'xz' else 'zip' if fmt == 'zip' else 'tar.gz'}")
    dest_path = os.path.abspath(dest_path)

    if fmt == 'xz' or fmt == 'gz':
        if fmt == 'xz':
            preset = max(0, min(9, int(compress_level)))
            with lzma.open(dest_path, 'wb', preset=preset) as comp:
                with tarfile.open(fileobj=comp, mode='w') as tar:
                    if os.path.isdir(source_path):
                        for root, _, files in os.walk(source_path):
                            for name in files:
                                if _matches_filters(name, include_ext, exclude_ext):
                                    full = os.path.join(root, name)
                                    arcname = os.path.relpath(full, os.path.dirname(source_path))
                                    tar.add(full, arcname=arcname)
                    else:
                        tar.add(source_path, arcname=os.path.basename(source_path))
        else:
            try:
                with tarfile.open(dest_path, mode='w:gz', compresslevel=int(compress_level)) as tar:
                    if os.path.isdir(source_path):
                        for root, _, files in os.walk(source_path):
                            for name in files:
                                if _matches_filters(name, include_ext, exclude_ext):
                                    full = os.path.join(root, name)
                                    arcname = os.path.relpath(full, os.path.dirname(source_path))
                                    tar.add(full, arcname=arcname)
                    else:
                        tar.add(source_path, arcname=os.path.basename(source_path))
            except TypeError:
                with tarfile.open(dest_path, mode='w:gz') as tar:
                    if os.path.isdir(source_path):
                        for root, _, files in os.walk(source_path):
                            for name in files:
                                if _matches_filters(name, include_ext, exclude_ext):
                                    full = os.path.join(root, name)
                                    arcname = os.path.relpath(full, os.path.dirname(source_path))
                                    tar.add(full, arcname=arcname)
                    else:
                        tar.add(source_path, arcname=os.path.basename(source_path))

    elif fmt == 'zip':
        compression = zipfile.ZIP_LZMA if hasattr(zipfile, 'ZIP_LZMA') else zipfile.ZIP_DEFLATED
        zlevel = None
        try:
            zlevel = int(compress_level)
        except Exception:
            zlevel = None

        if zlevel is not None:
            try:
                zf = zipfile.ZipFile(dest_path, 'w', compression=compression, compresslevel=zlevel)
            except TypeError:
                zf = zipfile.ZipFile(dest_path, 'w', compression=compression)
        else:
            zf = zipfile.ZipFile(dest_path, 'w', compression=compression)

        with zf:
            if os.path.isdir(source_path):
                for root, _, files in os.walk(source_path):
                    for name in files:
                        if _matches_filters(name, include_ext, exclude_ext):
                            full = os.path.join(root, name)
                            arcname = os.path.relpath(full, os.path.dirname(source_path))
                            zf.write(full, arcname)
            else:
                zf.write(source_path, os.path.basename(source_path))

    return dest_path


def _is_executable_available(name: str) -> bool:
    return shutil.which(name) is not None


def create_archive_parallel(source_path: str,
                            dest_path: Optional[str] = None,
                            fmt: str = "xz",
                            compress_level: int = 9,
                            include_ext: Optional[List[str]] = None,
                            exclude_ext: Optional[List[str]] = None) -> str:
    source_path = os.path.abspath(source_path)
    if dest_path is None:
        base = os.path.basename(source_path.rstrip(os.sep)) or "archive"
        dest_path = os.path.join(os.getcwd(), f"{base}.tar.xz")
    dest_path = os.path.abspath(dest_path)

    if fmt != 'xz':
        return create_archive(source_path, dest_path=dest_path, fmt=fmt, compress_level=compress_level, include_ext=include_ext, exclude_ext=exclude_ext)

    if not (_is_executable_available('tar') and _is_executable_available('xz')):
        return create_archive(source_path, dest_path=dest_path, fmt=fmt, compress_level=compress_level, include_ext=include_ext, exclude_ext=exclude_ext)

    src = source_path
    if os.path.isdir(src):
        cwd = os.path.dirname(src)
        target = os.path.basename(src)
        tar_cmd = ['tar', 'cf', '-', '-C', cwd, target]
    else:
        cwd = None
        tar_cmd = ['tar', 'cf', '-', os.path.basename(src)]

    xz_cmd = ['xz', f'-T0', f'-{max(0,min(9,int(compress_level)))}', '-c']

    try:
        with open(dest_path, 'wb') as out_f:
            tar_proc = subprocess.Popen(tar_cmd, cwd=cwd, stdout=subprocess.PIPE)
            xz_proc = subprocess.Popen(xz_cmd, stdin=tar_proc.stdout, stdout=out_f)
            if tar_proc.stdout is not None:
                tar_proc.stdout.close()
            xz_ret = xz_proc.wait()
            tar_ret = tar_proc.wait()
            if xz_ret != 0 or tar_ret != 0:
                raise RuntimeError(f"tar/xz failed (tar={tar_ret}, xz={xz_ret})")
    except Exception as e:
        return create_archive(source_path, dest_path=dest_path, fmt=fmt, compress_level=compress_level, include_ext=include_ext, exclude_ext=exclude_ext)

    return dest_path


def extract_archive(archive_path: str, dest_dir: Optional[str] = None) -> str:
    archive_path = os.path.abspath(archive_path)
    if dest_dir is None:
        dest_dir = os.path.splitext(archive_path)[0] + '_extracted'
    dest_dir = os.path.abspath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)

    try:
        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, 'r:*') as tar:
                tar.extractall(dest_dir)
            return dest_dir
    except Exception:
        pass

    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(dest_dir)
            return dest_dir
    except Exception:
        pass

    raise ValueError('Unsupported or corrupted archive format')


if __name__ == '__main__':
    print('Module with archive helpers. Import and use create_archive/extract_archive/list_archive.')


def compress_file(file_path: str, out_path: Optional[str] = None, fmt: str = 'xz', compress_level: int = 9) -> str:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)

    if fmt == 'xz':
        if out_path is None:
            out_path = file_path + '.xz'
        else:
            if out_path.lower().endswith('.tar.xz'):
                return create_archive(file_path, dest_path=out_path, fmt='xz', compress_level=compress_level)

        out_path = os.path.abspath(out_path)
        preset = max(0, min(9, int(compress_level)))
        with open(file_path, 'rb') as inf, lzma.open(out_path, 'wb', preset=preset) as outf:
            shutil.copyfileobj(inf, outf)
        return out_path

    return create_archive(file_path, dest_path=out_path, fmt=fmt, compress_level=compress_level)


def decompress_file(archive_path: str, dest_dir: Optional[str] = None) -> str:
    archive_path = os.path.abspath(archive_path)
    if dest_dir is None:
        dest_dir = os.path.splitext(archive_path)[0] + '_decompressed'
    dest_dir = os.path.abspath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)

    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, 'r:*') as tar:
            tar.extractall(dest_dir)
        return dest_dir

    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(dest_dir)
        return dest_dir

    lower = archive_path.lower()
    if lower.endswith('.xz'):
        out_name = os.path.splitext(os.path.basename(archive_path))[0]
        out_path = os.path.join(dest_dir, out_name)
        try:
            with lzma.open(archive_path, 'rb') as inf, open(out_path, 'wb') as outf:
                shutil.copyfileobj(inf, outf)
            return out_path
        except Exception as e:
            raise RuntimeError(f'Failed to decompress raw .xz: {e}')

    if lower.endswith('.gz'):
        import gzip
        out_name = os.path.splitext(os.path.basename(archive_path))[0]
        out_path = os.path.join(dest_dir, out_name)
        try:
            with gzip.open(archive_path, 'rb') as inf, open(out_path, 'wb') as outf:
                shutil.copyfileobj(inf, outf)
            return out_path
        except Exception as e:
            raise RuntimeError(f'Failed to decompress raw .gz: {e}')

    raise ValueError('Unsupported or unknown compressed format')
