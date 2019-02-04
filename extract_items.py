import argparse
import pickle

import requests

import config
import utils


def get_page(user_id, page_token=None):
    params = {'key': config.API_KEY}
    if page_token:
        params['pageToken'] = page_token
    api_url = config.API_URL.format(user_id=user_id)
    req = utils.requests_retry_session().get(api_url, params=params)
    json_data = req.json()
    next_page_token = json_data.get('nextPageToken', None)
    return json_data['items'], next_page_token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user-id', required=True)
    parser.add_argument('-o', '--out', default='items.pkl')
    args = parser.parse_args()

    items = []
    page_token = None
    while True:
        page_items, page_token = get_page(
            user_id=args.user_id, page_token=page_token)
        items.extend(page_items)
        print(f'Processed {len(items)} items')
        if page_token is None:
            break
    with open(args.out, 'wb') as f:
        pickle.dump(items, f)


if __name__ == '__main__':
    main()
