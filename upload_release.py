import argparse
import os
import sys
from typing import Optional

try:
    import requests
except Exception:
    print('The requests library is required. Install with: pip install requests')
    sys.exit(1)


def find_or_create_release(session: requests.Session, owner: str, repo: str, tag: str, title: str, body: str, draft: bool, prerelease: bool):
    create_url = f'https://api.github.com/repos/{owner}/{repo}/releases'
    payload = {'tag_name': tag, 'name': title, 'body': body, 'draft': draft, 'prerelease': prerelease}

    r = session.post(create_url, json=payload)
    if r.status_code == 201:
        return r.json()
    if r.status_code == 422:
        # Tag already exists; try to fetch release by tag
        rt = session.get(f'https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}')
        if rt.status_code == 200:
            return rt.json()
        # Fall through to error
    # raise with helpful message
    raise RuntimeError(f'Failed to create or find release: {r.status_code} {r.text}')


def upload_asset(session: requests.Session, upload_url_template: str, file_path: str) -> dict:
    upload_url = upload_url_template.split('{')[0]
    filename = os.path.basename(file_path)
    url = f"{upload_url}?name={filename}"
    headers = {'Content-Type': 'application/zip'}
    with open(file_path, 'rb') as fh:
        r = session.post(url, headers=headers, data=fh)
    if r.status_code in (200, 201):
        return r.json()
    raise RuntimeError(f'Asset upload failed: {r.status_code} {r.text}')


def parse_args(argv) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Create a GitHub release and upload an asset')
    p.add_argument('--owner', default='Vaasudev29', help='GitHub owner/org')
    p.add_argument('--repo', default='Diary-Calculator-ui', help='Repository name')
    p.add_argument('--tag', default='v1.0.0', help='Release tag')
    p.add_argument('--title', default=None, help='Release title (defaults to tag)')
    p.add_argument('--body', default="Dairy_Yield_Chain_Updated.zip — updated project with ZIP release feature.", help='Release notes/body')
    p.add_argument('--draft', action='store_true', help='Create release as draft')
    p.add_argument('--prerelease', action='store_true', help='Mark release as prerelease')
    p.add_argument('--file', default=os.path.join(os.path.dirname(__file__), 'Dairy_Yield_Chain_Updated.zip'), help='Path to file to upload')
    p.add_argument('--token', default=None, help='GitHub token (optional; otherwise read GH_TOKEN env var)')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    token = args.token or os.getenv('GH_TOKEN')
    if not token:
        print('Error: GH_TOKEN environment variable is not set and --token not provided.')
        sys.exit(2)

    file_path = os.path.abspath(args.file)
    if not os.path.exists(file_path):
        print(f'Error: file not found: {file_path}')
        sys.exit(3)

    session = requests.Session()
    session.headers.update({'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json', 'User-Agent': 'upload-release-script'})

    title = args.title or args.tag
    try:
        release = find_or_create_release(session, args.owner, args.repo, args.tag, title, args.body, args.draft, args.prerelease)
        print('Release URL:', release.get('html_url'))
    except Exception as e:
        print('Error creating/finding release:', e)
        sys.exit(4)

    upload_url_template = release.get('upload_url')
    if not upload_url_template:
        print('Error: no upload_url in release payload')
        sys.exit(5)

    try:
        asset = upload_asset(session, upload_url_template, file_path)
        print('Upload successful:', asset.get('browser_download_url'))
    except Exception as e:
        print('Error uploading asset:', e)
        sys.exit(6)


if __name__ == '__main__':
    main()
