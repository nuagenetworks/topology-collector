set -e

PACKAGE_NAME="nuage-topology-collector"

DEBEMAIL="Nuage Networks <info@nuagenetworks.net>" dch -b --newversion \
    1:${NUAGE_PROJECT}.${NUAGE_BUILD_RELEASE}-${NUAGE_BUILD_NUMBER} "Jenkins build" --distribution $(lsb_release --codename --short)

debuild -d -i -us -uc -b -kinfo@nuagenetworks.net

mv ../${PACKAGE_NAME}* .

if [ -n "$BUILD_NAME" ]
then
    dpkg-sig -k 83496517 -s builder ${PACKAGE_NAME}_*.changes
fi
