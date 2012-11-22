#!/usr/bin/env python3

fail = False
try:
	try:
		from gi.repository import GObject, Gtk, Gdk
	except ImportError:
		print("Requres gir1.2-gtk-3.0")
		fail = True
	try:
		import gi
		gi.require_version('Gst', '1.0')
		from gi.repository import Gst
	except ImportError:
		print("Requires gir1.2-gstreamer-1.0")
		fail = True
	try:
		from gi.repository import AppIndicator3
	except ImportError:
		print("Requires gir1.2-appindicator3-0.1")
		fail = True
except ImportError:
	print("Requires python3-gi")
	fail = True
try:
	import cairo
except ImportError:
	print("Requires python3-cairo")
	fail = True
try:
	import feedparser
except ImportError:
	print("Requires python3-feedparser")
	fail = True
import os
import random
import re
import webbrowser

macrosdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "macros")

class Notifier(Gtk.Window):
	def animate(self):
		self.image.set_from_pixbuf(self.it.get_pixbuf().add_alpha(True, 213, 218, 240))
		self.it.advance(None)
		GObject.timeout_add(self.it.get_delay_time(), self.animate)
		return False
	
	def __init__(self, sound):
		Gtk.Window.__init__(self, decorated = False, resizable = False)
		self.sound = sound
		if self.sound:
			self.player = Gst.ElementFactory.make("playbin", None)
			fakesink = Gst.ElementFactory.make("fakesink", None)
			self.player.set_property("video-sink", fakesink)
			bus = self.player.get_bus()
			bus.add_signal_watch()
			bus.connect("message", self.on_message)
		box = Gtk.EventBox()
		box.set_visible_window(False)
		box.connect("button-press-event", lambda w, e: self.hide())
		self.image = Gtk.Image.new_from_file(os.path.join(macrosdir, random.choice([f for f in os.listdir(macrosdir) if f.lower()[f.rfind(".") + 1:] in ("jpg", "jpeg", "png", "gif")])))
		box.add(self.image)
		if self.image.get_storage_type() == Gtk.ImageType.PIXBUF:
			self.image.set_from_pixbuf(self.image.get_pixbuf().add_alpha(True, 213, 218, 240))
		elif self.image.get_storage_type() == Gtk.ImageType.ANIMATION:
			anim = self.image.get_animation()
			self.it = anim.get_iter(None)
			self.image.set_from_pixbuf(self.it.get_pixbuf())
			GObject.timeout_add(self.it.get_delay_time(), self.animate)
		self.set_keep_above(True)
		self.connect("show", self.on_show)
		self.connect("draw", self.on_draw)
		self.set_app_paintable(True)
		self.add(box)
		box.show_all()
		colormap = self.get_screen().get_rgba_visual()
		self.set_visual(colormap);
	
	def on_show(self, widget):
		screen = widget.get_screen()
		w, h = self.get_size()
		self.move(screen.get_width() - w, screen.get_height() - h)
		if self.sound:
			self.player.set_property("uri", "file://" + os.path.join(macrosdir, random.choice([f for f in os.listdir(macrosdir) if f.lower()[f.rfind(".") + 1:] in ("wav", "mp3", "ogg")])))
			self.player.set_state(Gst.State.PLAYING)
	
	def on_draw(self, widget, cr):
		cr.set_source_rgba(1, 1, 1, 0)
		cr.set_operator(cairo.OPERATOR_SOURCE)
		cr.paint()
	
	def on_message(self, bus, message):
		t = message.type
		if t == Gst.MessageType.EOS:
			self.player.set_state(Gst.State.NULL)
		elif t == Gst.MessageType.ERROR:
			self.player.set_state(Gst.State.NULL)
			err, debug = message.parse_error()
			print("Error: %s" % err, debug)

