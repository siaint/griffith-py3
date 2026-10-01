# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from six.moves import range
__revision__ = '$Id: backup.py 1632 2012-12-16 21:15:57Z mikej06 $'

# Copyright (c) 2005-2009 Vasco Nunes, Piotr Ożarowski
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

import copy
import datetime
import logging
import os.path
import zipfile
from io import BytesIO
from shutil import rmtree, move
from tempfile import mkdtemp

from sqlalchemy import create_engine, select, insert, text
from platform import system

from lib import config
from lib import gutils
from lib import db
from lib import sql
from lib.initialize import dictionaries, people_treeview

from gi.repository import Gtk
gtk = Gtk

try:
    import EasyDialogs
except:
    pass
    
log = logging.getLogger('Griffith')

def create(self):
    """perform a compressed griffith database/posters/preferences backup"""
    #if self.db.session.bind.engine.name != 'sqlite':
    #    gutils.error(_("Backup function is available only for SQLite engine for now"), self.widgets['window'])
    #    return False
    
    default_name = "%s_backup_%s.zip" % (self.config.get('name', 'griffith', section='database'),\
                    datetime.date.isoformat(datetime.datetime.now()))
    filename = gutils.file_chooser(_("Save Griffith backup"), \
        action=Gtk.FileChooserAction.SAVE, name=default_name, \
        buttons=(gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, gtk.STOCK_SAVE, Gtk.ResponseType.OK))

    if filename and filename[0]:
        proceed = True
        zipfilename = filename[0]
        log.debug('Backup filename: %s', zipfilename)
        if os.path.isfile(zipfilename):
            if not gutils.question(_("File exists. Do you want to overwrite it?"), window=self.widgets['window']):
                proceed = False

        if proceed:
            try:
                if zipfile.zlib is not None:
                    log.debug('Creating zip file with compression')
                    mzip = zipfile.ZipFile(zipfilename, 'w', zipfile.ZIP_DEFLATED)
                else:
                    log.debug('Creating zip file without compression')
                    mzip = zipfile.ZipFile(zipfilename, 'w')
            except:
                gutils.error(_("Error creating backup"), self.widgets['window'])
                return False
            log.debug('Preparing data and saving it to the zip archive')
            if self.db.engine.name == 'sqlite':
                mzip.write(os.path.join(self.locations['home'], 'griffith.cfg'), arcname='griffith.cfg')
                db_file_name = "%s.db" % self.config.get('name', 'griffith', section='database')
                file_path = os.path.join(self.locations['home'], db_file_name)
                mzip.write(file_path, arcname=db_file_name)
            else:
                tmp_engine = None
                try:
                    tmp_dir = mkdtemp()
                    tmp_config_file = os.path.join(tmp_dir, 'griffith.cfg')
                    self.config.save(tmp_config_file)
                    tmp_config = config.Config(file=tmp_config_file)
                    tmp_config.set('type', 'sqlite', section='database')
                    tmp_config.set('file', 'griffith.db', section='database')
                    tmp_config.set('name', 'griffith', section='database')
                    tmp_config.save()
                    mzip.write(tmp_config._file, arcname='griffith.cfg')

                    tmp_file = os.path.join(tmp_dir, 'griffith.db')
                    tmp_engine = create_engine("sqlite:///%s" % tmp_file)
                    db.metadata.create_all(bind=tmp_engine)

                    # SQLite doesn't care about foreign keys much so we can just copy the data
                    with self.db.engine.connect() as src_conn, tmp_engine.begin() as dst_conn:
                        for table in db.metadata.sorted_tables:
                            if table.name in ('poster', 'posters', 'filters'):
                                continue
                            rows = [dict(r._mapping) for r in src_conn.execute(select(table)).fetchall()]
                            if rows:
                                dst_conn.execute(table.insert(), rows)

                        # posters
                        p_table = getattr(db, 'Poster', None).__table__ if hasattr(db, 'Poster') else (db.metadata.tables.get('poster') or db.metadata.tables.get('posters'))
                        for p in src_conn.execute(select(p_table)).fetchall():
                            p_dict = dict(p._mapping)
                            dst_conn.execute(p_table.insert(), [{'md5sum': p_dict['md5sum'], 'data': bytes(p_dict['data'])}])

                    mzip.write(tmp_file, arcname='griffith.db')
                finally:
                    # disposing the temporary db connection before rmtree and in finally block to avoid locked db file
                    if tmp_engine:
                        tmp_engine.dispose()
                    rmtree(tmp_dir)
            gutils.info(_("Backup has been created"), self.widgets['window'])


