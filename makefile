MAKEFILEPREFIX = /var/www

install: install_systemd 
	mkdir -p $(DESTDIR)$(PREFIX)/www-repo-gui
	rsync -rupE ./src $(DESTDIR)$(PREFIX)/www-repo-gui

install_systemd:
	rsync -rupE ./service $(DESTDIR)/etc/systemd/system

uninstall_systemd: 
	rm -f $(DESTDIR)/etc/systemd/system/iot-dev-hub.service	

uninstall: uninstall_systemd
	rm -fr $(DESTDIR)$(PREFIX)/www-repo-gui

clean: uninstall_systemd
	rm -fr $(DESTDIR)$(PREFIX)/www-repo-gui
