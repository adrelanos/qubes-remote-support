# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2020 Marta Marczykowska-Górecka
#                               <marmarta@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program; if not, see <http://www.gnu.org/licenses/>.

# pylint: disable=wrong-import-position,import-error
import sys
import gi
import pkg_resources
import subprocess
import threading
import typing
import time

gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk, GObject  # isort:skip
from qubesadmin import Qubes


class RemoteSupportGUI(Gtk.Application):
    def __init__(self, **properties):
        super().__init__(**properties)

        self.qubes_app: Qubes = Qubes()

        self.set_application_id("org.qubes.qui.tray.RemoteSupport")
        self.register()

        # load objects
        self.builder: Gtk.Builder = Gtk.Builder()
        self.builder.add_from_file(pkg_resources.resource_filename(
            __name__, 'remote_gui.glade'))

        # ask window
        self.ask_window: AskWindow = AskWindow(
            self.builder, self.qubes_app, self)
        self.ask_window.ok_button.connect("clicked", self.start_remote)
        self.ask_window.cancel_button.connect("clicked", self.exit_app)

        # progress window
        self.progress_window: ProgressWindow = ProgressWindow(
            self.builder, self.qubes_app, self)
        self.progress_window.abort_button.connect("clicked", self.exit_app)

        # status icon
        self.status_icon: RemoteSupportIcon = RemoteSupportIcon(
            self.qubes_app, self.exit_app)

        self.start_process: typing.Optional[subprocess.Popen] = None
        self.current_window: typing.Optional[Gtk.Dialog] = None

        self.ask_window.ask_dialog.show()
        self.vm_name: typing.Optional[str] = None

        self.aborted = False

        Gtk.main()

    def exit_app(self, *_args):
        self.aborted = True
        self.progress_window.progress_dialog.close()
        self.ask_window.ask_dialog.close()

        Gtk.main_iteration()

        if self.start_process and not self.start_process.returncode:
            self.start_process.kill()
            try:
                subprocess.check_call(["qubes-remote-support-receiver-stop"])
            except subprocess.CalledProcessError:
                self.show_message(
                    title="Failed to exit Qubes Remote Support",
                    text="Unknown error occurred. You can run "
                         "qubes-remote-support-receiver-stop in dom0 "
                         "terminal to check detailed error log.",
                    is_error=True)

        Gtk.main_quit()

    def start_thread(self):
        self.start_process = subprocess.Popen(
            ["qubes-remote-support-receiver-start", self.vm_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        # handle crash here

        for line in self.start_process.stdout:
            line = line.decode().strip()
            if line.startswith('wormhole_code:'):
                wormcode = line[14:]
                self.progress_window.wormhole_label.set_text(wormcode)
                self.progress_window.progress_bar.set_fraction(1)
                self.progress_window.success_label.set_visible(True)
                break

        while True:
            if self.aborted:
                return
            self.start_process.poll()
            if self.start_process.returncode is None:
                continue
            if self.start_process.returncode == 0:
                GObject.idle_add(self.progress_window.progress_dialog.hide)
                GObject.idle_add(self.status_icon.enable_icon)
                GObject.idle_add(
                    self.show_message,
                    "Connection successful!",
                    "Remote connection established. Use tray icon to "
                         "terminate Qubes Remote Support Daemon when it's "
                         "no longer needed.",
                    False)
                return
            GObject.idle_add(self.progress_window.progress_dialog.hide)
            GObject.idle_add(
                self.show_message,
                "Connection error!",
                "Remote connection failed. Error code: {}".format(
                    self.start_process.returncode),
                False,
                self.exit_app)
            time.sleep(1)

    def progress_thread(self):
        while not self.progress_window.wormhole_label.get_text() and \
                not self.aborted:
            self.progress_window.progress_bar.pulse()
            time.sleep(0.5)

    def start_remote(self, *_args):
        self.ask_window.ask_dialog.hide()

        self.progress_window.progress_dialog.show()

        self.vm_name = self.ask_window.select_vm_combo.get_active_id()

        threading.Thread(target=self.start_thread).start()
        threading.Thread(target=self.progress_thread).start()

    def show_message(self, title=None, text=None, is_error=True, callback=None):
        if is_error:
            message_type = Gtk.MessageType.ERROR
        else:
            message_type = Gtk.MessageType.INFO

        dialog = Gtk.MessageDialog(
            None, 0, message_type, Gtk.ButtonsType.OK)
        dialog.set_title(title)
        dialog.set_markup(text)
        if callback is None:
            callback = (lambda *x: dialog.destroy())
        dialog.connect("response", callback)
        dialog.show()


class RemoteSupportIcon:
    def __init__(self, qubes_app, exit_callback):
        """
        Icon in tray.
        :param qubes_app: Qubes object
        :param exit_callback: function to use when user selects Exit from menu
        """
        self.qubes_app: Qubes = qubes_app
        self.exit_callback: typing.Callable[[], None] = exit_callback

        self.state: bool = False
        self.icon: Gtk.StatusIcon = Gtk.StatusIcon()
        self.icon.set_visible(False)
        self.icon.connect('button-press-event', self._show_menu)
        self.tray_menu: Gtk.Menu = Gtk.Menu()

    def enable_icon(self):
        self.icon.set_visible(True)
        self._update_state()

        GObject.timeout_add(15 * 1000, self._update_state)

    def _set_icon_state(self, state: bool):
        """
        Set status icon.
        :param state: True for connection established, False for connection down
        :return: None
        """
        if state:
            self.icon.set_from_icon_name('qubes-remote-on')
            self.icon.set_tooltip_markup(
                '<b>Qubes Remote Support</b>\n'
                'Remote Support access active.')
            self.state = True
        else:
            self.icon.set_from_icon_name('qubes-remote')
            self.icon.set_tooltip_markup(
                '<b>Qubes Remote Support</b>\n'
                'Remote Support access not active.')
            self.state = False

    def _update_state(self, *_args):
        try:
            subprocess.check_call(["qubes-remote-support-receiver-status"],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            self._set_icon_state(True)
        except subprocess.CalledProcessError:
            self._set_icon_state(False)

    def _show_menu(self, _unused, _event):
        self.tray_menu = Gtk.Menu()

        self._setup_menu()

        self.tray_menu.popup_at_pointer(None)  # use current event

    def _setup_menu(self):
        title_label = Gtk.Label(xalign=0)
        title_label.set_markup("<b>Qubes Remote Support</b>")
        title_menu_item = Gtk.MenuItem()
        title_menu_item.add(title_label)
        title_menu_item.set_sensitive(False)

        subtitle_label = Gtk.Label(xalign=0)
        if self.state:
            subtitle_label.set_markup(
                "Qubes Remote Support is currently connected.")
        else:
            subtitle_label.set_markup(
                "Qubes Remote Support is currently not connected.")
        subtitle_menu_item = Gtk.MenuItem()
        subtitle_menu_item.set_margin_left(10)
        subtitle_menu_item.add(subtitle_label)
        subtitle_menu_item.set_sensitive(False)

        run_label = Gtk.Label(xalign=0)
        run_label.set_text("Exit Qubes Remote Support")
        run_menu_item = Gtk.MenuItem()
        run_menu_item.set_margin_left(10)
        run_menu_item.add(run_label)
        run_menu_item.connect('activate', self.exit_callback)

        self.tray_menu.append(title_menu_item)
        self.tray_menu.append(subtitle_menu_item)
        self.tray_menu.append(run_menu_item)

        self.tray_menu.show_all()


class ProgressWindow:
    def __init__(self, builder, qubes_app, parent_app):
        self.builder: Gtk.Builder = builder
        self.qubes_app: Qubes = qubes_app
        self.parent_app: Gtk.Application = parent_app

        self.progress_dialog: Gtk.Dialog = \
            self.builder.get_object("progress_dialog")
        self.abort_button: Gtk.Button = \
            self.builder.get_object("abort_button_progress")
        self.in_progress_label: Gtk.Label = \
            self.builder.get_object("label_inprogess")
        self.progress_bar: Gtk.ProgressBar = \
            self.builder.get_object("progress_bar")
        self.success_label: Gtk.Label = \
            self.builder.get_object("label_success")
        self.wormhole_label: Gtk.Label = \
            self.builder.get_object("label_wormhole")

        self.progress_bar.set_fraction(0)
        self.progress_bar.set_pulse_step(0.4)

        self.success_label.set_visible(False)


class AskWindow:
    def __init__(self, builder, qubes_app, parent_app):
        self.builder: Gtk.Builder = builder
        self.qubes_app: Qubes = qubes_app
        self.parent_app: Gtk.Application = parent_app

        self.ask_dialog: Gtk.Dialog = self.builder.get_object("ask_dialog")
        self.ok_button: Gtk.Button = self.builder.get_object("ok_button")
        self.cancel_button: Gtk.Button = \
            self.builder.get_object("cancel_button")
        self.select_vm_combo: Gtk.ComboBox = \
            self.builder.get_object("select_vm_combo")
        self.sure_checkbox: Gtk.CheckButton = \
            self.builder.get_object("sure_checkbox")

        self._fill_vms()

        self._test_validity()

        self.select_vm_combo.connect("changed", self._test_validity)
        self.sure_checkbox.connect("toggled", self._test_validity)

    def _test_validity(self, *_args):
        self.ok_button.set_sensitive(
            self.sure_checkbox.get_active() and
            self.select_vm_combo.get_active_id())

    def _fill_vms(self):
        candidate_vm = self._guess_vm()

        for domain in self.qubes_app.domains:
            if getattr(domain, 'provides_network', False):
                self.select_vm_combo.append(str(domain), str(domain))

        if candidate_vm:
            self.select_vm_combo.set_active_id(candidate_vm)

    def _guess_vm(self):
        if 'sys-whonix' in self.qubes_app.domains and \
                getattr(self.qubes_app.domains['sys-whonix'],
                        'provides_network', False):
            return 'sys-whonix'

        domains_with_network = [domain for domain in self.qubes_app.domains
                                if getattr(
                domain, 'provides_network', False)]

        for domain in domains_with_network:
            if 'whonix' in str(domain) and 'sys' in str(domain):
                return str(domain)
            if 'whonix' in str(domain) and domain.klass != 'TemplateVM':
                return str(domain)


def main():
    app = RemoteSupportGUI()
    app.run()


if __name__ == '__main__':
    sys.exit(main())
