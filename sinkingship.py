# -*- encoding: utf-8

import json
import os
import subprocess
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlretrieve

from bs4 import BeautifulSoup
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

    api_url = f"https://api.tumblr.com/v2/blog/{blog_identifier}/likes"

    # First get the number of liked posts, so we can give the user some idea of
    # how many there are and how long the script will take.
    resp = sess.get(api_url, params=params)

    liked_count = resp.json()["response"]["liked_count"]

    def iterator():
        params = {
            "api_key": api_key,
        }

        while True:
            resp = sess.get(api_url, params=params)

            posts = resp.json()["response"]["liked_posts"]
            yield from posts

            # An empty posts list tells us we've finished.
            if not posts:
                break

            # Tumblr helpfully includes some query parameters in the response that
            # we can use to build our next request.
            params.update(resp.json()["response"]["_links"]["next"]["query_params"])

    return tqdm.tqdm(iterator(), total=liked_count)


def get_all_posts(*, blog_identifier, api_key):
    sess = create_session()

    params = {
        "api_key": api_key,
    }

    api_url = f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts"

    # First get the number of liked posts, so we can give the user some idea of
    # how many there are and how long the script will take.
    resp = sess.get(api_url, params=params)

    total_posts = resp.json()["response"]["total_posts"]

    def iterator():
        params = {
            "api_key": api_key,
            "reblog_info": True,
            "notes_info": True,
        }

        while True:
            resp = sess.get(api_url, params=params)

            posts = resp.json()["response"]["posts"]
            yield from posts

            # An empty posts list tells us we've finished.
            if not posts:
                break

            # We can only get the last 1000 posts with the offset parameter;
            # instead look at the timestamps of the posts we retrieved and
            # set that as the "before" parameter.
            earliest_timestamp = min(p["timestamp"] for p in posts)
            params["before"] = earliest_timestamp - 1

    return tqdm.tqdm(iterator(), total=total_posts)


def find_all_metadata_files(path):
    if not os.path.exists(path):
        raise ValueError(f"Asked to save media files in non-existent dir {path!r}?")

    if not os.path.isdir(path):
        raise ValueError(f"Asked to save media files in non-directory {path!r}?")

    for root, _, filenames in os.walk(path):
        if "info.json" in filenames:
            yield os.path.join(root, "info.json")


def _download_asset(post_dir, url, suffix=""):
    name = os.path.basename(url) + suffix
    out_path = os.path.join(post_dir, name)
    if os.path.exists(out_path):
        return
    try:
        urlretrieve(url, out_path)
    except HTTPError:
        print(url)
        return


def _download_with_youtube_dl(post_dir, url):
    """
    Download a video using youtube-dl.
    """

    # The purpose of this marker is to check "have we run youtube_dl before?"
    #
    # Although youtube_dl is smart about not re-downloading files, it has to make
    # a network request before it does that, which is slow and mostly unnecessary.
    # This is a crude way to avoid unnecessary shell-outs/network requests.
    #
    marker = os.path.join(post_dir, ".youtube_dl")
    if os.path.exists(marker):
        return

    try:
        subprocess.check_call(
            ["youtube-dl", url],
            stdout=subprocess.DEVNULL,
            cwd=post_dir
        )
    except subprocess.CalledProcessError as err:
        post_id = os.path.basename(post_dir)
        print(f"Unable to download video for post ID {post_id} from {url!r} ({err}).")
    else:
        open(marker, "wb").write(b"")