@gutils.popup_message(_('Restoring database...'))
def copy_db(src_engine, dst_engine):
    print('=' * 60)
    print('[RESTORE AUDIT] START copy_db')
    print(f'[RESTORE AUDIT] SRC URL: {src_engine.url}')
    print(f'[RESTORE AUDIT] DST URL: {dst_engine.url}')
    print('=' * 60)
    
    # Включаем эхо на уровне движков, чтобы видеть сырой SQL в консоли
    src_engine.echo = False
    dst_engine.echo = False  # поставьте True, если захотите видеть каждый INSERT

    with src_engine.connect() as s_conn, dst_engine.begin() as d_conn:
        print('[RESTORE AUDIT] Connected to both databases successfully.')
        
        # 1. Проверяем таблицу постеров
        p_table = getattr(db, 'Poster', None).__table__ if hasattr(db, 'Poster') else (db.metadata.tables.get('poster') or db.metadata.tables.get('posters'))
        if p_table is not None:
            src_posters = s_conn.execute(select(p_table)).fetchall()
            print(f'[RESTORE AUDIT] Source posters read: {len(src_posters)}')
            d_conn.execute(p_table.delete())
            print('[RESTORE AUDIT] Destination posters cleared.')
            
            seen_md5 = set()
            poster_rows = []
            for p in src_posters:
                p_dict = dict(p._mapping)
                md5 = p_dict.get('md5sum')
                if md5 and md5 not in seen_md5:
                    seen_md5.add(md5)
                    raw_data = p_dict.get('data')
                    poster_rows.append({'md5sum': md5, 'data': bytes(raw_data) if raw_data is not None else b''})
            if poster_rows:
                d_conn.execute(p_table.insert(), poster_rows)
            print(f'[RESTORE AUDIT] Destination posters inserted: {len(poster_rows)}')

        # 2. Перебираем остальные таблицы
        for table in db.metadata.sorted_tables:
            if table.name in ('poster', 'posters', 'filters'):
                continue
            rows = s_conn.execute(select(table)).fetchall()
            print(f'[RESTORE AUDIT] Table "{table.name}": read {len(rows)} rows from SRC')
            
            # Очищаем таблицу перед накатыванием
            d_conn.execute(table.delete())
            
            data = [dict(r._mapping) for r in rows]
            if data:
                insertcmd = table.insert()
                for partition in range(0, len(data), 50):
                    d_conn.execute(insertcmd, data[partition:partition + 50])
            print(f'[RESTORE AUDIT] Table "{table.name}": inserted {len(data)} rows into DST')

    print('=' * 60)
    print('[RESTORE AUDIT] copy_db FINISHED & COMMITTED!')
    print('=' * 60)

def merge_db(src_db, dst_db):  # FIXME
    merged = 0
    dst_db.session.rollback()  # cancel all pending operations
    src_session = src_db.Session()  # create new session
    dst_session = dst_db.Session()  # create new session
    movies = src_session.query(db.Movie).count()
    for movie in src_session.query(db.Movie).all():
        if dst_session.query(db.Movie).filter_by(o_title=movie.o_title).first() is not None:
            continue
        t_movies = {}
        for column in movie.mapper.c.keys():
            t_movies[column] = eval("movie.%s" % column)

        # replace number with new one
        t_movies["number"] = gutils.find_next_available(dst_db)

        # don't restore volume/collection/tag/language/loan data (it's dangerous)
        t_movies.pop('movie_id')
        t_movies.pop('loaned')
        t_movies.pop('volume_id')
        t_movies.pop('collection_id')

        if dst_db.add_movie(t_movies):  # FIXME
            print(t_movies)

        if movie.image is not None:
            dest_file = os.path.join(self.locations['posters'], movie.image + '.jpg')
            if not os.path.isfile(dest_file):
                src_file = os.path.join(tmp_dir, movie.image + '.jpg')
                if os.path.isfile(src_file):
                    move(src_file, dest_file)
        merged += 1
    return merged


