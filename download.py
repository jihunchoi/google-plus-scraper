import argparse
import html
import json
import pickle
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import dateutil.parser

import config
import utils


def download_file(url, save_dir):
    req = utils.requests_retry_session().get(url, stream=True)
    content_disposition = req.headers['content-disposition']
    filename_pattern = 'filename="(.*?)"'
    filename = re.findall(filename_pattern, content_disposition)[0]
    filename = filename.replace('/', '_')
    print(f'Extracted filename: {filename}')

    save_path = Path(save_dir) / filename
    if req.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in req.iter_content(1024):
                f.write(chunk)
        print(f'Download completed: {save_path}')
        if filename.endswith('zip'):
            print(f'Unzipping {save_path}')
            f = zipfile.ZipFile(save_path)
            f.extractall(save_dir)
            print('Completed; deleting the zip file.')
            save_path.unlink()
    else:
        print(f'Got {req.status_code} while downloading file.')
    return req.status_code


def download_media(album_url, save_dir):
    print(f'Connecting to {album_url}')
    if 'youtu' in album_url:
        subprocess.run(['you-get', album_url, '-o', str(save_dir)])
        return 999
    album_req = utils.requests_retry_session().get(album_url)
    if album_req.status_code == 200:
        pattern = '(http.*?video-downloads\.googleusercontent\.com.*?)"'
        download_url = re.findall(pattern, album_req.text)[0]
        print(f'Extracted download URL: {download_url}')
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        status_code = download_file(download_url, save_dir)
    else:
        print(f'Got {album_req.status_code} while extracting URL.')
        status_code = album_req.status_code
    return status_code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--items', required=True)
    parser.add_argument('--resume', default=0, type=int)
    parser.add_argument('-o', '--out', required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)

    with open(args.items, 'rb') as f:
        items = pickle.load(f)

    failed = []
    for i, item in enumerate(items):
        try:
            if i < args.resume:
                continue
            print(f'Start #{i}')
            published_datetime = dateutil.parser.parse(item['published'])
            year_month_dir = published_datetime.strftime('%Y_%m')
            subdir = published_datetime.strftime('%Y_%m_%d_%H_%M_%S')
            save_dir = out_dir / year_month_dir / subdir
            if save_dir.exists():
                shutil.rmtree(save_dir)

            save_dir.mkdir(parents=True, exist_ok=True)

            with open(save_dir / 'raw.json', 'w') as f:
                json.dump(item, f, ensure_ascii=False)

            verb = item['verb']
            actor = item['actor']['displayName']
            if item['verb'] == 'share':
                actor_line = f'Posted by {actor} (Reshared post)'
                annotation = item.get('annotation', '').replace('<br />', '\n')
                annotation = html.unescape(annotation)
                orig_actor = item['object']['actor'].get('displayName', '???')
                orig_actor_line = f'Original post by {orig_actor}'
                orig_content = (
                    item['object'].get('content', '').replace('<br />', '\n'))
                orig_content = html.unescape(orig_content)
                formatted = (f'{actor_line}\n'
                             f'----------------------------------------\n'
                             f'{annotation}\n'
                             f'----------------------------------------\n\n'
                             f'{orig_actor_line}\n'
                             f'----------------------------------------\n'
                             f'{orig_content}')
            else:
                actor_line = f'Posted by {actor}'
                content = item['object']['content'].replace('<br />', '\n')
                content = html.unescape(content)
                formatted = (f'{actor_line}\n'
                             f'----------------------------------------\n'
                             f'{content}')
            with open(save_dir / 'content.txt', 'w') as f:
                f.write(formatted)

            attachments = item['object'].get('attachments', [])
            for att in attachments:
                status_code = download_media(att['url'], save_dir)
                if status_code != 200:
                    failed.append((i, item['id'], item['url']))
            print(f'Completed #{i}')
        except Exception as e:
            print('-' * 40)
            print(f'Caught exception: {e}')
            failed.append((i, item['id'], item['url']))
            break

    print('-' * 40)
    print('List of (possibly) failed posts')
    print('-' * 40)
    for i, id_, url in failed:
        print(f'{i},{id_},{url}')


if __name__ == '__main__':
    main()
