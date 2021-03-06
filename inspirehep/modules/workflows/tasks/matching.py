# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE.
# Copyright (C) 2014, 2015, 2016 CERN.
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

"""Tasks to check if the incoming record already exist."""

import datetime
import os
import traceback

from functools import wraps

from flask import current_app

from inspirehep.utils.arxiv import get_arxiv_id_from_record
from inspirehep.utils.datefilter import date_older_than
from inspirehep.utils.helpers import (
    get_record_from_model,
    get_record_from_obj
)

from invenio_base.globals import cfg
from invenio_base.wrappers import lazy_import

from invenio_matcher.api import match as _match

import requests

import six


BibWorkflowObject = lazy_import('invenio_workflows.models.BibWorkflowObject')


def search(query):
    """Perform a search and returns the matching ids."""
    params = dict(p=query, of='id')

    try:
        return requests.get(
            cfg["WORKFLOWS_MATCH_REMOTE_SERVER_URL"],
            params=params
        ).json()
    except requests.ConnectionError:
        current_app.logger.error(
            "Error connecting to remote server:\n {0}".format(
                traceback.format_exc()
            )
        )
        raise
    except ValueError:
        current_app.logger.error(
            "Error decoding results from remote server:\n {0}".format(
                traceback.format_exc()
            )
        )
        raise


def match_by_arxiv_id(record):
    """Match by arXiv identifier."""
    arxiv_id = get_arxiv_id_from_record(record)

    if arxiv_id:
        query = '035:"{0}"'.format(arxiv_id)
        return search(query)

    return list()


def match_by_doi(record):
    """Match by DOIs."""
    dois = record.get('dois.value', [])

    result = set()
    for doi in dois:
        query = '0247:"{0}"'.format(doi)
        result.update(search(query))

    return list(result)


def match(obj, eng):
    """Return True if the record already exists in INSPIRE.

    Searches by arXiv identifier and DOI, updates extra_data with the
    first id returned by the search.
    """
    model = eng.workflow_definition.model(obj)
    record = get_record_from_model(model)

    response = list(
        set(match_by_arxiv_id(record)) | set(match_by_doi(record))
    )

    obj.extra_data['record_matches'] = {
        "recids": [str(recid) for recid in response],
        "records": [],
        "base_url": os.path.join(
            cfg["CFG_ROBOTUPLOAD_SUBMISSION_BASEURL"],
            'record'
        )
    }
    return bool(obj.extra_data['record_matches']['recids'])


def match_with_invenio_matcher(queries=None, index="hep", doc_type="record"):
    """Match record using Invenio Matcher."""
    @wraps(match_with_invenio_matcher)
    def _match_with_invenio_matcher(obj, eng):
        model = eng.workflow_definition.model(obj)
        record = get_record_from_model(model)

        if queries is None:
            queries_ = [
                {'type': 'exact', 'match': 'dois.value'},
                {'type': 'exact', 'match': 'arxiv_eprints.value'}
            ]
        else:
            queries_ = queries

        record_matches = {
            "recids": [],
            "records": [],
            "base_url": os.path.join(
                cfg["CFG_SITE_URL"],
                'record'
            )
        }

        for matched_record in _match(record, queries=queries_, index=index, doc_type='record'):
            matched_recid = matched_record.record.get('control_number')
            record_matches['recids'].append(matched_recid)
            record_matches['records'].append({
                "source": matched_record.record.dumps(),
                "score": matched_record.score
            })

        obj.extra_data["record_matches"] = record_matches

        return bool(record_matches['recids'])
    return _match_with_invenio_matcher


def was_already_harvested(record):
    """Return True if the record was already harvested.

    We use the following heuristic: if the record belongs to one of the
    CORE categories then it was probably ingested in some other way.
    """
    categories = record.get('subject_terms.term', [])
    for category in categories:
        if category.lower() in cfg.get('INSPIRE_ACCEPTED_CATEGORIES', []):
            return True


