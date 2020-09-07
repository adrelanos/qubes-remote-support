Name:		qubes-remote-support-receiver-dom0
Version: @VERSION@
Release: @REL@%{?dist}

Summary:	Qubes Remote Support Receiver
Group:	Applications/System
License:	GPL
URL:		https://www.qubes-os.org/doc/remote-support/

Requires: torsocks socat openssh-server x2goserver

Source0: %{name}-%{version}.tar.gz

%description
Scripts to easily receive remote support using Qubes OS.

%prep
%setup -q

%install
mkdir $RPM_BUILD_ROOT/usr
cp -a bin $RPM_BUILD_ROOT/usr/

%files
/usr/bin/qubes-remote-support-receiver-start
/usr/bin/qubes-remote-support-receiver-stop
/usr/bin/qubes-remote-support-receiver-status
/usr/bin/qubes-remote-support-receiver-wormhole-helper

%changelog
@CHANGELOG@
