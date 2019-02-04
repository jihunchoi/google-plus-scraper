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
import lxml.html

import config
import utils


def clean_content(content):
    content = content.replace('<br />', '\n').strip()
    if content:
        content = lxml.html.document_fromstring(content).text_content()
    content = html.unescape(content)
    return content.strip()


def download_file(url, save_dir):
    req = utils.requests_retry_session().get(url, stream=True)
    if req.status_code == 200:
        if 'content-disposition' in req.headers:
            content_disposition = req.headers['content-disposition']
            filename_pattern = 'filename="(.*?)"'
            filename = re.findall(filename_pattern, content_disposition)[0]
            filename = filename.replace('/', '_')
        else:
            content_type = req.headers['content-type']
            filename, ext = content_type.rsplit('/', 1)
            filename = f'{filename.replace("/", "_")}.{ext}'
        save_path = Path(save_dir) / filename
        idx = 1
        while save_path.exists():
            new_filename = save_path.stem + str(idx) + save_path.suffix
            save_path = save_path.parent / new_filename
            idx += 1
        print(f'Will save to: {save_path}')

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

        if status_code != 200:
            print('Got failure; going into fallback mode (dirty)')
            parsed = lxml.html.document_fromstring(album_req.text)
            script_tags = parsed.cssselect('script')
            json_data = None
            for script_tag in script_tags:
                if ('AF_initDataCallback' in script_tag.text
                        and "key: 'ds:0'" in script_tag.text):
                    json_data_str = re.findall(
                        'return (.*?)}}', script_tag.text, flags=re.S)[0]
                    json_data = json.loads(json_data_str)
                    break
            if json_data is None:
                return 404
            url_tups = list(json_data[-1][-1][-1][-1].values())[-1][-1]
            max_res = 0
            url = None
            for url_tup in url_tups:
                res = url_tup[1] * url_tup[2]
                if res > max_res:
                    max_res = res
                    url = url_tup[3]
            print(f'Extracted dirty url {url}')
            new_status_code = download_file(url, save_dir)
            if new_status_code == 200:
                return 999
            return new_status_code
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
                annotation = clean_content(item.get('annotation', ''))
                orig_actor = item['object']['actor'].get('displayName', '???')
                orig_actor_line = f'Original post by {orig_actor}'
                orig_content = clean_content(item['object'].get('content', ''))
                formatted = (f'{actor_line}\n'
                             f'----------------------------------------\n'
                             f'{annotation}\n'
                             f'----------------------------------------\n\n'
                             f'{orig_actor_line}\n'
                             f'----------------------------------------\n'
                             f'{orig_content}')
            else:
                actor_line = f'Posted by {actor}'
                content = clean_content(item['object']['content'])
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
