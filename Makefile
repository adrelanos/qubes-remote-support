install-dom0:
	install -m 775 -D qubes-remote-support-receiver-start $(DESTDIR)/usr/bin/qubes-remote-support-receiver-start
	install -m 775 -D qubes-remote-support-receiver-stop $(DESTDIR)/usr/bin/qubes-remote-support-receiver-stop
	install -m 775 -D qubes-remote-support-receiver-status $(DESTDIR)/usr/bin/qubes-remote-support-receiver-status
	install -m 775 -D qubes-remote-support-receiver-wormhole-helper $(DESTDIR)/usr/bin/qubes-remote-support-receiver-wormhole-helper

clean:
	rm -rf pkgs
