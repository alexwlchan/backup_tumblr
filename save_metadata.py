#!/usr/bin/env python
# -*- encoding: utf-8

import click


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
    prompt="Where do you want to save your metadata?",
    help="Directory for saving metadata"
)
@click.option(
    "--mode",
    type=click.Choice(["likes", "posts"]), default="posts",
    prompt="Do you want to save likes or posts?",
    help="Whether to save likes or posts"
)
def save_metadata(blog_identifier, api_key, dst, mode):
    print(blog_identifier)
    print(api_key),
    print(dst)
    print(mode)


if __name__ == '__main__':
    save_metadata()