def save_post_media_files(info_path):
    post_data = json.load(open(info_path))
    post_dir = os.path.dirname(info_path)
    post_id = post_data["id"]

    if post_data["type"] == "photo":
        for photo in post_data["photos"]:
            _download_asset(post_dir=post_dir, url=photo["original_size"]["url"])

    elif post_data["type"] in ("answer", "chat", "link", "quote", "text"):
        return

    elif post_data["type"] == "video":
        players = [p for p in post_data["player"] if p["embed_code"]]

        if post_data["video_type"] == "tumblr":
            _download_asset(post_dir=post_dir, url=post_data["video_url"])

        elif post_data["video_type"] == "youtube":
            if all(not p["embed_code"] for p in post_data["player"]):
                return

            try:
                if post_data["source_url"].startswith("https://www.youtube.com/embed"):
                    source_url = post_data["source_url"]
                else:
                    source_url = parse_qs(urlparse(post_data["source_url"]).query)["z"][0]
            except KeyError:
                best_player = max(players, key=lambda p: p["width"])
                soup = BeautifulSoup(best_player["embed_code"], "html.parser")
                iframe_matches = soup.find_all("iframe", attrs={"id": "youtube_iframe"})
                assert len(iframe_matches) == 1

                source_url = iframe_matches[0].attrs["src"]

            _download_with_youtube_dl(post_dir=post_dir, url=source_url)

        elif post_data["video_type"] in ("vimeo", "youtube"):
            best_player = max(players, key=lambda p: p["width"])
            soup = BeautifulSoup(best_player["embed_code"], "html.parser")
            iframe_matches = soup.find_all("iframe")
            assert len(iframe_matches) == 1

            embed_url = iframe_matches[0].attrs["src"]

            _download_with_youtube_dl(post_dir=post_dir, url=embed_url)

        elif (
            post_data["video_type"] == "unknown" and
            post_data.get("source_url").startswith("https://t.umblr.com/redirect?z=http%3A%2F%2Fwww.youtube.com")
        ):
            source_url = parse_qs(urlparse(post_data["source_url"]).query)["z"][0]
            _download_with_youtube_dl(post_dir=post_dir, url=source_url)

        elif post_data["video_type"] == "instagram":
            source_url = post_data["permalink_url"]
            _download_with_youtube_dl(post_dir=post_dir, url=source_url)

        elif post_data["video_type"] == "flickr":
            source_url = parse_qs(urlparse(post_data["source_url"]).query)["z"][0]
            print(f"Unable to download video for {post_id!r}: {source_url}")

        else:
            print(f"Unable to download video for {post_id!r}")

    elif post_data["type"] == "audio":

        # Exammple contents of the "player" field:
        #
        #     <iframe
        #       class="tumblr_audio_player tumblr_audio_player_76004518890"
        #       src="http://example.tumblr.com/post/1234/audio_player_iframe/example/tumblr_1234?audio_file=https%3A%2F%2Fwww.tumblr.com%2Faudio_file%2Fexample%2F1234%2Ftumblr_1234"
        #       frameborder="0"
        #       allowtransparency="true"
        #       scrolling="no"
        #       width="540"
        #       height="169"></iframe>
        #
        if post_data["audio_type"] == "tumblr":
            player_soup = BeautifulSoup(post_data["player"], "html.parser")
            player_matches = player_soup.find_all(
                "iframe", attrs={"class": "tumblr_audio_player"}
            )
            assert len(player_matches) == 1

            src_url = player_matches[0]["src"]
            query_string = parse_qs(urlparse(src_url).query)
            assert len(query_string["audio_file"]) == 1
            audio_file = query_string["audio_file"][0]
            print(
                f"Unable to download audio file for {post_id!r}: {audio_file!r}"
            )

        elif post_data["audio_type"] == "spotify":
            source_url = post_data["audio_source_url"]
            print(
                f"Unable to download audio file for {post_id!r}: {source_url!r}"
            )

        elif post_data["audio_type"] == "soundcloud":
            source_url = post_data["audio_source_url"]
            print(
                f"Unable to download audio file for {post_id!r}: {source_url!r}"
            )

        else:
            print(f"Unable to download audio for {post_id!r}")

    else:
        post_type = post_data["type"]
        raise ValueError(f"Unrecognised post type: {post_id!r} ({post_type})")
