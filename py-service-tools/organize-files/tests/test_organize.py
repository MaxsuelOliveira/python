import os
import tempfile
from organize_files.main import organize_by_extension, organize_by_mtime


def test_organize_by_extension_move(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    file1 = src / 'a.txt'
    file1.write_text('hello')
    file2 = src / 'b.jpg'
    file2.write_text('img')

    dest = tmp_path / 'dest'
    dest.mkdir()

    organize_by_extension(str(src), str(dest), move=True, dry_run=False)

    assert (dest / 'txt' / 'a.txt').exists()
    assert (dest / 'jpg' / 'b.jpg').exists()


def test_organize_by_mtime(tmp_path):
    src = tmp_path / 'src2'
    src.mkdir()
    file1 = src / 'c.txt'
    file1.write_text('x')
    # set mtime to a known timestamp
    import time
    ts = 1609459200  # 2021-01-01
    os.utime(str(file1), (ts, ts))

    dest = tmp_path / 'dest2'
    dest.mkdir()

    organize_by_mtime(str(src), str(dest), move=True, dry_run=False, by='month')

    assert (dest / '2021-01' / 'c.txt').exists()
