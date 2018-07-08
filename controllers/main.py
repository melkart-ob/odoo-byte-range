# -*- coding: utf-8 -*-

import base64
import logging

import werkzeug
import werkzeug.utils
import werkzeug.wrappers

import odoo
import odoo.modules.registry
from odoo import http
from odoo.addons.web.controllers import main
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def binary_content(xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None,
                   default_mimetype='application/octet-stream', env=None):
    return request.registry['ir.http'].binary_content(
        xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field,
        download=download, mimetype=mimetype, default_mimetype=default_mimetype, env=env)


class ByteRange(main.Binary):

    @http.route(['/web/image',
                 '/web/image/<string:xmlid>',
                 '/web/image/<string:xmlid>/<string:filename>',
                 '/web/image/<string:xmlid>/<int:width>x<int:height>',
                 '/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<string:model>/<int:id>/<string:field>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<string:filename>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<int:id>',
                 '/web/image/<int:id>/<string:filename>',
                 '/web/image/<int:id>/<int:width>x<int:height>',
                 '/web/image/<int:id>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<int:id>-<string:unique>',
                 '/web/image/<int:id>-<string:unique>/<string:filename>',
                 '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>',
                 '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>'], type='http', auth="public")
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas', filename_field='datas_fname', unique=None, filename=None, mimetype=None, download=None, width=0, height=0):
        status, headers, content = binary_content(xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field, download=download, mimetype=mimetype,
                                                  default_mimetype='image/png')
        if status == 304:
            return werkzeug.wrappers.Response(status=304, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200 and download:
            return request.not_found()

        height = int(height or 0)
        width = int(width or 0)
        if content and (width or height):
            # resize maximum 500*500
            if width > 500:
                width = 500
            if height > 500:
                height = 500
            content = odoo.tools.image_resize_image(base64_source=content, size=(width or None, height or None), encoding='base64', filetype='PNG')
            # resize force png as filetype
            headers = self.force_contenttype(headers, contenttype='image/png')

        if content:
            image_base64 = base64.b64decode(content)
        else:
            image_base64 = self.placeholder(image='placeholder.png')  # could return (contenttype, content) in master
            headers = self.force_contenttype(headers, contenttype='image/png')

        # headers.append(('Content-Length', len(image_base64)))
        response = Response(headers=headers, status=status)
        response.automatically_set_content_length = False
        response.set_data(image_base64)
        if request.httprequest.environ.get('HTTP_RANGE'):
            # For iOS and Mac media content type must match
            response.content_type = 'video/mp4'
        return response

    @http.route(['/web/content',
                 '/web/content/<string:xmlid>',
                 '/web/content/<string:xmlid>/<string:filename>',
                 '/web/content/<int:id>',
                 '/web/content/<int:id>/<string:filename>',
                 '/web/content/<int:id>-<string:unique>',
                 '/web/content/<int:id>-<string:unique>/<string:filename>',
                 '/web/content/<string:model>/<int:id>/<string:field>',
                 '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], type='http', auth="public")
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='datas', filename=None, filename_field='datas_fname', unique=None, mimetype=None, download=None, data=None, token=None,
                       **kw):
        status, headers, content = binary_content(xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field, download=download, mimetype=mimetype)
        if status == 304:
            response = werkzeug.wrappers.Response(status=status, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        # Add HTTP 206 Partial Content Header Support
        elif status == 206:
            if content:
                image_base64 = base64.b64decode(content)
            else:
                image_base64 = self.placeholder(image='placeholder.png')  # could return (contenttype, content) in master
                headers = self.force_contenttype(headers, contenttype='image/png')

            response = Response(headers=headers, status=status)
            response.automatically_set_content_length = False
            response.set_data(image_base64)
        elif status != 200:
            response = request.not_found()
        else:
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)
        if token:
            response.set_cookie('fileToken', token)
        return response
