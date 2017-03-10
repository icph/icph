MAKEFILEPREFIX = /var/www

install: install_systemd 
	mkdir -p $(DESTDIR)$(PREFIX)/www-repo-gui
	rsync -rupE ./src $(DESTDIR)$(PREFIX)/www-repo-gui

install_systemd:
	cp ./service/iot-dev-hub.service /etc/systemd/system
	systemctl enable /etc/systemd/system/iot-dev-hub.service
	systemctl start iot-dev-hub.service

uninstall_systemd: 
	systemctl stop iot-dev-hub.service
	systemctl disable iot-dev-hub.service
	rm /etc/systemd/system/iot-dev-hub.service	

uninstall: uninstall_systemd
	rm -fr $(DESTDIR)$(PREFIX)/www-repo-gui

clean: uninstall_systemd
	rm -fr $(DESTDIR)$(PREFIX)/www-repo-gui
