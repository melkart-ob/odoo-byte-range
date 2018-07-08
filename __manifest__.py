# -*- coding: utf-8 -*-
# Copyright 2016-2017 Melkart.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Odoo Byte-Range",
    "summary": "Byte-Range header support for Odoo. iOS and Mac devices can now play videos posted on the web"
               "web",
    "version": "1.0",
    "description": """
        iOS and Mac devices uses Byte-Range headers to play videos. By default Odoo doesn't support this feature, with
        some modifications it is now possible.
    """,
    "category": "Website",
    "website": "https://melkart-ob.com/",
    "author": "Rodolfo Alvarez García",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        'product'
    ],
    "data": [
        'views/product.xml',
    ],
    'qweb': [
    ],
    'application': True,
}
