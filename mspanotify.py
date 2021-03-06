#!/usr/bin/env python3

import os
import random
import sys
import re
import webbrowser

_reqmissing = []
_optmissing = []
try:
    from gi.repository import GObject, Gtk, Gdk, AppIndicator3
    import feedparser
except ImportError as e:
    module = str(e)
    if module.startswith("No module named ") or module.startswith("cannot import name "):
        _reqmissing.append(module[module.rfind(" ") + 1:])
    else:
        print(e)
try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    import cairo
except ImportError as e:
    module = str(e)
    if module.startswith("No module named ") or module.startswith("cannot import name "):
        _optmissing.append(module[module.rfind(" ") + 1:])
    else:
        print(e)
if _reqmissing:
    print("ERROR: The following modules are required for "
          + sys.argv[0]
          + " to run and are missing on your system:")
    for m in reqmissing: print("* " + m)
    exit()

class Notifier(Gtk.Window):
    _macrosdir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "macros")

    def _animate(self):
        advance = self._it.advance(None)
        if advance:
            self._image.set_from_pixbuf(
                self._it.get_pixbuf().add_alpha(True, 213, 218, 240))
        delay = self._it.get_delay_time()
        if delay != -1:
            GObject.timeout_add(delay, self._animate)
        return False

    def __init__(self, sound, newpage):
        Gtk.Window.__init__(self, decorated = False, resizable = False)
        self.set_gravity(Gdk.Gravity.SOUTH_EAST)
        self._newpage = newpage
        self._sound = sound
        if self._sound:
            self._player = Gst.ElementFactory.make("playbin", None)
            fakesink = Gst.ElementFactory.make("fakesink", None)
            self._player.set_property("video-sink", fakesink)
            bus = self._player.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_message)
        box = Gtk.EventBox()
        box.set_visible_window(False)
        self.connect("button-press-event", self._on_click)
        macrosdir = self.__class__._macrosdir
        self._image = Gtk.Image.new_from_file(
            os.path.join(macrosdir, random.choice(
                tuple(f for f in os.listdir(macrosdir)
                      if f.lower()[f.rfind(".") + 1:]
                      in {"jpg", "jpeg", "png", "gif"}))))
        box.add(self._image)
        if self._image.get_storage_type() == Gtk.ImageType.PIXBUF:
            self._image.set_from_pixbuf(
                self._image.get_pixbuf().add_alpha(True, 213, 218, 240))
        elif self._image.get_storage_type() == Gtk.ImageType.ANIMATION:
            self._it = self._image.get_animation().get_iter(None)
            self._image.set_from_pixbuf(
                self._it.get_pixbuf().add_alpha(True, 213, 218, 240))
            delay = self._it.get_delay_time()
            if delay != -1:
                GObject.timeout_add(delay, self._animate)
        self.set_keep_above(True)
        self.connect("show", self._on_show)
        if "cairo" not in _optmissing:
            self.connect("draw", self._on_draw)
            self.set_app_paintable(True)
            colormap = self.get_screen().get_rgba_visual()
            self.set_visual(colormap)
        self.add(box)
        box.show_all()

    def _on_show(self, widget):
        screen = widget.get_screen()
        w, h = self.get_size()
        self.move(screen.get_width(), screen.get_height())
        if self._sound:
            macrosdir = self.__class__._macrosdir
            files = tuple(f for f in os.listdir(macrosdir)
                          if f.lower()[f.rfind(".") + 1:]
                          in {"wav", "mp3", "ogg"})
            self._player.set_property(
                "uri", "file://" + os.path.join(macrosdir,
                                                random.choice(files)))
            self._player.set_state(Gst.State.PLAYING)

    def _on_draw(self, widget, cr):
        cr.set_source_rgba(1, 1, 1, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

    def _on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self._player.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            self._player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)

    def _on_click(self, widget, event):
        if event.button == 1:
            webbrowser.open_new_tab("http://www.mspaintadventures.com/?s=6&p=" + self._newpage)
        self.hide()

