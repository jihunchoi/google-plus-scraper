# Google Plus Scraper
## Configuration
1. Make `credentials.py` and add the following line:
    ```
    API_KEY = [YOUR_API_KEY]
    ```
1. Install dependencies
    ```
    pip install -r requirements.txt
    ```

## How to Run
1. Extract (meta-)data
    ```
    python extract_items.py --user-id [USER_ID] --out [ITEMS_FILE]
    ```
1. Download
    ```
    python download.py --items [ITEMS_FILE] --out [SAVE_DIR]
    ```
    * You may add `--resume N` option to resume downloading from the index `N`.
