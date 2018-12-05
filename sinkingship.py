# -*- encoding: utf-8

import json
import os

import requests
import tqdm


def create_session():
    s = requests.Session()

    # Error hook.  See https://alexwlchan.net/2017/10/requests-hooks/
    def check_for_errors(resp, *args, **kwargs):
        resp.raise_for_status()

    s.hooks["response"].append(check_for_errors)

    return s


def save_post_metadata(dst, post_data):
    post_id = post_data["id"]
    out_dir = os.path.join(dst, str(post_id)[:2], str(post_id))
    os.makedirs(out_dir, exist_ok=True)

    json_string = json.dumps(post_data, separators=(",", ":"))
    with open(os.path.join(out_dir, "info.json"), "w") as outfile:
        outfile.write(json_string)


def get_all_likes(*, blog_identifier, api_key):
    sess = create_session()

    params = {
        "api_key": api_key,
    }

    # First get the number of liked posts, so we can give the user some idea of
    # how many there are and how long the script will take.
    resp = sess.get(
        f"https://api.tumblr.com/v2/blog/{blog_identifier}/likes",
        params=params
    )

    liked_count = resp.json()["response"]["liked_count"]

    def iterator():
        params = {
            "api_key": api_key,
        }

        while True:
            resp = sess.get(
                f"https://api.tumblr.com/v2/blog/{blog_identifier}/likes",
                params=params
            )

            posts = resp.json()["response"]["liked_posts"]
            yield from posts

            # An empty posts list tells us we've finished.
            if not posts:
                break

            # Tumblr helpfully includes some query parameters in the response that
            # we can use to build our next request.
            params.update(resp.json()["response"]["_links"]["next"]["query_params"])

    return tqdm.tqdm(iterator(), total=liked_count)
