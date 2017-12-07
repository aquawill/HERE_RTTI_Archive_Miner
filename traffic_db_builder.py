import datetime
import gzip
import sqlite3
import xml.etree.ElementTree as ET

import requests
from retrying import retry
import sys

rtti_url = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

@retry
def mlrealtime_downloader(rtti_url):
    now = datetime.datetime.now().isoformat()
    print('{} downloading: {}'.format(now, rtti_url))
    r = gzip.decompress(requests.get(rtti_url, auth=(username, password)).content).decode('utf-8')
    return r


def mlrealtime_parser():
    # mlrealtime = open('RealtimeFlowF1D10.xml', mode='r', encoding='utf-8').read()
    # filename = 'RealtimeFlowF1D10'
    mlrealtime = mlrealtime_downloader(rtti_url)
    mlrealtime_xml = ET.fromstring(mlrealtime)
    tmc_map_version = mlrealtime_xml.get('MAP_VERSION')
    tmc_units = mlrealtime_xml.get('UNITS')
    tmc_feed_version = mlrealtime_xml.get('VERSION')
    tmc_created_timestamp = mlrealtime_xml.get('CREATED_TIMESTAMP')
    tmc_table_version = mlrealtime_xml.get('TMC_TABLE_VERSION')
    xmlns = mlrealtime_xml.tag[0:mlrealtime_xml.tag.find('}') + 1]

    timestamp_tuple = datetime.datetime.strptime(tmc_created_timestamp, "%Y-%m-%dT%H:%M:%SZ")
    year = timestamp_tuple.year
    month = timestamp_tuple.month
    day = timestamp_tuple.day
    hour = timestamp_tuple.hour
    minute = timestamp_tuple.minute
    second = timestamp_tuple.second

    now = datetime.datetime.now().isoformat()
    print('{} opening: {}_{}_{}_{}.sqlite'.format(now, year, month, day, hour))

    conn = sqlite3.connect('{}_{}_{}_{}.sqlite'.format(year, month, day, hour))
    cursor = conn.cursor()
    create_tmc = "CREATE TABLE IF NOT EXISTS tmc (year int, month int, day int, hour int, minute int, second int, tmc_created_timestamp varchar(32),tmc_map_version int,tmc_units varchar(16),tmc_feed_version varchar(8),tmc_table_version float,tmc_ebu_country_code varchar(4),tmc_extended_country_code varchar(4),tmc_table_id varchar(4),roadway_id varchar(16),roadway_description varchar(255),place_code int,place_description varchar(255),queue_direction char(1),length float,type char(2),speed float,speed_uncapped float,free_flow float,jam_factor float,confidence float,traversability_status char(1),ss_length float,ss_speed float,ss_speed_uncapped float,ss_free_flow float,ss_jam_factor float,ss_traversability_status char(1))"
    create_shp = "CREATE TABLE IF NOT EXISTS shp (year int, month int, day int, hour int, minute int, second int, tmc_created_timestamp varchar(32),tmc_map_version int,tmc_units varchar(16),tmc_feed_version varchar(8),tmc_table_version float,tmc_ebu_country_code varchar(4),tmc_extended_country_code varchar(4),tmc_table_id varchar(4),functional_class int,link_id varchar(16),length float,form_of_way varchar(8),shape varchar(512),type char(2),speed float,speed_uncapped float,free_flow float,jam_factor float,confidence float)"
    cursor.execute(create_tmc)
    cursor.execute(create_shp)


    for child in mlrealtime_xml:
        if child.get('TY') == 'TMC':
            rws_tmc = child
            tmc_ebu_country_code = rws_tmc.get('EBU_COUNTRY_CODE')
            tmc_extended_country_code = rws_tmc.get('EXTENDED_COUNTRY_CODE')
            tmc_table_id = rws_tmc.get('TABLE_ID')
            for rw in rws_tmc:
                tmc_rw = rw.attrib
                roadway_id = tmc_rw.get('LI')
                roadway_description = tmc_rw.get('DE')
                ss_list = []
                for fis in rw:
                    for fi in fis:
                        for child in fi:
                            if child.tag == xmlns + 'TMC':
                                tmc_rw_fi_tmc = child
                                place_code = tmc_rw_fi_tmc.get('PC')
                                place_description = tmc_rw_fi_tmc.get('DE')
                                queue_direction = tmc_rw_fi_tmc.get('QD')
                                length = tmc_rw_fi_tmc.get('LE')
                            if child.tag == xmlns + 'CF':
                                tmc_rw_fi_cf = child
                                type = tmc_rw_fi_cf.get('TY')
                                speed = tmc_rw_fi_cf.get('SP')
                                speed_uncapped = tmc_rw_fi_cf.get('SU')
                                free_flow = tmc_rw_fi_cf.get('FF')
                                jam_factor = tmc_rw_fi_cf.get('JF')
                                confidence = tmc_rw_fi_cf.get('CN')
                                traversability_status = tmc_rw_fi_cf.get('TS')
                                if len(tmc_rw_fi_cf) > 0:
                                    for sss in tmc_rw_fi_cf:
                                        for ss in sss:
                                            ss_length = ss.get('LE')
                                            ss_speed = ss.get('SP')
                                            ss_speed_uncapped = ss.get('SU')
                                            ss_free_flow = ss.get('FF')
                                            ss_jam_factor = ss.get('JF')
                                            ss_traversability_status = ss.get('TS')
                                            ss_list.append(
                                                [ss_length, ss_speed, ss_speed_uncapped, ss_free_flow, ss_jam_factor,
                                                 ss_traversability_status])
                                else:
                                    ss_list = [[]]
                                for ss in ss_list:
                                    if len(ss) > 0:
                                        ss_length = ss[0]
                                        ss_speed = ss[1]
                                        ss_speed_uncapped = ss[2]
                                        ss_free_flow = ss[3]
                                        ss_jam_factor = ss[4]
                                        ss_traversability_status = ss[5]
                                        tmc_sql = "insert into tmc values ({},{},{},{},{},{},'{}',{},'{}','{}',{},'{}','{}','{}','{}','{}',{},'{}','{}',{},'{}',{},{},{},{},{},'{}',{},{},{},{},{},'{}')".format(
                                            year, month, day, hour, minute, second, tmc_created_timestamp,
                                            tmc_map_version,
                                            tmc_units, tmc_feed_version, tmc_table_version, tmc_ebu_country_code,
                                            tmc_extended_country_code, tmc_table_id, roadway_id, roadway_description,
                                            place_code, place_description, queue_direction, length, type, speed,
                                            speed_uncapped, free_flow, jam_factor, confidence, traversability_status,
                                            ss_length, ss_speed, ss_speed_uncapped, ss_free_flow, ss_jam_factor,
                                            ss_traversability_status)
                                        cursor.execute(tmc_sql)
                                    else:
                                        tmc_sql = "insert into tmc values ({},{},{},{},{},{},'{}',{},'{}','{}',{},'{}','{}','{}','{}','{}',{},'{}','{}',{},'{}',{},{},{},{},{},'{}','','','','','','')".format(
                                            year, month, day, hour, minute, second, tmc_created_timestamp,
                                            tmc_map_version,
                                            tmc_units, tmc_feed_version, tmc_table_version, tmc_ebu_country_code,
                                            tmc_extended_country_code, tmc_table_id, roadway_id, roadway_description,
                                            place_code, place_description, queue_direction, length, type, speed,
                                            speed_uncapped, free_flow, jam_factor, confidence, traversability_status)
                                        cursor.execute(tmc_sql)
        if child.get('TY') == 'SHP':
            rws_shp = child
            shp_ebu_country_code = rws_shp.get('EBU_COUNTRY_CODE')
            shp_extended_country_code = rws_shp.get('EXTENDED_COUNTRY_CODE')
            shp_table_id = rws_shp.get('TABLE_ID')
            for rw in rws_shp:
                for fis in rw:
                    for fi in fis:
                        for fi_elem in fi:
                            if fi_elem.tag == xmlns + 'SHP':
                                functional_class = fi_elem.get('FC')
                                link_id = fi_elem.get('LID')
                                length = fi_elem.get('LE')
                                form_of_way = fi_elem.get('FW')
                                shape = fi_elem.text
                            if fi_elem.tag == xmlns + 'CF':
                                type = fi_elem.get('TY')
                                speed = fi_elem.get('SP')
                                speed_uncapped = fi_elem.get('SU')
                                free_flow = fi_elem.get('FF')
                                jam_factor = fi_elem.get('JF')
                                confidence = fi_elem.get('CN')
                                shp_sql = "insert into shp values ({},{},{},{},{},{},'{}',{},'{}','{}',{},'{}','{}','{}',{},'{}',{},'{}','{}','{}',{},{},{},{},{})".format(
                                    year, month, day, hour, minute, second, tmc_created_timestamp, tmc_map_version,
                                    tmc_units, tmc_feed_version, tmc_table_version, shp_ebu_country_code,
                                    shp_extended_country_code, shp_table_id, functional_class, link_id, length,
                                    form_of_way,
                                    shape, type, speed, speed_uncapped, free_flow, jam_factor, confidence)
                                cursor.execute(shp_sql)
        conn.commit()
    
mlrealtime_parser()
