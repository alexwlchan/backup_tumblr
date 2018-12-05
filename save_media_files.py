#!/usr/bin/env python
# -*- encoding: utf-8

import os

import click

from sinkingship import find_all_metadata_files


@click.command(
    help="Save all the media files for your Tumblr posts/likes."
)
@click.option(
    "--metadata", default="tumblr",
    help="Directory where your metadata is saved."
)
def save_all_media_files(metadata):
    for mf in find_all_metadata_files(path=metadata):
        print(mf)


if __name__ == '__main__':
    save_all_media_files()
