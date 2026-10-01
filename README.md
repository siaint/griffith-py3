# Griffith

Griffith is a film collection manager, released under the GNU/GPL License.

Please see the file COPYING for licensing and warranty information.


## System Requirements

| Name                                                     | Minimum version | URL                                            | NOTE                                                  |
|----------------------------------------------------------|-----------------|------------------------------------------------|-------------------------------------------------------|
| Python                                                   | 3.10 or higher  | https://www.python.org                         | Tested up to Python 3.14                              |
| GTK+                                                     | 3.24.0          | https://www.gtk.org                            | GTK 3 toolkit                                         |
| PyGObject (replacing PyGTK)                              | 3.42.0          | https://pygobject.readthedocs.io               | GObject Introspection bindings (`gi.repository.Gtk`)  |
| SQLAlchemy                                               | 2.0             | https://www.sqlalchemy.org/                    | Imperative mapping (`registry.map_imperatively`)      |
| SQLite support                                           | Built-in        | https://docs.python.org/3/library/sqlite3.html | Python standard library `sqlite3` module is used      |
| Pillow (replacing PIL)                                   | 9.0             | https://python-pillow.org/                     | Poster and cover image manipulation                   |
| ReportLab                                                | 3.5             | https://www.reportlab.com/                     | PDF generation for covers and printable reports       |
| PostgreSQL support (optional): Psycopg                   | 2.9 or 3.0      | https://www.psycopg.org/                       | Optional driver for remote PostgreSQL databases       |
| MySQL support (optional): mysqlclient or PyMySQL         | 2.0             | https://github.com/PyMySQL/mysqlclient         | Replaces obsolete MySQLdb / MySQL-python              |
| Encoding detection of imported CSV file support: chardet | 4.0             | https://github.com/chardet/chardet             | Automatic charset detection on CSV imports            |
| GtkSpell (optional)                                      | 3.0             | https://gitlab.gnome.org/GNOME/gtkspell        | GObject Introspection bindings via GtkSpell-3.0       |
| Covers and reports support: PDF reader                   |                 |                                                | Any system PDF viewer (Evince, SumatraPDF, etc.)      |

## To check dependencies

    $ ./griffith --check-dep

## To show detected Python modules versions:

    $ ./griffith --show-dep

Windows installer includes all the needed requirements.
A GTK+ runtime is not necessary when using this installer.


## External databases

You need to prepare a new database and a new user by yourself

### PostgreSQL


	CREATE USER griffith UNENCRYPTED PASSWORD 'gRiFiTh' NOCREATEDB NOCREATEUSER;
	CREATE DATABASE griffith WITH OWNER = griffith ENCODING = 'UNICODE';
	GRANT ALL ON DATABASE griffith TO griffith;

### MySQL

	CREATE DATABASE `griffith` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
	CREATE USER 'griffith'@'localhost' IDENTIFIED BY 'gRiFiTh';
	CREATE USER 'griffith'@'%' IDENTIFIED BY 'gRiFiTh';
	GRANT ALL ON `griffith` . * TO 'griffith'@'localhost';
	GRANT ALL ON `griffith` . * TO 'griffith'@'%';

### Microsoft SQL Server

	CREATE DATABASE griffith
	EXEC sp_addlogin @loginame='griffith', @passwd='gRiFiTh', @defdb='griffith'
	GO
	USE griffith
	EXEC sp_changedbowner @loginame='griffith'


## Installation

See INSTALL file

## Reporting Bugs

If you want to help or report any bugs founded please visit:
  - https://github.com/micjahn/Griffith/issues/new

## TODO

See TODO file

## About the Authors

See AUTHORS file
