#!/bin/env python

"""
The MIT License

Copyright (c) 2010 The Chicago Tribune

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import csv
from datetime import datetime
import re
import time
from urllib import urlencode
from urllib2 import urlopen, URLError

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

"""
This module provides a thin wrapper around the CTA BusTracker API.

All objects returned by this module are simple dictionaries of the
attributes parsed from the API's XML.

For a demonstration of features, execute the module.
"""

CTA_API_VERSION = 'v1'
CTA_API_ROOT_URL = 'http://www.ctabustracker.com/bustime/api'

class CTABusTracker(object):
    
    def __init__(self, api_key, retry_urls=True, retry_attempts=3, retry_delay=3, retry_backoff=2):
        self.api_key = api_key
        self.retry_urls = retry_urls
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff

    def _build_api_url(self, method, **params):
        """
        Build a valid CTA API url.
        """
        params['key'] = self.api_key
        
        url = '%(root)s/%(version)s/%(method)s?%(params)s' % {
            'root': CTA_API_ROOT_URL, 
            'version': CTA_API_VERSION, 
            'method': method, 
            'params': urlencode(params)}
        
        return url

    def _grab_url(self, url):
        """
        URLOpen wrapper with exponential back-off.
        
        Algorithm sourced from:
        http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
        """
        attempts_remaining = self.retry_attempts
        delay = self.retry_delay
        
        while attempts_remaining > 1:
            try:
                return urlopen(url, timeout=5)
            except URLError, e:
                #print "%s, Retrying in %d seconds..." % (str(e), delay)
                time.sleep(delay)
                attempts_remaining -= 1
                delay *= self.retry_backoff
                
        # Final attempt, errors will propogate up
        return urlopen(url, timeout=5)
    
    def get_time(self):
        """
        Get CTA system time.
        
        Return a datetime object.
        """
        url = self._build_api_url('gettime')

        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)
        
        tag = soup.find('tm')
        
        return datetime.strptime(tag.string, '%Y%m%d %H:%M:%S')

    def get_vehicle(self, vehicle_id):
        """
        Get the details of a single vehicle.

        Return a dictionary of vehicle attributes.
        """
        url = self._build_api_url('getvehicles', vid=vehicle_id)

        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)

        vehicle_tags = soup.findAll('vehicle')

        if len(vehicle_tags) > 1:
            raise Exception('Multiple buses with the same id?')

        tag = vehicle_tags[0]
        vehicle = {
            'id': str(tag.vid.string),
            'last_update': datetime.strptime(tag.tmstmp.string, '%Y%m%d %H:%M'),
            'latitude': str(tag.lat.string),
            'longitude': str(tag.lon.string),
            'heading': int(tag.hdg.string),
            'pattern_id': str(tag.pid.string),
            'route_id': str(tag.rt.string),
            'destination': str(tag.des.string),
            'distance_into_route': float(tag.pdist.string)
            }

        if hasattr(tag.dly, 'string') and tag.dly.string == 'true':
            vehicle['delayed'] = True
        else:
            vehicle['delayed'] = False

        return vehicle

    def get_route_vehicles(self, route_id):
        """
        Get all vehicles active on a given route.

        Return a dictionary with vehicle ids as keys. Values are dictionaries
        of vehicle attributes.
        """
        url = self._build_api_url('getvehicles', rt=route_id)

        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)

        vehicles = {}

        for tag in soup.findAll('vehicle'):
            vehicles[str(tag.vid.string)] = {
                'id': str(tag.vid.string),
                'last_update': datetime.strptime(tag.tmstmp.string, '%Y%m%d %H:%M'),
                'latitude': str(tag.lat.string),
                'longitude': str(tag.lon.string),
                'heading': int(tag.hdg.string),
                'pattern_id': str(tag.pid.string),
                'route_id': str(tag.rt.string),
                'destination': str(tag.des.string),
                'distance_into_route': float(tag.pdist.string)
                }

            if hasattr(tag.dly, 'string') and tag.dly.string == 'true':
                vehicles[str(tag.vid.string)]['delayed'] = True
            else:
                vehicles[str(tag.vid.string)]['delayed'] = False

        return vehicles
        
    def get_routes(self):
        """
        Get all available routes.
        
        Return a dictionary with route ids as keys. Values are dictionaries
        of route attributes.
        """
        url = self._build_api_url('getroutes')
        
        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)
        
        routes = {}
        
        for tag in soup.findAll('route'):
            routes[str(tag.rt.string)] = {
                'id': str(tag.rt.string),
                'name': str(tag.rtnm.string)
                }
                
        return routes
    
    def get_route_directions(self, route_id):
        """
        Get all directions that buses travel on a given route.
        
        Return a list of directions (as strings).
        """
        url = self._build_api_url('getdirections', rt=route_id)
        
        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)
        
        directions = []
        
        for tag in soup.findAll('dir'):
            directions.append(str(tag.string))
                
        return directions
    
    def get_route_stops(self, route_id, direction):
        """
        Get all stops for a given route, traveling in a given direction.
        
        Return a dictionary with stop ids as keys.  Values are dictionaries
        of stop attributes.
        """
        url = self._build_api_url('getstops', rt=route_id, dir=direction)
        
        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)
        
        stops = {}
        
        for tag in soup.findAll('stop'):
            try:
                stops[str(tag.stpid.string)] = {
                    'id': str(tag.stpid.string),
                    'name': str(tag.stpnm.string),
                    'latitude': str(tag.lat.string),
                    'longitude': str(tag.lon.string)
                    }
            except AttributeError:
                # Stops sometimes come back without proper lat/lon attributes
                continue
                
        return stops
    
    def get_pattern(self, pattern_id):
        """
        Get a single pattern by id.
        
        Return a dictionary of pattern attributes.
        """
        url = self._build_api_url('getpatterns', pid=pattern_id)
        
        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)
        
        pattern_tags = soup.findAll('ptr')

        if len(pattern_tags) > 1:
            raise Exception('Multiple patterns with the same id?')

        tag = pattern_tags[0]
        
        pattern = {
            'id': str(tag.pid.string),
            'length': int(float(tag.ln.string)),
            'route_direction': str(tag.rtdir.string),
            'path': {}
            }
                
        for pt in tag.findAll('pt'):
            pattern['path'][str(pt.seq.string)] = {
                'id': str(pt.seq.string),
                'type': str(pt.typ.string),  # S = stop, W = waypoint
                'latitude': str(pt.lat.string),
                'longitude': str(pt.lon.string)
                }
                
            if pt.type == 'S':
                pattern['path'][str(pt.seq.string)]['stop_id'] = str(pt.stpid.string)
                pattern['path'][str(pt.seq.string)]['stop_name'] = str(pt.stpnm.string)
            else:
                pattern['path'][str(pt.seq.string)]['stop_id'] = None
                pattern['path'][str(pt.seq.string)]['stop_name'] = None
                
        return pattern
    
    def get_route_patterns(self, route_id):
        """
        Get all active patterns for a given route.
        
        Return a dictionary with pattern ids as keys. Values are dictionaries
        of pattern attributes.
        """
        url = self._build_api_url('getpatterns', rt=route_id)
        
        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)
        
        patterns = {}
        
        for tag in soup.findAll('ptr'):
            patterns[str(tag.pid.string)] = {
                'id': str(tag.pid.string),
                'length': int(float(tag.ln.string)),
                'route_direction': str(tag.rtdir.string),
                'path': {}
                }
                
            for pt in tag.findAll('pt'):
                patterns[str(tag.pid.string)]['path'][str(pt.seq.string)] = {
                    'id': str(pt.seq.string),
                    'type': str(pt.typ.string),  # S = stop, W = waypoint
                    'latitude': str(pt.lat.string),
                    'longitude': str(pt.lon.string)
                    }
                    
                if pt.type == 'S':
                    patterns[str(tag.pid.string)]['path'][str(pt.seq.string)]['stop_id'] = str(pt.stpid.string)
                    patterns[str(tag.pid.string)]['path'][str(pt.seq.string)]['stop_name'] = str(pt.stpnm.string)
                else:
                    patterns[str(tag.pid.string)]['path'][str(pt.seq.string)]['stop_id'] = None
                    patterns[str(tag.pid.string)]['path'][str(pt.seq.string)]['stop_name'] = None
                
        return patterns
    
    def get_vehicle_predictions(self, vehicle_id):
        """
        Get ETD/ETA predictions for a given vehicle.
        
        Return a list of predictions (dictoinaries of prediction attributes).
        """
        url = self._build_api_url('getpredictions', vid=vehicle_id)
        
        return self._parse_predictions(url)
    
    def get_route_predictions(self, route_id):
        """
        Get ETD/ETA predictions for a given route.
        
        Return a list of predictions (dictoinaries of prediction attributes).
        """
        url = self._build_api_url('getpredictions', rt=route_id)
        
        return self._parse_predictions(url)
    
    def get_stop_predictions(self, stop_id):
        """
        Get ETD/ETA predictions for a given stop.
        
        Return a list of predictions (dictoinaries of prediction attributes).
        """
        url = self._build_api_url('getpredictions', stpid=stop_id)
        
        return self._parse_predictions(url)
    
    def _parse_predictions(self, url):
        """
        Encapsulates prediction parsing since it has multiple entry points.
        """
        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)

        predictions = []

        for tag in soup.findAll('prd'):
            p = {
                'last_update': datetime.strptime(tag.tmstmp.string, '%Y%m%d %H:%M'),
                'type': str(tag.typ.string), # A = arrival, D = departure
                'stop_id': str(tag.stpid.string),
                'stop_name': str(tag.stpnm.string),
                'distance_to_destination': int(tag.dstp.string),
                'vehicle_id': str(tag.vid.string),
                'route_id': str(tag.rt.string),
                'direction': str(tag.rtdir.string),
                'destination': str(tag.des.string),
                'prediction': datetime.strptime(tag.prdtm.string, '%Y%m%d %H:%M'),
                }
            
            if hasattr(p.dly, 'string') and p.dly.string == 'true':
                p['delay'] = True
            else:
                p['delay'] = False
            
            predictions.append(p)

        return predictions
    
    def get_route_service_bulletins(self, route_id, direction=None):
        """
        Get all service bulletins for a given route.
        
        Return a list of bulletins (dictoinaries of bulletins attributes).
        """
        if direction:
            url = self._build_api_url('getservicebulletins', rt=route_id, rtdir=direction)
        else:    
            url = self._build_api_url('getservicebulletins', rt=route_id)
            
        return self._parse_service_bulletins(url)
    
    def get_stop_service_bulletins(self, stop_id):
        """
        Get all service bulletins for a given stop.
        
        Return a list of bulletins (dictoinaries of bulletins attributes).
        """
        url = self._build_api_url('getservicebulletins', stpid=stop_id)
            
        return self._parse_service_bulletins(url)
    
    def _parse_service_bulletins(self, url):
        """
        Encapsulates service bulletin parsing since there are multiple ways
        of requesting this information.
        """
        xml = self._grab_url(url)
        soup = BeautifulStoneSoup(xml)
        
        bulletins = []
        
        for tag in soup.findAll('sb'):
            b = {
                'title': str(tag.sbj.string),
                'details_full': str(tag.dtl.string),
                'details_short': str(tag.brf.string),
                'priority': str(tag.prty.string),
                'affects': []   #if empty, affects all
                }
                
            if hasattr(tag, 'srvc'):
                for elem in tag.srvc:
                    # Skip non-tags
                    if not hasattr(elem, 'name'):
                        continue
                    
                    if elem.name == 'stpid':
                        b['affects'].append(('stop', str(elem.string)))
                    elif elem.name == 'rt':
                        b['affects'].append(('route', str(elem.string)))
                        
            bulletins.append(b)
                
        return bulletins

# Demo
if __name__ == "__main__":
    API_KEY = raw_input('Enter your API Key:')
    TEST_ROUTE = raw_input('Enter a route id (e.g. 60):')
    
    cbt = CTABusTracker(API_KEY)
    
    print 'CTA system time is ', cbt.get_time(), '.'
    
    routes = cbt.get_routes()
    print 'Found %i routes.' % len(routes)
    
    dirs = cbt.get_route_directions(TEST_ROUTE)
    print 'Route %s runs in %i directions.' % (TEST_ROUTE, len(dirs))
    
    vehicles = cbt.get_route_vehicles(TEST_ROUTE)
    print 'Route %s has %i active vehicles.' % (TEST_ROUTE, len(vehicles))
    
    stops = cbt.get_route_stops(TEST_ROUTE, dirs[0])
    print 'Route %s has %i active stops in the %s direction.' % (TEST_ROUTE, len(stops), dirs[0])
    
    bulletins = cbt.get_route_service_bulletins(TEST_ROUTE)
    if bulletins:
        print 'Route %s has %i services bulletins.' % (TEST_ROUTE, len(bulletins))
    else:
        print 'Route %s has no service bulletins.' % TEST_ROUTE
        
    patterns = cbt.get_route_patterns(TEST_ROUTE)
    print 'Route %s includes %i patterns.' % (TEST_ROUTE, len(patterns))
    
    predictions = cbt.get_route_predictions(TEST_ROUTE)
    print 'Route %s has %i ETD/ETA predictions.' % (TEST_ROUTE, len(predictions))