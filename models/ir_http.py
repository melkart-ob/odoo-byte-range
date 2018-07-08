# -*- coding: utf-8 -*-
import base64
import hashlib
import mimetypes
import os
import re

from odoo import models
from odoo.addons.base.ir.ir_http import IrHttp
from odoo.exceptions import AccessError
from odoo.http import request, STATIC_CACHE
from odoo.modules import get_module_path, get_resource_path
from odoo.tools.mimetypes import guess_mimetype


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def binary_content(cls, xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
        """ Get file, attachment or downloadable content

        If the ``xmlid`` and ``id`` parameter is omitted, fetches the default value for the
        binary field (via ``default_get``), otherwise fetches the field for
        that precise record.

        :param str xmlid: xmlid of the record
        :param str model: name of the model to fetch the binary from
        :param int id: id of the record from which to fetch the binary
        :param str field: binary field
        :param bool unique: add a max-age for the cache control
        :param str filename: choose a filename
        :param str filename_field: if not create an filename with model-id-field
        :param bool download: apply headers to download the file
        :param str mimetype: mintype of the field (for headers)
        :param str default_mimetype: default mintype if no mintype found
        :param Environment env: by default use request.env
        :returns: (status, headers, content)
        """
        env = env or request.env
        # get object and content
        obj = None
        if xmlid:
            obj = env.ref(xmlid, False)
        elif id and model in env.registry:
            obj = env[model].browse(int(id))

        # obj exists
        if not obj or not obj.exists() or field not in obj:
            return 404, [], None

        # check read access
        try:
            last_update = obj['__last_update']
        except AccessError:
            return 403, [], None

        status, headers, content = None, [], None

        # attachment by url check
        module_resource_path = None
        if model == 'ir.attachment' and obj.type == 'url' and obj.url:
            url_match = re.match("^/(\w+)/(.+)$", obj.url)
            if url_match:
                module = url_match.group(1)
                module_path = get_module_path(module)
                module_resource_path = get_resource_path(module, url_match.group(2))
                if module_path and module_resource_path:
                    module_path = os.path.join(os.path.normpath(module_path), '')  # join ensures the path ends with '/'
                    module_resource_path = os.path.normpath(module_resource_path)
                    if module_resource_path.startswith(module_path):
                        with open(module_resource_path, 'rb') as f:
                            content = base64.b64encode(f.read())
                        last_update = str(os.path.getmtime(module_resource_path))

            if not module_resource_path:
                module_resource_path = obj.url

            if not content:
                status = 301
                content = module_resource_path
        else:
            content = obj[field] or ''

        # filename
        if not filename:
            if filename_field in obj:
                filename = obj[filename_field]
            elif module_resource_path:
                filename = os.path.basename(module_resource_path)
            else:
                filename = "%s-%s-%s" % (obj._name, obj.id, field)

        # mimetype
        mimetype = 'mimetype' in obj and obj.mimetype or False
        if not mimetype:
            if filename:
                mimetype = mimetypes.guess_type(filename)[0]
            if not mimetype and getattr(env[model]._fields[field], 'attachment', False):
                # for binary fields, fetch the ir_attachement for mimetype check
                attach_mimetype = env['ir.attachment'].search_read(domain=[('res_model', '=', model), ('res_id', '=', id), ('res_field', '=', field)], fields=['mimetype'], limit=1)
                mimetype = attach_mimetype and attach_mimetype[0]['mimetype']
            if not mimetype:
                mimetype = guess_mimetype(base64.b64decode(content), default=default_mimetype)

        headers += [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff')]

        # cache
        etag = hasattr(request, 'httprequest') and request.httprequest.headers.get('If-None-Match')
        retag = '"%s"' % hashlib.md5(content).hexdigest()
        status = status or (304 if etag == retag else 200)
        headers.append(('ETag', retag))
        headers.append(('Cache-Control', 'max-age=%s' % (STATIC_CACHE if unique else 0)))

        # content-disposition default name
        if download:
            headers.append(('Content-Disposition', IrHttp.content_disposition(filename)))
            # force download on safari
            headers.append(('Pragma', 'no-cache'))
            headers.append(('Expires', '0'))

        # Get Full File Length
        file_len = len(base64.b64decode(content))
        response_length = file_len

        # Just for byte-range requests
        if request.httprequest.environ.get('HTTP_RANGE', False):
            try:
                first, last = parse_byte_range(request.httprequest.environ.get('HTTP_RANGE'))
            except ValueError as e:
                return 400, [], None
            # Fix last for "x-" like ranges
            if last is None or last >= file_len:
                last = file_len - 1
            if first >= file_len:
                return 416, [], None
            status = 206
            # Offset ranges needs offset content
            if first != 0:
                if last != file_len - 1:
                    couple_bytes = base64.b64decode(content)[first:last]
                else:
                    couple_bytes = base64.b64decode(content)[first:]
                content = base64.b64encode(couple_bytes)
            response_length = last - first + 1
            headers.append(('Content-Range', 'bytes %s-%s/%s' % (first, last, file_len)))
            headers.append(('Accept-Ranges', 'bytes'))

        headers.append(('Content-Length', str(response_length)))
        return status, headers, content


BYTE_RANGE_RE = re.compile(r'bytes=(\d+)-(\d+)?$')


def parse_byte_range(byte_range):
    """Returns the two numbers in 'bytes=123-456' or throws ValueError.
    The last number or both numbers may be None.
    """
    if byte_range.strip() == '':
        return None, None

    m = BYTE_RANGE_RE.match(byte_range)
    if not m:
        raise ValueError('Invalid byte range %s' % byte_range)

    first, last = [x and int(x) for x in m.groups()]
    if last and last < first:
        raise ValueError('Invalid byte range %s' % byte_range)
    return first, last
