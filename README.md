# HERE RTTI Archive Miner

This is a plugin of QGIS(https://qgis.org), it has 3 major functions:
1. Convert GPS trace to sqlite3 format, calling HERE Route Match Extension to acquire route information including TMC attributes.
2. Mapping GPS trace with route information with HERE Real Time Traffic Information (RTTI) archive to obtain traffic information along the route with specific time frame (by GPS timestamp or manual override is possible).
3. Generate the results in CSV format, load it into QGIS with customized rendering settings.

It also includes "traffic_db_builder.py" which can download HERE Real Time Traffic feed (v3.2) and convert it to Sqlite3 format. However it should be called using a batch file (.bat) and task scheduler of Windows OS with Python 3.x installed.

This plugin is only for HERE internal use.

Any inquiry please contact: guan-ling.wu@here.com