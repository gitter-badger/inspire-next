# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE.
# Copyright (C) 2014, 2015 CERN.
#
# INSPIRE is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Inspire bundles."""

# '_' prefix indicates private variables, and prevents duplicated import by
# auto-discovery service of invenio
from invenio_base.bundles import invenio as _i, jquery as _j, styles as _base_styles

from invenio_deposit.bundles import js as _deposit_js

from invenio_ext.assets import Bundle, RequireJSFilter

from invenio_formatter.bundles import css as _formatter_css

js = Bundle(
    'js/inspire_base_init.js',
    output='base.js',
    filters=RequireJSFilter(exclude=[_j, _i]),
    weight=20,
    bower={
        "toastr": "latest",
        "jQuery-menu-aim": "latest",
        "clipboard": "latest"
    }
)


dependencies_to_remove = ["MathJax"]

for elem in dependencies_to_remove:
    try:
        del _j.bower[elem]
    except KeyError:
        pass


landing_page_styles = Bundle(
    "less/landing_page.less",
    output="landing_page.css",
    depends=[
        "less/landing_page.less"
    ],
    filters="less,cleancss",
    weight=60,
)

detailed_record_styles = Bundle(
    "less/format/detailed-record.less",
    "less/format/abstract.less",
    "vendors/datatables/media/css/dataTables.bootstrap.css",
    output="detailed-record.css",
    depends=[
        "less/format/detailed-record.less"
    ],
    filters="less,cleancss",
    weight=60,
)

detailed_record_js = Bundle(
    "js/detailed_record_init.js",
    output="detailed_record.js",
    filters=RequireJSFilter(exclude=[_j, _i]),
    weight=51,
    bower={
        "datatables": "1.10.10"
    }
)

brief_result_styles = Bundle(
    "less/format/brief-results.less",
    "less/format/abstract.less",
    output="brief-results.css",
    depends=[
        "less/format/brief-results.less"
    ],
    filters="less,cleancss",
    weight=60,
)

collection_landing_page_styles = Bundle(
    "less/search/collection.less",
    output="collection.css",
    depends=[
        "less/search/collection.less"
    ],
    filters="less,cleancss",
    weight=60,
)

# FIXME variables.less is already imported in inspire.less so there should be
# no need to add it here to the contents. If it is not added, the depends=
# parameter takes no effect and modifications to the file don't trigger
# bundle refresh.
_base_styles.contents += (
    'less/inspire.less',
    'less/accounts/settings/account-settings.less',
    'less/base/variables.less',
    'less/base/header.less',
    'less/base/footer.less',
    'less/base/panels.less',
    'less/base/helpers.less',
    'less/base/sticky-footer.less',
    'less/base/list-group.less',
    'less/base/core.less',
    'less/accounts/login.less',
    'less/search/index.less',
    'less/feedback/button.less',
    'less/feedback/modal.less',
    'less/workflows/workflows.less',
    'vendors/toastr/toastr.css'
)

_base_styles.bower["font-awesome"] = "4.4.0"

to_remove = ["less/base.less",
             "less/user-menu.less",
             "less/sticky-footer.less",
             "less/footer.less"]

for elem in to_remove:
    _base_styles.contents.remove(elem)


_deposit_js.bower["eonasdan-bootstrap-datetimepicker"] = \
    "git://github.com/inspirehep/bootstrap-datetimepicker.git#allow-only-year"

_formatter_css.contents += (
    'css/formatter/templates_detailed_inspire.css',
)
