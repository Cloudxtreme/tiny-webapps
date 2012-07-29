#!/usr/bin/env python2.6

import hmac
import urllib2
import urlparse
from cStringIO import StringIO

from PIL import Image, ImageOps
from PIL.ImageFileIO import ImageFileIO


def crop_image(img, width, height):
    src_width, src_height = img.size
    src_ratio = float(src_width) / float(src_height)
    dst_width, dst_height = int(width), int(height)
    dst_ratio = float(dst_width) / float(dst_height)

    if dst_ratio < src_ratio:
        crop_height = src_height
        crop_width = crop_height * dst_ratio
        x_offset = float(src_width - crop_width) / 2
        y_offset = 0
    else:
        crop_width = src_width
        crop_height = crop_width / dst_ratio
        x_offset = 0
        y_offset = float(src_height - crop_height) / 3

    img = img.crop((x_offset, y_offset, x_offset+int(crop_width), y_offset+int(crop_height)))

    return img


def calculate_size(img, long_side):
    width, height = img.size
    width, height = float(width), float(height)

    if height > width:
        width = (width / height) * long_side
        height = long_side
    else:
        height = (height / width) * long_side
        width = long_side

    return width, height


def load_remote_image(url):
    return Image.open(ImageFileIO(urllib2.urlopen(url)))


def create_thumbnail(img, long_side):
    width, height = calculate_size(img, int(long_side))
    img.thumbnail((width, height), Image.ANTIALIAS)
    return img


def desaturate_image(img):
    img = ImageOps.grayscale(img)
    return img


KEY = ""

OPERATIONS = {
    "thumb": (create_thumbnail, 1),
    "crop": (crop_image, 2),
    "desaturate": (desaturate_image, 0),
}

def generate_sig(query):
    clean = ["{0}{1}".format(k,v) for k, v in query if k != "sig"]
    return hmac.new(KEY, "".join(clean)).hexdigest()


def thumbnailer_app(environ, start_response):
    to_do = []
    qs = []
    for tup in urlparse.parse_qsl(environ.get('QUERY_STRING', '')):
        if tup[0] == "sig":
            sig = tup[1]
        else:
            qs.append(tup)

    # Validate
    if generate_sig(qs) != sig:
        start_response('401 Forbidden', [('Content-Type', 'text/plain')])
        return ["You may not use the thumbnailer for that site."]

    need_values = 0
    for key, value in qs:
        if need_values > 0:
            to_do[-1].append(value)
            need_values -= 1
            continue

        if key == "image":
            path = value
        elif key == "op":
            op, args = OPERATIONS[value]
            need_values = args
            to_do.append([op])

    # Start the web response
    start_response('200 OK', [('Content-Type', 'image/jpeg')])

    img = load_remote_image(path)

    for action in to_do:
        func = action.pop(0)
        img = func(img, *action)

    return img.tostring('jpeg', img.mode)


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        qs = urlparse.parse_qsl(urlparse.urlparse(sys.argv[-1]).query)
        print "{0}&sig={1}".format(sys.argv[-1], generate_sig(qs))
        sys.exit(0)

    from flup.server.fcgi_fork import WSGIServer
    WSGIServer(thumbnailer_app, debug=True, maxSpare=1).run()
