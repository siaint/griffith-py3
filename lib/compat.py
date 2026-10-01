# lib/compat.py
"""
Адаптер для плавной миграции Griffith с PyGTK 2 / Glade на PyGObject / GTK 3.
Эмулирует поведение gtk.glade.XML через современный Gtk.Builder.
"""
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject

class _SignalProxy:
    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        if isinstance(self._target, dict):
            if name in self._target:
                return self._target[name]
        elif hasattr(self._target, name):
            return getattr(self._target, name)

        return lambda *args, **kwargs: None

    def __getitem__(self, name):
        if isinstance(self._target, dict) and name in self._target:
            return self._target[name]
        return getattr(self, name)



class GladeXMLCompat:
    def __init__(self, filename, root=None, domain=None):
        self.builder = Gtk.Builder()
        
        # Если передан путь к .glade, подменяем на сконвертированный .ui
        if filename.endswith('.glade'):
            ui_filename = filename[:-6] + '.ui'
            if os.path.exists(ui_filename):
                filename = ui_filename

        self.builder.add_from_file(filename)

    def get_widget(self, name):
        """Эмуляция вызова get_widget из старого gtk.glade"""
        widget = self.builder.get_object(name)
        return widget

    def signal_autoconnect(self, instance_or_dict):
        # Вместо прямого self.builder.connect_signals(instance_or_dict):
        proxy = _SignalProxy(instance_or_dict)
        self.builder.connect_signals(proxy)

    def __getitem__(self, name):
        return self.get_widget(name)