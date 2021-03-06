# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE.
# Copyright (C) 2014, 2015 CERN.
#
# INSPIRE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this licence, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

"""Inspire views."""

import json

from flask import (
    redirect,
    request,
    Blueprint,
    render_template,
    current_app,
    url_for
)
from flask.ext.menu import register_menu, current_menu
from flask.ext.login import current_user

from invenio_base.i18n import _
from invenio_ext.email import send_email
from invenio_base.decorators import wash_arguments
from invenio_base.globals import cfg


blueprint = Blueprint('inspire', __name__, url_prefix="",
                      template_folder='templates', static_folder='static')


@blueprint.before_app_first_request
def register_menu_items():
    """Hack to remove children of Settings menu"""
    def menu_fixup():
        item = current_menu.submenu("settings.groups")
        item.hide()
        item = current_menu.submenu("settings.workflows")
        item.hide()
        item = current_menu.submenu("settings.applications")
        item.hide()
        item = current_menu.submenu("settings.oauthclient")
        item.hide()
    current_app.before_first_request_funcs.append(menu_fixup)


#
# Static pages
#

@blueprint.route('/about', methods=['GET', ])
@register_menu(blueprint, 'footermenu_left.about', _('About'), order=1)
# @register_breadcrumb(blueprint, 'breadcrumbs.about', _("About"))
def about():
    return render_template('inspire/about.html')


@blueprint.route('/privacy', methods=['GET', ])
@register_menu(blueprint, 'footermenu_left.privacy', _('Privacy'), order=2)
# @register_breadcrumb(blueprint, 'breadcrumbs.about', _("About"))
def privacy():
    return render_template('inspire/privacy.html')


@blueprint.route('/faq', methods=['GET', ])
@register_menu(blueprint, 'footermenu_left.faq', _('FAQ'), order=3)
# @register_breadcrumb(blueprint, 'breadcrumbs.about', _("About"))
def faq():
    return render_template('inspire/faq.html')


#
# Collections
#

@blueprint.route('/literature', methods=['GET', ])
@blueprint.route('/collection/literature', methods=['GET', ])
@blueprint.route('/', methods=['GET', 'POST'])
def index():
    """View for literature collection landing page."""
    collection = {'name': 'hep'}
    return render_template('search/collection_literature.html',
                           collection=collection)


@blueprint.route('/authors', methods=['GET', ])
@blueprint.route('/collection/authors', methods=['GET', ])
def hepnames():
    """View for authors collection landing page."""
    collection = {'name': 'hepnames'}
    return render_template('search/collection_authors.html',
                           collection=collection)


@blueprint.route('/conferences', methods=['GET', ])
def conferences():
    """View for conferences collection landing page."""
    collection = {'name': 'conferences'}
    return render_template('search/collection_conferences.html',
                           collection=collection)


@blueprint.route('/jobs', methods=['GET', ])
def jobs():
    """View for jobs collection landing page."""
    return redirect(url_for('search.search', cc='jobs'))


@blueprint.route('/institutions', methods=['GET', ])
def institutions():
    """View for institutions collection landing page."""
    collection = {'name': 'institutions'}
    return render_template('search/collection_institutions.html',
                           collection=collection)


@blueprint.route('/experiments', methods=['GET', ])
def experiments():
    """View for experiments collection landing page."""
    collection = {'name': 'experiments'}
    return render_template('search/collection_experiments.html',
                           collection=collection)


@blueprint.route('/journals', methods=['GET', ])
def journals():
    """View for journals collection landing page."""
    collection = {'name': 'journals'}
    return render_template('search/collection_journals.html',
                           collection=collection)


@blueprint.route('/data', methods=['GET', ])
def data():
    """View for data collection landing page."""
    collection = {'name': 'data'}
    return render_template('search/collection_data.html',
                           collection=collection)


#
# Handlers for AJAX requests regarding references and citations
#

@blueprint.route('/ajax/references', methods=['GET', 'POST'])
@wash_arguments({'recid': (unicode, ""),
                 'collection': (unicode, "")})
def ajax_references(recid, collection):
    """Handler for datatables references view"""
    from flask import jsonify
    from inspirehep.utils.references import Reference
    from invenio.base.globals import cfg
    from invenio_ext.es import es

    index = cfg['SEARCH_ELASTIC_COLLECTION_INDEX_MAPPING'].get(collection, 'hep')
    return jsonify(
        {
            "data": Reference(es.get(index=index, id=recid)['_source']).references()
        }
    )


@blueprint.route('/ajax/citations', methods=['GET', 'POST'])
@wash_arguments({'recid': (unicode, ""),
                 'collection': (unicode, "")})
def ajax_citations(recid, collection):
    """Handler for datatables citations view"""
    from flask import jsonify
    from inspirehep.utils.citations import Citation
    from invenio.base.globals import cfg
    from invenio_ext.es import es

    index = cfg['SEARCH_ELASTIC_COLLECTION_INDEX_MAPPING'].get(collection, 'hep')
    return jsonify(
        {
            "data": Citation(es.get(index=index, id=recid)['_source']).citations()
        }
    )

#
# Feedback handler
#


@blueprint.route('/postfeedback', methods=['POST', ])
def postfeedback():
    """Handler to create a ticket for user feedback."""
    subject = "INSPIRE Labs feedback"

    feedback = json.loads(request.form.get("data"))

    content = """
Feedback:

{feedback}
    """.format(feedback=feedback)

    # fd, temp_path = mkstemp(suffix=".png")
    # fh = os.fdopen(fd, "wb")
    # fh.write("".join(feedback_data[1].split(",")[1:]).decode('base64'))
    # fh.close()

    # attachments = [temp_path]
    attachments = []

    if send_email(fromaddr=cfg['CFG_SITE_SUPPORT_EMAIL'],
                  toaddr=cfg['INSPIRELABS_FEEDBACK_EMAIL'],
                  subject=subject,
                  content=content,
                  replytoaddr=current_user.get("email"),
                  attachments=attachments):
        return json.dumps(
            {'success': True}
        ), 200, {'ContentType': 'application/json'}
    else:
        return json.dumps(
            {'success': False}
        ), 500, {'ContentType': 'application/json'}

#
# Jinja2 filters
#


@blueprint.app_template_filter('marcxml')
def marcxml_filter(record):
    from inspirehep.dojson.hep import hep2marc
    from inspirehep.dojson.hepnames import hepnames2marc
    from inspirehep.dojson.utils import legacy_export_as_marc

    collections = [
        collection['primary'] for collection in record["collections"]
    ]

    if "HEP" in collections:
        return legacy_export_as_marc(hep2marc.do(record))
    elif "HEPNAMES" in collections:
        return legacy_export_as_marc(hepnames2marc.do(record))
