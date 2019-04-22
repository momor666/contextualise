import maya
from flask import (Blueprint, render_template, request, flash, url_for, redirect)
from flask_login import current_user
from flask_security import login_required
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.store.retrievaloption import RetrievalOption
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint('video', __name__)


@bp.route('/videos/<map_identifier>/<topic_identifier>')
def index(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    video_occurrences = topic_store.get_topic_occurrences(map_identifier, topic_identifier, 'video',
                                                          resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    videos = []
    for video_occurrence in video_occurrences:
        videos.append({'identifier': video_occurrence.identifier,
                       'title': video_occurrence.get_attribute_by_name('title').value,
                       'scope': video_occurrence.scope,
                       'url': video_occurrence.resource_ref})

    occurrences_stats = topic_store.get_topic_occurrences_statistics(map_identifier, topic_identifier)

    creation_date_attribute = topic.get_attribute_by_name('creation-timestamp')
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else 'Undefined'

    return render_template('video/index.html',
                           topic_map=topic_map,
                           topic=topic,
                           videos=videos,
                           creation_date=creation_date,
                           occurrences_stats=occurrences_stats)


@bp.route('/videos/<map_identifier>/add/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def add(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    form_video_title = ''
    form_video_url = ''
    form_video_scope = '*'

    error = 0

    if request.method == 'POST':
        form_video_title = request.form['video-title'].strip()
        form_video_url = request.form['video-url'].strip()
        form_video_scope = request.form['video-scope'].strip()

        # If no values have been provided set their default values
        if not form_video_scope:
            form_video_scope = '*'  # Universal scope

        # Validate form inputs
        if not form_video_title:
            error = error | 1
        if not form_video_url:
            error = error | 2
        if not topic_store.topic_exists(topic_map.identifier, form_video_scope):
            error = error | 4

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            video_occurrence = Occurrence(instance_of='video', topic_identifier=topic.identifier,
                                          scope=form_video_scope,
                                          resource_ref=form_video_url)
            title_attribute = Attribute('title', form_video_title, video_occurrence.identifier,
                                        data_type=DataType.STRING)

            # Persist objects to the topic store
            topic_store.set_occurrence(topic_map.identifier, video_occurrence)
            topic_store.set_attribute(topic_map.identifier, title_attribute)

            flash('Video link successfully added.', 'success')
            return redirect(
                url_for('video.index', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('video/add.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           video_title=form_video_title,
                           video_url=form_video_url,
                           video_scope=form_video_scope)