class Indicator():
	def __init__(self):
		self.ind = AppIndicator3.Indicator.new_with_path("mspanotify", "logo", AppIndicator3.IndicatorCategory.APPLICATION_STATUS, os.path.dirname(os.path.realpath(__file__)))
		self.ind.set_attention_icon_full("logo2", ":o")
		self.ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
		menu = Gtk.Menu()
		self.prefs = PrefsWindow()
		goto_page_item = Gtk.MenuItem("Open MSPA in browser")
		check_now_item = Gtk.MenuItem("Check now")
		fake_check_item = Gtk.MenuItem("Fake check")
		prefs_item = Gtk.MenuItem("Preferences")
		quit_item = Gtk.MenuItem("Quit")
		goto_page_item.connect("activate", self.goto_page_activate)
		check_now_item.connect("activate", self.check)
		fake_check_item.connect("activate", self.fake_check)
		sep1 = Gtk.SeparatorMenuItem()
		prefs_item.connect("activate", lambda w: self.prefs.show())
		sep2 = Gtk.SeparatorMenuItem()
		quit_item.connect("activate", self.quit_activate)
		menu.append(goto_page_item)
		menu.append(check_now_item)
		menu.append(fake_check_item)
		menu.append(sep1)
		menu.append(prefs_item)
		menu.append(sep2)
		menu.append(quit_item)
		menu.show_all()
		self.ind.set_menu(menu)
		self.lastupdate = self.read_update_file()
		GObject.timeout_add_seconds(self.prefs.prefs["freq"], self.check, None)
	
	def fake_check(self, widget):
		n = Notifier(self.prefs.prefs["sound"])
		n.show()

	def check(self, widget):
		feed = feedparser.parse("http://www.mspaintadventures.com/rss/rss.xml")
		regex = re.compile(r"http://www.mspaintadventures.com/\?s=([0-9]+)&p=([0-9]+)")
		matches = regex.match(feed.entries[0].link)
		storynum = matches.group(1)
		pagenum = matches.group(2)
		if int(pagenum) > int(self.lastupdate):
			self.lastupdate = pagenum
			self.write_update_file(self.lastupdate)
			self.ind.set_status(AppIndicator3.IndicatorStatus.ATTENTION)
			n = Notifier(self.prefs.prefs["sound"])
			n.show()
	
	def goto_page_activate(self, widget):
		webbrowser.open_new_tab("http://www.mspaintadventures.com/?s=6&p=" + self.lastupdate)
		self.ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

	def quit_activate(self, widget):
		self.write_update_file(self.lastupdate)
		Gtk.main_quit()
	
	def write_update_file(self, lastupdatetime):
		with open(os.path.expanduser("~/.mspaupdate"), "w") as f:
			f.write(lastupdatetime)

	def read_update_file(self):
		if not os.path.exists(os.path.expanduser("~/.mspaupdate")):
			self.write_update_file("001901")
		with open(os.path.expanduser("~/.mspaupdate"), "r") as f:
			update = f.read()
		return update

class PrefsWindow(Gtk.Window):
	def __init__(self):
		Gtk.Window.__init__(self, title = "MSPANotify Preferences", window_position = Gtk.WindowPosition.CENTER)
		vbox = Gtk.VBox()
		hbox1 = Gtk.HBox()
		hbox2 = Gtk.HBox()
		hbox3 = Gtk.HBox()
		freq_label = Gtk.Label("Update frequency (minutes): ")
		freq_spinner = Gtk.SpinButton()
		close_button = Gtk.Button("Close")
		freq_spinner.set_increments(5, 10)
		freq_spinner.set_range(10, 60)
		freq_spinner.connect("value-changed", self.freq_changed)
		sound_check = Gtk.CheckButton("Play sound")
		sound_check.connect("toggled", self.sound_toggled)
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
		self.prefs = { "freq": 600, "sound": True }
		
	def freq_changed(self, widget):
		self.prefs["freq"] = widget.get_value() * 60
	
	def sound_toggled(self, widget):
		self.prefs["sound"] = widget.get_active()

if __name__ == "__main__" and fail == False:
	GObject.threads_init()
	Gst.init(None)
	Indicator()
	Gtk.main()