def restore(self, merge=False):
    """
    Merge database from:
    * compressed backup (*.zip)
    * SQLite2 *.gri file
    * SQLite3 *.db file
    """
    # let user select a backup file
    filename, path = gutils.file_chooser(_("Restore Griffith backup"), \
                action=Gtk.FileChooserAction.OPEN, backup=True, \
                buttons=(gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, gtk.STOCK_OPEN, Gtk.ResponseType.OK))
    if not filename:
        log.debug('no file selected')
        return False

    try:
        tmp_db = None
        tmp_dir = mkdtemp()
        os.mkdir(os.path.join(tmp_dir, 'posters'))
        print(filename)
        if filename.lower().endswith('.zip'):
            try:
                zip_file = zipfile.ZipFile(filename, 'r')
            except:
                gutils.error(_("Can't read backup file"), self.widgets['window'])
                return False

            old_config_file = False
            # unpack files to temporary directory
            for file_path in zip_file.namelist():
                file_name = os.path.split(file_path)[-1]
                if not os.path.isdir(file_name):
                    if not file_name:
                        log.debug('skipping %s', file_path)
                        continue

                    if 'posters' in file_path:
                        new_file = os.path.join(tmp_dir, 'posters', file_name)
                    else:
                        new_file = os.path.join(tmp_dir, file_name)
                    if file_name.endswith('.conf'):
                        old_config_file = new_file
                    outfile = open(new_file, 'wb')
                    outfile.write(zip_file.read(file_path))
                    outfile.close()
            zip_file.close()

            # restore config file (new one will be created if old config format is detected)
            tmp_config = config.Config(file=os.path.join(tmp_dir, 'griffith.cfg'))
            if old_config_file:
                log.info('Old config file detected. Please note that it will not be used.')
                f = open(old_config_file, 'r')
                old_config_raw_data = f.read()
                f.close()
                if old_config_raw_data.find('griffith.gri') >= -1:
                    tmp_config.set('file', 'griffith.gri', section='database')

            # update filename var. to point to the unpacked database
            filename = os.path.join(tmp_dir, tmp_config.get('name', 'griffith', section='database') + '.db')
        else:  # not a zip file? prepare a fake config file then
            tmp_config = config.Config(file=os.path.join(tmp_dir, 'griffith.cfg'))
            tmp_config.set('type', 'sqlite', section='database')
            tmp_config.set('file', 'griffith.db', section='database')

        # prepare temporary GriffithSQL instance
        locations = {'home': tmp_dir}
        # check if file needs conversion
        if filename.lower().endswith('.gri'):
            from dbupgrade import convert_from_old_db
            tmp_db = convert_from_old_db(tmp_config, filename, os.path.join(tmp_dir, 'griffith.db'), locations)
            if not tmp_db:
                log.info("MERGE: Can't convert database, aborting.")
                return False
        else:
            tmp_db = sql.GriffithSQL(tmp_config, tmp_dir, fallback=False)

        if merge:
            merge_db(tmp_db, self.db)
        else:
            self.db.session.rollback()  # cancel all pending operations
            print(f"[RESTORE AUDIT] tmp_dir: {tmp_dir}")
            print(f"[RESTORE AUDIT] tmp_db engine: {tmp_db.engine.url}")
            print(f"[RESTORE AUDIT] self.db engine: {self.db.engine.url}")
            copy_db(tmp_db.engine, self.db.engine)
            # update old database section with current config values
            # (important while restoring to external databases)
            for key in ('name', 'passwd', 'host', 'user', 'file', 'type', 'port'):
                tmp_config.set(key, self.config.get(key, section='database'), section='database')
            tmp_config._file = self.config._file
            self.config = tmp_config
            self.config.save()
            dictionaries(self)
            people_treeview(self)
            # let's refresh the treeview
            self.clear_details()
            self.populate_treeview()
        #gutils.info(_("Databases merged!\n\nProcessed movies: %s\nMerged movies: %s"%(movies, merged)), self.widgets['window'])
        gutils.info(_("Backup restored"), self.widgets['window'])
    except:
        log.exception('')
        raise
    finally:
        # disposing the temporary db connection before rmtree and in finally block to avoid locked db file
        if tmp_db:
            tmp_db.dispose()
        log.debug('temporary directory no logger needed, removing %s', tmp_dir)
        rmtree(tmp_dir)
