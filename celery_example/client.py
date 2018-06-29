import os

import tasks
from celery import group, chain


def get_filenames(folder):
    for root, dirs, files in os.walk(folder):
        if files:
            for filename in files:
                yield root, filename

chain(group(
        tasks.generate_thumbnail.s(*filename) for filename in  get_filenames('lfw')
    ) | tasks.genarate_gallery.s()
)()
