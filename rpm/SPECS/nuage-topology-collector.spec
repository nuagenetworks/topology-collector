# Macros for py2/py3 compatibility
%if 0%{?fedora} || 0%{?rhel} > 7
%global pyver %{python3_pkgversion}
%else
%global pyver 2
%endif
# End of macros for py2/py3 compatibility

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
Requires:   python%{pyver}-keystoneauth1 >= 3.4.0
Requires:   python%{pyver}-neutronclient  >= 6.3.0
Requires:   python%{pyver}-novaclient >= 9.1.0
Requires:   python%{pyver}-ovsdbapp >= 0.8.0
# Handle python2 exception
%if %{pyver} == 2
Requires: python-construct >= 2.8.10
%else
Requires: python%{pyver}-construct >= 2.8.10
%endif

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
mkdir -p %{buildroot}/opt/nuage/topology-collector/nuage_topology_collector
cp -rf * %{buildroot}/opt/nuage/topology-collector/nuage_topology_collector

%clean
rm -rf %{buildroot}

%files
%defattr(755,stack,stack,-)
/opt/nuage/topology-collector/nuage_topology_collector
