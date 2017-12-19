# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HERE_RTTI_Archive_Miner
                                 A QGIS plugin
 This plugin can mapping gps traces and points to HERE RTTI Archive.
                              -------------------
        begin                : 2017-11-27
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Guan Ling Wu
        email                : guan-ling.wu@here.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import datetime
import json
import math
import os.path
import sqlite3

import requests
# Initialize Qt resources from file resources.py
from PyQt4 import QtCore
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QProgressBar, QDockWidget
from qgis.core import *
from qgis.gui import QgsMessageBar
from urllib.request import urlretrieve

# Import the code for the dialog
from here_rtti_archive_miner_dialog import HERE_RTTI_Archive_MinerDialog


def resolve(name, basepath=None):
    if not basepath:
        basepath = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(basepath, name)


class HERE_RTTI_Archive_Miner:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'HERE_RTTI_Archive_Miner_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&HERE_RTTI_Archive_Miner')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'HERE_RTTI_Archive_Miner')
        self.toolbar.setObjectName(u'HERE_RTTI_Archive_Miner')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('HERE_RTTI_Archive_Miner', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = HERE_RTTI_Archive_MinerDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/HERE_RTTI_Archive_Miner/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Mapping GPS trace to Traffic Archive'),
            callback=self.run,
            parent=self.iface.mainWindow())
        init_config_path = './here_rtti_miner_config.ini'
        if os.path.exists(init_config_path):
            init_config = open(init_config_path, mode='r')
            f = init_config.readlines()
            if len(f) == 3:
                self.iface.messageBar().pushMessage("Info", '{}\\here_rtti_miner_config.ini loaded.'.format(
                    os.path.abspath(os.path.curdir)), level=QgsMessageBar.INFO, duration=1)
                app_id = (f[0].replace('\n', ''))
                self.dlg.app_id_textbox.setPlainText(app_id)
                app_code = (f[1].replace('\n', ''))
                self.dlg.app_code_textbox.setPlainText(app_code)
                archive_path = (f[2].replace('\n', ''))
                self.dlg.archive_textbox.setPlainText(archive_path)

        """Checkbox Listener"""
        self.cb = self.dlg.date_time_override_checkBox
        self.cb.toggle()
        self.cb.setChecked(False)
        self.dlg.connect(self.cb, QtCore.SIGNAL('stateChanged(int)'), self.change_state)

        """DTM preload"""
        self.dtm = self.dlg.dateTimeEdit
        # get current date and time
        now = QtCore.QDateTime.currentDateTime()
        # set current date and time to the object
        self.dtm.setDateTime(now)

    def override_dtm(self):
        self.dtm = self.dlg.dateTimeEdit
        target_current_second = self.dtm.dateTime().toMSecsSinceEpoch() / 1000
        return target_current_second

    def change_state(self):
        if self.cb.isChecked():
            dtm_override_enabled = True
        else:
            dtm_override_enabled = False
        return dtm_override_enabled

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&HERE_RTTI_Archive_Miner'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def select_output_file(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ", "", '*.csv')
        self.dlg.lineEdit.setText(filename)

    def rad(self, d):
        return d * math.pi / 180.0

    def distance(self, lat1, lng1, lat2, lng2):
        radlat1 = self.rad(lat1)
        radlat2 = self.rad(lat2)
        a = radlat1 - radlat2
        b = self.rad(lng1) - self.rad(lng2)
        s = 2 * math.asin(
            math.sqrt(
                math.pow(math.sin(a / 2), 2) + math.cos(radlat1) * math.cos(radlat2) * math.pow(math.sin(b / 2), 2)))
        earth_radius = 6378.137
        s = s * earth_radius
        if s < 0:
            return -s
        else:
            return s

    def mia_image(self, app_id, app_code):
        map_language = 'cht'
        mia_url = 'http://image.maps.cit.api.here.com/mia/1.6/mapview?app_id={}&app_code={}&nomrk&f=0&nocrop&t=&bbox={},{},{},{}&h={}&w={}'.format(
            app_id, app_code, self.iface.mapCanvas().extent().yMaximum(), self.iface.mapCanvas().extent().xMaximum(),
            self.iface.mapCanvas().extent().yMinimum(), self.iface.mapCanvas().extent().xMinimum(),
            self.iface.mapCanvas().size().height(), self.iface.mapCanvas().size().width())
        pic_file_name = "mia.png"
        local_file_name, headers = urlretrieve(mia_url, pic_file_name)
        lat_min = float(headers.get('Viewport-Bottom-Left').split(', ')[0].split(' ')[1])
        lon_min = float(headers.get('Viewport-Bottom-Left').split(', ')[1].split(' ')[1])
        lat_max = float(headers.get('Viewport-Top-Right').split(', ')[0].split(' ')[1])
        lon_max = float(headers.get('Viewport-Top-Right').split(', ')[1].split(' ')[1])
        world_file_name = pic_file_name.split('.')[0] + '.wld'
        wld = open(world_file_name, mode='w')
        wld.write('{}\n{}\n{}\n{}\n{}\n{}'.format(
            format((lon_max - lon_min) / self.iface.mapCanvas().size().width(), '.32f'), 0, 0,
            format((lat_min - lat_max) / self.iface.mapCanvas().size().height(), '.32f'), format(lon_min, '.32f'),
            format(lat_max, '.32f')))
        wld.close()
        mia_existed = False
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer in layers:
            if layer.name() == "mia":
                QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
        mia = self.iface.addRasterLayer(pic_file_name, 'mia')
        order = self.iface.layerTreeCanvasBridge().customLayerOrder()
        order.insert(-1, order.pop(order.index(mia.id())))
        self.iface.layerTreeCanvasBridge().setCustomLayerOrder(order)
        self.iface.layerTreeCanvasBridge().setHasCustomLayerOrder(True)

    def rme_result_parsing(self, input_file_name, file_type, rme_result):
        conn = sqlite3.connect(input_file_name + '.sqlite')
        cursor = conn.cursor()
        create_route_links = "CREATE TABLE IF NOT EXISTS route_links (file_name varchar(255),link_id int,route_direction varchar(1),shape varchar(65535),functional_class int, confidence float, link_length float, m_sec_to_reach_link_from_start float, tmcs varchar(32))"
        create_trace_point = "CREATE TABLE IF NOT EXISTS trace_points (file_name varchar(255),file_type varchar(255),timestamp int, year int, month int, day int, hour int, minute int, second float, link_id_matched int,lat float,lon float,lat_matched float,lon_matched float,heading_matched float,speed_mps float,speed_kph float)"
        create_warnings = "CREATE TABLE IF NOT EXISTS warnings (user_id varchar(255), file_name varchar(255), route_link_seq_num int, trace_point_seq_num int, category int, text varchar(255))"
        cursor.execute(create_route_links)
        cursor.execute(create_trace_point)
        cursor.execute(create_warnings)
        file_name = input_file_name
        file_type = file_type
        route_links = rme_result.get('RouteLinks')
        if len(route_links) == 0:
            self.iface.messageBar().pushMessage("Error", 'No route link returned from HERE RME with your GPS log!',
                                                level=QgsMessageBar.CRITICAL)
        trace_points = rme_result.get('TracePoints')
        warnings = rme_result.get('Warnings')
        rme_link_id_results = []
        if rme_result.get('RouteLinks'):
            if len(rme_result.get('RouteLinks')) > 0:
                for route_link in route_links:
                    shape = route_link['shape']
                    link_id = route_link['linkId']
                    rme_link_id_results.append(str(link_id))
                    if int(link_id) > 0:
                        route_direction = 'f'
                    else:
                        route_direction = 't'
                    functional_class = route_link['functionalClass']
                    confidence = route_link['confidence']
                    link_length = route_link['linkLength']
                    m_sec_to_reach_link_from_start = route_link['mSecToReachLinkFromStart']
                    if route_link.get('attributes'):
                        attributes = list(route_link.get('attributes').values())[0][0]
                        tmcs = attributes.get('TMCS').replace('[', '').replace(']', '').replace(' ', '')
                    else:
                        tmcs = ''
                    route_links_insert_data = "insert into route_links values ('{}',{},'{}','{}','{}',{},{},{},'{}')".format(
                        file_name, link_id, route_direction, shape, functional_class, confidence, link_length,
                        m_sec_to_reach_link_from_start, tmcs)
                    cursor.execute(route_links_insert_data)
        if rme_result.get('TracePoints'):
            if len(rme_result.get('TracePoints')) > 0:
                target_dtm = self.override_dtm()
                i = 0
                while i < len(trace_points):
                    if i < len(trace_points) - 1:
                        time_inverval = trace_points[i + 1]['timestamp'] - trace_points[i]['timestamp']
                    else:
                        time_inverval = trace_points[i]['timestamp'] - trace_points[i - 1]['timestamp']
                    trace_point = trace_points[i]
                    # for trace_point in trace_points:
                    if self.change_state() and i == 0:
                        dtm_delta = int(int(trace_point['timestamp']) - target_dtm * 1000)
                    elif self.change_state() and i > 0:
                        target_dtm += time_inverval / 1000
                        dtm_delta = int(int(trace_point['timestamp']) - (target_dtm * 1000))
                    elif not self.change_state():
                        dtm_delta = 0
                    timestamp = trace_point['timestamp'] - dtm_delta
                    timestamp_isoformat = datetime.datetime.utcfromtimestamp(timestamp / 1000)
                    year = timestamp_isoformat.year
                    month = timestamp_isoformat.month
                    day = timestamp_isoformat.day
                    hour = timestamp_isoformat.hour
                    minute = timestamp_isoformat.minute
                    second = timestamp_isoformat.second
                    lat = trace_point['lat']
                    lon = trace_point['lon']
                    lat_matched = trace_point['latMatched']
                    lon_matched = trace_point['lonMatched']
                    link_id_matched = trace_point['linkIdMatched']
                    heading_matched = trace_point['headingMatched']
                    speed_mps = trace_point['speedMps']
                    if i > 0 and speed_mps == 0.0:
                        speed_mps = float(self.distance(trace_points[i]['latMatched'], trace_points[i]['lonMatched'],
                                                        trace_points[i - 1]['latMatched'],
                                                        trace_points[i - 1]['lonMatched']) * 1000) / (
                                            ((trace_points[i]['timestamp'] - dtm_delta) - (
                                                    trace_points[i - 1]['timestamp'] - dtm_delta)) / 1000)
                    speed_kph = float(speed_mps) * 3.6
                    trace_points_insert_data = "insert into trace_points values ('{}','{}','{}',{},{},{},{},{},{},{},{},{},{},{},{},'{}','{}')".format(
                        file_name, file_type, timestamp, year, month, day, hour, minute, second, link_id_matched, lat,
                        lon, lat_matched, lon_matched, heading_matched, speed_mps, speed_kph)
                    cursor.execute(trace_points_insert_data)
                    i += 1
        if rme_result.get('Warnings'):
            if len(rme_result.get('Warnings')) > 0:
                for warning in warnings:
                    route_link_seq_num = warning.get('routeLinkSeqNum')
                    trace_point_seq_num = warning.get('tracePointSeqNum')
                    category = warning.get('category')
                    text = warning.get('text')
                    if int(route_link_seq_num) > 0 and int(trace_point_seq_num) > 0:
                        warnings_insert_data_sql = "insert into warnings values ('{}','{}','{}','{}','{}')".format(
                            file_name, route_link_seq_num, trace_point_seq_num, category, text)
                        cursor.execute(warnings_insert_data_sql)
        conn.commit()
        conn.close()
        return input_file_name + '.sqlite'

    def here_rtti_mapping(self, source_file, rme_result_db):
        print('Start mapping to RTTI archive...')
        output_csv = open('{}.csv'.format(source_file), mode='w')
        output_csv.write(
            'year,month,day,hour,minute,second,lat_matched,lon_matched,link_id,route_direction,queue_direction,heading,gps_speed,tmc,rtti_speed,rtti_speed_uncapped,rtti_free_flow,rtti_jam_factor,rtti_confidence,ss_speed,ss_speed_uncapped,ss_free_flow,ss_jam_factor\n')
        conn = sqlite3.connect(rme_result_db)
        cursor = conn.cursor()
        trace_query = "select distinct year, month, day, hour, minute, second, lat_matched, lon_matched, link_id_matched, route_direction, heading_matched, speed_kph, tmcs " \
                      "from trace_points inner join route_links on trace_points.link_id_matched = route_links.link_id"
        cursor.execute(trace_query)
        results = list(cursor.fetchall())
        # clear the message bar
        self.iface.messageBar().clearWidgets()
        # set a new message bar
        progressMessageBar = self.iface.messageBar()
        progress = QProgressBar()
        # Maximum is set to 100, making it easy to work with percentage of completion
        progress.setMaximum(len(results))
        # pass the progress bar to the message Bar
        progressMessageBar.pushWidget(progress)
        i = 0
        while i < len(results):
            year = results[i][0]
            month = results[i][1]
            day = results[i][2]
            hour = results[i][3]
            minute = results[i][4]
            second = results[i][5]
            lat_matched = results[i][6]
            lon_matched = results[i][7]
            link_id = results[i][8]
            route_direction = results[i][9]
            heading = results[i][10]
            speed_kph = results[i][11]
            rtti_archive_db = '{}\\{}_{}_{}_{}.sqlite'.format(self.archive_path, year, month, day, hour)
            if os.path.exists(rtti_archive_db):
                rtti_conn = sqlite3.connect(rtti_archive_db)
            else:
                print('Unable to find corresponding HERE RTTI archive database.')
                i += 1
                continue
            if len(results[i][12]) > 0:
                tmcs = results[i][12].split(',')
                for tmc in tmcs:
                    tmc_ebu_country_code = tmc[0]
                    if tmc.find('+') > 0:
                        separator = '+'
                        queue_direction = '+'
                    elif tmc.find('-') > 0:
                        separator = '-'
                        queue_direction = '-'
                    elif tmc.find('P') > 0:
                        separator = 'P'
                        queue_direction = '+'
                    elif tmc.find('N') > 0:
                        separator = 'N'
                        queue_direction = '-'
                    location_code = tmc.split(separator)[1][:-1]
                    tmc_table_id = tmc.split(separator)[0][1:]
                    query_rtti_tmc_sql = "select speed, speed_uncapped, free_flow, jam_factor, confidence, ss_length, ss_speed, ss_speed_uncapped, ss_free_flow, ss_jam_factor from tmc where year = {} and month = {} and day = {} and hour = {} and minute = {} " \
                                         "and tmc_ebu_country_code = '{}' and tmc_table_id = {} and place_code = {} and queue_direction = '{}'".format(
                        year, month, day, hour, minute, tmc_ebu_country_code, tmc_table_id, location_code,
                        queue_direction)
                    tmc_result = rtti_conn.execute(query_rtti_tmc_sql).fetchall()
                    tmc_output_format = '{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n'.format(year, month, day, hour,
                                                                                                minute,
                                                                                                second, lat_matched,
                                                                                                lon_matched, link_id,
                                                                                                route_direction,
                                                                                                queue_direction,
                                                                                                heading,
                                                                                                speed_kph, tmc, {})
                    tmc_message_format = 'Record-{} --> link_id: {} found in location table: {}{}/location code: {} ({}) {}'.format(
                        i, link_id, tmc_ebu_country_code, tmc_table_id, location_code, rtti_archive_db, {})
                    if len(tmc_result) > 0:
                        if tmc.find(route_direction.upper()) > 0:
                            print(tmc_message_format.format(' --> RTTI retrieved'))
                            output_csv.write(tmc_output_format.format(','.join(str(elem) for elem in tmc_result[0])))
                        else:
                            print(
                                tmc_message_format.format(
                                    ' --> unable to retrieve RTTI, potentially illegal maneuver.'))
                    else:
                        print(tmc_message_format.format(''))
                        output_csv.write(tmc_output_format.format(''))
            else:
                query_rtti_shp_sql = "select speed, speed_uncapped, free_flow, jam_factor, confidence from shp where year = {} and month = {} and day = {} and hour = {} and minute = {} " \
                                     "and link_id = '{}'".format(year, month, day, hour, minute,
                                                                 (str(abs(link_id)) + route_direction.upper()))
                shp_result = rtti_conn.execute(query_rtti_shp_sql).fetchall()

                shp_output_format = '{},{},{},{},{},{},{},{},,{},{},{},{},{}\n'.format(year, month, day, hour, minute,
                                                                                       second,
                                                                                       lat_matched, lon_matched,
                                                                                       route_direction,
                                                                                       '', heading, speed_kph, '', {})
                if len(shp_result) > 0:
                    print('Record-{} --> link_id: {} found in DLR coverage'.format(i, link_id))
                    output_csv.write(shp_output_format.format(','.join(str(elem) for elem in shp_result[0])))
                else:
                    print('Record-{} --> link_id: {} has no TMC or DLR coverage.'.format(i, link_id))
                    output_csv.write(shp_output_format.format(''))
            progress.setValue(i)
            i += 1
        self.iface.messageBar().clearWidgets()
        output_csv.close()
        print('{}.csv'.format(source_file))
        self.iface.messageBar().pushMessage("Info", 'Task completed.', level=QgsMessageBar.INFO, duration=10)
        return '{}.csv'.format(source_file)

    def run(self):

        """Run method that performs all the real work"""
        self.iface.actionShowPythonDialog().trigger()
        python_console = self.iface.mainWindow().findChild(QDockWidget, 'PythonConsole')
        if not python_console.isVisible():
            python_console.setVisible(True)
        layers = self.iface.legendInterface().layers()
        layer_list = []
        for layer in layers:
            layer_list.append(layer.name())
        self.dlg.trace_file_list.addItems(layer_list)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            f = open('./here_rtti_miner_config.ini', mode='w')
            app_id = self.dlg.app_id_textbox.toPlainText()
            f.write(app_id + '\n')
            app_code = self.dlg.app_code_textbox.toPlainText()
            f.write(app_code + '\n')
            archive_path = self.dlg.archive_textbox.toPlainText()
            f.write(archive_path + '\n')
            f.close()

            """Getting Source Of Target Layer"""
            self.app_id = self.dlg.app_id_textbox.toPlainText()
            self.app_code = self.dlg.app_code_textbox.toPlainText()
            self.archive_path = self.dlg.archive_textbox.toPlainText()
            selected_layer_index = self.dlg.trace_file_list.currentIndex()
            self.mia_image(self.app_id, self.app_code)
            def mia_autorefresh():
                self.mia_image(self.app_id, self.app_code)
            self.mia_image(self.app_id, self.app_code)
            self.iface.mapCanvas().extentsChanged.connect(mia_autorefresh)
            if selected_layer_index >= 0:
                selected_layer = layers[selected_layer_index]
                selected_layer_source = selected_layer.source()
                selected_layer_source_file = selected_layer_source.split('|')[0]
                selected_layer_source_file_type = selected_layer_source_file.split('.')[-1].upper()

                """Accessing HERE Route Match Extension"""
                print('Calling HERE RME...')
                app_id = self.dlg.app_id_textbox.toPlainText()
                app_code = self.dlg.app_code_textbox.toPlainText()
                rme_url = 'http://rme.cit.api.here.com/2/matchroute.json?routemode=car&access,gate,oneway,thrutraf,turn&filetype={}&app_id={}&app_code={}&attributes=LINK_TMC_FC1(*),LINK_TMC_FC2(*),LINK_TMC_FC3(*),LINK_TMC_FC4(*),LINK_TMC_FC5(*)'.format(
                    selected_layer_source_file_type, app_id, app_code)
                payload = open(selected_layer_source_file, mode='r').read()
                r = requests.post(rme_url, data=payload)
                r.encoding = 'utf-8'
                rme_result = json.loads(r.text)
                print('RMC result captured.\nStart Parsing...')
                rme_result_db = self.rme_result_parsing(selected_layer_source_file,
                                                        selected_layer_source_file_type.upper(), rme_result)
                output_result = self.here_rtti_mapping(selected_layer_source_file, rme_result_db)
                print('Opening results.')
                uri = 'file:///{}?delimiter={}&xField={}&yField={}'.format(output_result.replace('\\', '/'), ',',
                                                                           'lon_matched', 'lat_matched')
                vlayer = QgsVectorLayer(uri, 'output_result', "delimitedtext")
                QgsMapLayerRegistry.instance().addMapLayer(vlayer)
                vlayer.loadNamedStyle(resolve('render_result.qml'))
                order = self.iface.layerTreeCanvasBridge().customLayerOrder()
                order.insert(0, order.pop(order.index(vlayer.id())))
                self.iface.layerTreeCanvasBridge().setCustomLayerOrder(order)
                self.iface.layerTreeCanvasBridge().setHasCustomLayerOrder(True)
                print('Results opened.')
            else:
                self.iface.messageBar().pushMessage("Error",
                                                    'GPS trace is not loaded, please load GPS trace in GPX/KML/NMEA/CSV format.',
                                                    level=QgsMessageBar.CRITICAL)
