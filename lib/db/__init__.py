# -*- coding: UTF-8 -*-
# vim: fdm=marker
from __future__ import absolute_import
__revision__ = '$Id: __init__.py 1449 2010-09-29 21:03:04Z mikej06 $'
__version__ = 6 # XXX: database format version, remember to increase after changing data structures

# Copyright © 2009 Piotr Ożarowski
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# You may use and distribute this software under the terms of the
# GNU General Public License, version 2 or later

from sqlalchemy import MetaData, func, select, and_

from sqlalchemy.orm import registry, relationship, deferred, column_property, synonym
from sqlalchemy.inspection import inspect

mapper_registry = registry()

def safe_mapper(cls, *args, **kwargs):
    """Обертка над map_imperatively с очисткой устаревших аргументов SQLAlchemy 0.x"""
    # Удаляем не поддерживаемый в 2.0 аргумент order_by маппера
    kwargs.pop('order_by', None)
    
    try:
        insp = inspect(cls, raiseerr=False)
        if insp is not None:
            return insp
    except Exception:
        pass
    return mapper_registry.map_imperatively(cls, *args, **kwargs)

mapper = safe_mapper
relation = relationship

metadata = MetaData()
from . import tables # *after* metadata initialization
from ._objects import *


mapper(Configuration, tables.configuration)
mapper(Volume, tables.volumes, properties={
    'loaned': synonym('_loaned', map_column=True),
    'movies': relationship(Movie, backref='volume')})
mapper(Collection, tables.collections, properties={
    'loaned': synonym('_loaned', map_column=True),
    'movies': relationship(Movie, backref='collection')})
mapper(Medium, tables.media, properties={
    'movies': relationship(Movie, backref='medium')})
mapper(Ratio, tables.ratios, properties={
    'movies': relationship(Movie, backref='ratio')})
mapper(VCodec, tables.vcodecs, properties={
    'movies': relationship(Movie, backref='vcodec')})
mapper(Person, tables.people, properties={
    'loans': relationship(Loan, backref='person', cascade='all, delete-orphan'),
    'loaned_movies_count': column_property(
        select(func.count(tables.loans.c.loan_id))
        .where(
            and_(
                tables.people.c.person_id == tables.loans.c.person_id,
                tables.loans.c.return_date == None
            )
        )
        .scalar_subquery(),
        deferred=True
    ),
    'returned_movies_count': column_property(
        select(func.count(tables.loans.c.loan_id))
        .where(
            and_(
                tables.people.c.person_id == tables.loans.c.person_id,
                tables.loans.c.return_date != None
            )
        )
        .scalar_subquery(),
        deferred=True
    )
})
mapper(MovieLang, tables.movie_lang, primary_key=[tables.movie_lang.c.ml_id], properties={
    'movie': relationship(Movie),
    'language': relationship(Lang),
    'achannel': relationship(AChannel),
    'acodec': relationship(ACodec),
    'subformat': relationship(SubFormat)})
mapper(ACodec, tables.acodecs, properties={
    'movielangs': relationship(MovieLang)})
mapper(AChannel, tables.achannels, properties={
    'movielangs': relationship(MovieLang)})
mapper(SubFormat, tables.subformats, properties={
    'movielangs': relationship(MovieLang)})
mapper(Lang, tables.languages, properties={
    'movielangs': relationship(MovieLang)})
mapper(MovieTag, tables.movie_tag)
mapper(Tag, tables.tags, properties={'movietags': relationship(MovieTag, backref='tag')})
mapper(Loan, tables.loans, properties={
    'volume': relationship(Volume),
    'collection': relationship(Collection)})
mapper(Movie, tables.movies, properties={
    'loans': relationship(Loan, backref='movie', cascade='all, delete-orphan'),
    #'tags': relationship(Tag, cascade='all, delete-orphan', secondary=movie_tag,
    'tags': relationship(Tag, secondary=tables.movie_tag,
                     primaryjoin=tables.movies.c.movie_id == tables.movie_tag.c.movie_id,
                     secondaryjoin=tables.movie_tag.c.tag_id == tables.tags.c.tag_id),
    'languages': relationship(MovieLang, cascade='all, delete-orphan')})
mapper(Poster, tables.posters, properties={
    'movies': relationship(Movie),
    'data': deferred(tables.posters.c.data)})
mapper(Filter, tables.filters)
