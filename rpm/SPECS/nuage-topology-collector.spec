Name:       nuage-topology-collector
Version:    %{version}
Release:    %{release}
Summary:    Nuage Topology Collector

License:    ASL 2.0
URL:        http://nuagenetworks.net
Vendor:     Nuage Networks
Source0:    nuage-topology-collector-%{version}.tar.gz
BuildRoot:  %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:  noarch
Requires:   ansible >= 2.1.0

%description
Ansible playbooks collects the following information about interfaces on compute hosts:

* Neighbor LLDP connectivity information
* VF port PCI information for the interface

The output of the code is a JSON report.

%prep
%setup -q

%build
if [[ -d %{buildroot} ]];then rm -rf %{buildroot};fi
mkdir -p  %{buildroot}

%install
mkdir -p %{buildroot}/opt/nuage/topology-collector
cp -rf * %{buildroot}/opt/nuage/topology-collector

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/opt/nuage/topology-collector