def is_too_old(record, days_ago=5):
    """Return True if the record is more than days_ago days old.

    If the record is older then it's probably an update of an earlier
    record, and we don't want those.
    """
    earliest_date = record.get('earliest_date', '')
    if not earliest_date:
        earliest_date = record.get('preprint_date', '')
    parsed_date = datetime.datetime.strptime(earliest_date, "%Y-%m-%d")
    if date_older_than(parsed_date,
                       datetime.datetime.now(),
                       days=days_ago):
        return True


def record_exists(obj, eng):
    """Check if record exist in the system."""
    # Use matcher if not on production
    if not cfg.get('PRODUCTION_MODE'):
        if match_with_invenio_matcher()(obj, eng):
            obj.log.info("Record already exists in INSPIRE (using matcher).")
            return True
    else:
        obj.log.warning("Remote match is deprecated.")
        if match(obj, eng):
            obj.log.info("Record already exists in INSPIRE.")
            return True
    return False


def already_harvested(obj, eng):
    """Check if record is already harvested."""
    if cfg.get('PRODUCTION_MODE'):
        model = eng.workflow_definition.model(obj)
        record = get_record_from_model(model)

        if was_already_harvested(record):
            obj.log.info('Record is already being harvested on INSPIRE.')
            return True
    return False


def previously_rejected(days_ago=None):
    """Check if record exist on INSPIRE or already rejected."""
    @wraps(previously_rejected)
    def _previously_rejected(obj, eng):
        if cfg.get('PRODUCTION_MODE'):
            model = eng.workflow_definition.model(obj)
            record = get_record_from_model(model)

            if days_ago is None:
                _days_ago = cfg.get('INSPIRE_ACCEPTANCE_TIMEOUT', 5)
            else:
                _days_ago = days_ago

            if is_too_old(record, days_ago=_days_ago):
                obj.log.info("Record is likely rejected previously.")
                return True
        return False

    return _previously_rejected


def save_identifiers_to_kb(kb_name,
                           identifier_key="report_numbers.value"):
    """Save the record identifiers into a KB."""
    @wraps(save_identifiers_to_kb)
    def _save_identifiers_to_kb(obj, eng):
        from inspirehep.utils.knowledge import save_keys_to_kb
        record = get_record_from_obj(obj, eng)

        identifiers = record.get(identifier_key, [])
        save_keys_to_kb(kb_name, identifiers, obj.id)

    return _save_identifiers_to_kb


def exists_in_holding_pen(obj, eng):
    """Check if a record exists in HP by looking in given KB."""
    from invenio_workflows.search import search as hp_search
    record = get_record_from_obj(obj, eng)

    identifiers = []
    for field, lookup in six.iteritems(
            current_app.config.get("HOLDING_PEN_MATCH_MAPPING")):
        # Add quotes around to make the search exact
        identifiers += ['{0}:"{1}"'.format(field, i)
                        for i in record.get(lookup, [])]
    # Search for any existing record in Holding Pen, exclude self
    result = set(hp_search(
        query=" OR ".join(identifiers),
        per_page=10,
        page=1,
    )[0]) - set([obj.id])
    if result:
        obj.log.info("Record already found in Holding Pen ({0})".format(
            result
        ))
    obj.extra_data["holdingpen_ids"] = list(result)
    return result


def delete_self_and_stop_processing(obj, eng):
    """Delete both versions of itself and stops the workflow."""
    BibWorkflowObject.delete(obj.id)
    eng.skipToken()


def stop_processing(obj, eng):
    """Stop processing for object and return as completed."""
    eng.stopProcessing()


def update_old_object(obj, *args, **kwargs):
    """Update the data of the old object with the new data."""
    holdingpen_ids = obj.extra_data.get("holdingpen_ids", [])
    if holdingpen_ids and len(holdingpen_ids) == 1:
        old_object = BibWorkflowObject.query.get(holdingpen_ids[0])
        if old_object:
            # record waiting approval
            old_object.set_data(obj.data)
            old_object.save()
    else:
        msg = "Cannot update old object, non valid ids: {0}".format(holdingpen_ids)
        obj.log.error(msg)
        raise Exception(msg)