class Indicator():
    def __init__(self):
        self._ind = AppIndicator3.Indicator.new_with_path(
            "mspanotify",
            "logo",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            os.path.dirname(os.path.realpath(__file__)))
        self._ind.set_attention_icon_full("logo2", ":o")
        self._ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        menu = Gtk.Menu()
        self._prefs = PrefsWindow()
        goto_page_item = Gtk.MenuItem("Open MSPA in browser")
        check_now_item = Gtk.MenuItem("Check now")
        fake_check_item = Gtk.MenuItem("Fake check")
        prefs_item = Gtk.MenuItem("Preferences")
        quit_item = Gtk.MenuItem("Quit")
        goto_page_item.connect("activate", self._goto_page_activate)
        check_now_item.connect("activate", self._manual_check)
        fake_check_item.connect("activate", self._fake_check)
        sep1 = Gtk.SeparatorMenuItem()
        prefs_item.connect("activate", lambda w: self._prefs.show())
        sep2 = Gtk.SeparatorMenuItem()
        quit_item.connect("activate", self._quit_activate)
        menu.append(goto_page_item)
        menu.append(check_now_item)
        menu.append(fake_check_item)
        menu.append(sep1)
        menu.append(prefs_item)
        menu.append(sep2)
        menu.append(quit_item)
        menu.show_all()
        self._ind.set_menu(menu)
        self._read_update_file()
        self._check()
        GObject.timeout_add_seconds(self._prefs.prefs["freq"], self._check)

    def _fake_check(self, widget):
        n = Notifier(self._prefs.prefs["sound"], self._lastupdate)
        n.show()

    def _manual_check(self, widget):
        temp = self._lastupdate
        self._check()
        if self._lastupdate >= temp:
            d = Gtk.MessageDialog(None,
                                  Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                  Gtk.MessageType.INFO,
                                  Gtk.ButtonsType.OK,
                                  "No new updates found.")
            d.run()
            d.destroy()

    def _check(self):
        feed = feedparser.parse("http://www.mspaintadventures.com/rss/rss.xml")
        regex = re.compile(
            r"http://www.mspaintadventures.com/\?s=([0-9]+)&p=([0-9]+)")
        matches = regex.match(feed.entries[0].link)
        storynum = matches.group(1)
        pagenum = matches.group(2)
        if int(pagenum) > int(self._lastupdate):
            self._write_update_file()
            self._ind.set_status(AppIndicator3.IndicatorStatus.ATTENTION)
            n = Notifier(self._prefs.prefs["sound"], int(self._lastupdate) + 1)
            n.show()
            self._lastupdate = pagenum
        return True

    def _goto_page_activate(self, widget):
        webbrowser.open_new_tab(
            "http://www.mspaintadventures.com/?s=6&p=" + self._lastupdate)
        self._ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    def _quit_activate(self, widget):
        self._write_update_file()
        Gtk.main_quit()

    def _write_update_file(self):
        with open(os.path.expanduser("~/.mspaupdate"), "w") as f:
            f.write(self._lastupdate)

    def _read_update_file(self):
        if not os.path.exists(os.path.expanduser("~/.mspaupdate")):
            self._lastupdate = "001901"
            self._write_update_file()
        with open(os.path.expanduser("~/.mspaupdate"), "r") as f:
            self._lastupdate = f.read()

class PrefsWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self,
                            title = "MSPANotify Preferences",
                            window_position = Gtk.WindowPosition.CENTER)
        self.prefs = { "freq": 600, "sound": True }
        vbox = Gtk.VBox()
        hbox1 = Gtk.HBox()
        hbox2 = Gtk.HBox()
        hbox3 = Gtk.HBox()
        freq_label = Gtk.Label("Update frequency (minutes): ")
        freq_spinner = Gtk.SpinButton()
        close_button = Gtk.Button("Close")
        freq_spinner.set_increments(5, 10)
        freq_spinner.set_range(10, 60)
        freq_spinner.connect("value-changed", self._freq_changed)
        sound_check = Gtk.CheckButton("Play sound")
        if "Gst" in _optmissing:
            self.prefs["sound"] = False
            sound_check.set_sensitive(False)
        sound_check.connect("toggled", self._sound_toggled)
        sound_check.set_active(self.prefs["sound"])
        close_button.connect("clicked", lambda w: self.hide())
        hbox1.add(freq_label)
        hbox1.add(freq_spinner)
        hbox2.add(close_button)
        hbox3.add(sound_check)
        vbox.add(hbox1)
        vbox.add(hbox3)
        vbox.add(hbox2)
        self.add(vbox)
        vbox.show_all()

    def _freq_changed(self, widget):
        self.prefs["freq"] = widget.get_value() * 60

    def _sound_toggled(self, widget):
        self.prefs["sound"] = widget.get_active()

if __name__ == "__main__":
    GObject.threads_init()
    if not "Gst" in _optmissing: Gst.init(None)
    Indicator()
    Gtk.main()
