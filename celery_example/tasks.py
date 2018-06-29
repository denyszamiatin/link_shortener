import os

from celery import Celery
from PIL import Image

app = Celery('tasks', broker="amqp://", backend='redis://')


@app.task
def generate_thumbnail(root, filename):
    image = Image.open(os.path.join(root, filename))
    image.thumbnail((64, 64))
    image.save(os.path.join('thumbnails', filename))
    return filename


@app.task
def genarate_gallery(filenames):
    gallery = Image.new('RGB', (64*20, (len(filenames)//20) * 64))

    x_offset = y_offset = 0

    for filename in filenames:
        image = Image.open(os.path.join('thumbnails', filename))
        gallery.paste(image, (x_offset, y_offset))
        x_offset += 64
        if x_offset > 64*20:
            x_offset = 0
            y_offset += 64

    gallery.save("gallery.jpg", 'JPEG')

    return 'Ok'
