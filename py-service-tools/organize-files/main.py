#!/usr/bin/env python3
"""Organize Files

Script para organizar arquivos de uma pasta por extensão ou por data de modificação.
Funções importáveis para testes: organize_by_extension, organize_by_mtime
"""
import os
import shutil
from datetime import datetime
import argparse
from typing import Iterable, Optional


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def organize_by_extension(source: str, dest_base: str, move: bool = True, dry_run: bool = False, include_ext: Optional[Iterable[str]] = None):
    """Organiza arquivos do `source` para `dest_base/<ext>/...`.

    - include_ext: se fornecido, lista de extensões (ex: ['.jpg','.png']) para incluir; caso contrário, todas.
    - move: se True, move os arquivos; caso contrário copia.
    - dry_run: se True, apenas loga as ações.
    """
    source = os.path.abspath(source)
    dest_base = os.path.abspath(dest_base)

    if not os.path.isdir(source):
        raise FileNotFoundError(source)

    for root, _, files in os.walk(source):
        for fname in files:
            fpath = os.path.join(root, fname)
            _, ext = os.path.splitext(fname)
            ext = ext.lower() or '.noext'
            if include_ext and ext not in [e.lower() for e in include_ext]:
                continue
            dest_dir = os.path.join(dest_base, ext.lstrip('.'))
            _ensure_dir(dest_dir)
            dest_path = os.path.join(dest_dir, fname)
            if dry_run:
                print(f"[dry-run] {'move' if move else 'copy'} {fpath} -> {dest_path}")
            else:
                if move:
                    shutil.move(fpath, dest_path)
                else:
                    shutil.copy2(fpath, dest_path)
    return True


def organize_by_mtime(source: str, dest_base: str, move: bool = True, dry_run: bool = False, by: str = 'month'):
    """Organiza arquivos do `source` por data de modificação.

    - by: 'month' -> YYYY-MM, 'day' -> YYYY-MM-DD
    """
    source = os.path.abspath(source)
    dest_base = os.path.abspath(dest_base)

    if not os.path.isdir(source):
        raise FileNotFoundError(source)

    for root, _, files in os.walk(source):
        for fname in files:
            fpath = os.path.join(root, fname)
            mtime = os.path.getmtime(fpath)
            dt = datetime.fromtimestamp(mtime)
            if by == 'day':
                key = dt.strftime('%Y-%m-%d')
            else:
                key = dt.strftime('%Y-%m')
            dest_dir = os.path.join(dest_base, key)
            _ensure_dir(dest_dir)
            dest_path = os.path.join(dest_dir, fname)
            if dry_run:
                print(f"[dry-run] {'move' if move else 'copy'} {fpath} -> {dest_path}")
            else:
                if move:
                    shutil.move(fpath, dest_path)
                else:
                    shutil.copy2(fpath, dest_path)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description='Organize files by extension or modification date')
    parser.add_argument('--source', '-s', required=True, help='source directory')
    parser.add_argument('--dest', '-d', required=True, help='destination base directory')
    parser.add_argument('--mode', '-m', choices=['extension', 'mtime'], default='extension', help='organize mode')
    parser.add_argument('--by', choices=['month', 'day'], default='month', help='for mtime mode: group by month or day')
    parser.add_argument('--ext', help='comma separated list of extensions to include (ex: .jpg,.png)')
    parser.add_argument('--copy', action='store_true', help='copy files instead of moving')
    parser.add_argument('--dry-run', action='store_true', help='simulate actions')

    args = parser.parse_args(argv)

    include_ext = args.ext.split(',') if args.ext else None
    move = not args.copy

    if args.mode == 'extension':
        organize_by_extension(args.source, args.dest, move=move, dry_run=args.dry_run, include_ext=include_ext)
    else:
        organize_by_mtime(args.source, args.dest, move=move, dry_run=args.dry_run, by=args.by)


if __name__ == '__main__':
    main()
