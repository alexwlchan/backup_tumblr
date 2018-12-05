#!/usr/bin/env python
# -*- encoding: utf-8

import json

import click

from sinkingship import get_all_likes, save_post_metadata


@click.command()
@click.option(
    "--blog_identifier", required=True,
    prompt="What is your blog identifier? e.g. 'alexwlchan.tumblr.com'",
    help="Blog identifier, as used by the Tumblr API"
)
@click.option(
    "--api_key", required=True,
    prompt="What is your API key? Register at https://www.tumblr.com/oauth/apps",
    help="OAuth API key for the Tumblr API (https://www.tumblr.com/oauth/apps)"
)
@click.option(
    "--dst", default="tumblr",
    help="Directory for saving metadata"
)
def save_metadata(blog_identifier, api_key, dst):
    for post_data in get_all_likes(blog_identifier=blog_identifier, api_key=api_key):
        save_post_metadata(dst=dst, post_data=post_data)

if __name__ == '__main__':
    save_metadata()
