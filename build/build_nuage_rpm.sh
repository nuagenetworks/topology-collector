#!/bin/bash
#
set -e

PKG_VERSION="${NUAGE_PROJECT}.${NUAGE_BUILD_RELEASE}"
PKG_RELEASE="${NUAGE_BUILD_NUMBER}"
###########Build Variables##########################
rpmbuild_dir="$(pwd)/rpm"

###########Build Functions##########################
setup_build_env() {
    for dir in "BUILD" "BUILDROOT" "RPMS" "SRPMS" "SOURCES" "SPECS"
    do
        rpmbuild_subdir="${rpmbuild_dir}/${dir}"
        [[ -d "${rpmbuild_subdir}" ]] || mkdir "${rpmbuild_subdir}"
    done
}

rename_topology_collector() {
    mv -T "nuage_topology_collector" \
        "nuage-topology-collector-${PKG_VERSION}"
}

create_build_src() {
    tar czvf \
        "${rpmbuild_dir}/SOURCES/nuage-topology-collector-${PKG_VERSION}.tar.gz" \
        "nuage-topology-collector-${PKG_VERSION}"
}

setup_build_env

rename_topology_collector

create_build_src

rpmbuild -ba \
    --define "_topdir ${rpmbuild_dir}" \
    --define "release ${PKG_RELEASE}" \
    --define "version ${PKG_VERSION}" \
    "${rpmbuild_dir}/SPECS/nuage-topology-collector.spec"
