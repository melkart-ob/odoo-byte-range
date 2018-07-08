# -*- coding: utf-8 -*-

from odoo import fields, models


class Product(models.Model):
    _inherit = "product.template"

    video = fields.Binary("Video", attachment=True, help="This field holds the product's video")


