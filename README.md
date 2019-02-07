# Google Plus Scraper
I know the code is dirty.

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
    * You may add `--retry [POST_ID]` option to retry downloading the post with the specified ID.
1. Check the failure logs
    * "999" means that the post contains YouTube video. The program doesn't know whether the download is successful or not (since it delegates the job to the you-get library).
    * "888" means that the program couldn't download the original video files (whose link contains `video-downloads.googlecontent.com`), however succeeded at downloading from the post. This log is for the informative purpose, you may ignore this.
    * "777" then "200" means that the program couldn't find the video file anywhere, but luckily succeeded at downloading the thumbnail.
    * "400" and "500" means that the program couldn't connect to the server. I recommend retrying download in this case.
    * In case of "404", "405", and "408", it is likely to be a dead image. Forget about it.
    * But it is recommended to visit the original (failed) post to check whether there remains something worth to be saved!
