# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HERE_RTTI_Archive_Miner
                                 A QGIS plugin
 This plugin can mapping gps traces and points to HERE RTTI Archive.
                             -------------------
        begin                : 2017-11-27
        copyright            : (C) 2017 by HERE Taiwan Limited Company
        email                : guan-ling.wu@here.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load HERE_RTTI_Archive_Miner class from file HERE_RTTI_Archive_Miner.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .here_rtti_archive_miner import HERE_RTTI_Archive_Miner
    return HERE_RTTI_Archive_Miner(iface)
