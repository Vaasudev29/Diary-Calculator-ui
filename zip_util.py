import io
import os
import zipfile


def create_project_zip_bytes(root_dir=None, exclude_dirs=None, exclude_files=None):
    """Create an in-memory ZIP of the project rooted at root_dir.

    - root_dir: directory to zip (defaults to repository root where this file lives)
    - exclude_dirs: iterable of directory names to exclude (by name)
    - exclude_files: iterable of file name patterns to exclude (exact names)

    Returns: bytes object containing the ZIP archive.
    """
    if root_dir is None:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
    if exclude_dirs is None:
        exclude_dirs = {'.venv', '.git', '__pycache__', '.pytest_cache', '.venv', '.idea', '.vscode', '.streamlit'}
    else:
        exclude_dirs = set(exclude_dirs)
    if exclude_files is None:
        exclude_files = set()
    else:
        exclude_files = set(exclude_files)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for foldername, subfolders, filenames in os.walk(root_dir):
            # compute relative path and skip excluded directories
            rel_folder = os.path.relpath(foldername, root_dir)
            # os.walk yields '.' for root
            if rel_folder == '.':
                rel_folder = ''
            # skip if any path segment is in exclude_dirs
            parts = [p for p in rel_folder.split(os.sep) if p]
            if any(p in exclude_dirs for p in parts):
                # prevent os.walk from recursing into these subfolders
                subfolders[:] = [d for d in subfolders if d not in exclude_dirs]
                continue

            for fname in filenames:
                if fname in exclude_files:
                    continue
                # skip common virtual env executables / caches
                if fname.endswith(('.pyc', '.pyo')):
                    continue

                full_path = os.path.join(foldername, fname)
                # compute archive name
                arcname = os.path.normpath(os.path.join(rel_folder, fname)) if rel_folder else fname
                try:
                    z.write(full_path, arcname)
                except OSError:
                    # skip files that cannot be read
                    continue

    buf.seek(0)
    return buf.getvalue()
