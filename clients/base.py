import httplib2, mimetypes, simplejson, urllib, uuid
from datetime import datetime

# and for multipart stuff
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2

# Register the streaming http handlers with urllib2
register_openers()
            
class BaseApi(object):
    """
    Consolidates functionality common across all HTTP(S) APIs. 
    """
    
    def __init__(self, server, app_prefix):
        self.server = server
        self.app_prefix = app_prefix
    
    # utility function to handle the dirty work of making a connection, catching errors, and returning the parsed result
    def _perform_request(self, uri, params, method="GET", request_type="standard"):
        http = httplib2.Http()
        url = self.server + self.app_prefix + uri
        
        if request_type == "standard":
            params = urllib.urlencode(params)
            # this is where the work happens
            resp, content = http.request(url, method, params, headers={'Content-type': 'application/x-www-form-urlencoded'})
        elif request_type == "multipart":
            try:
                datagen, headers = multipart_encode(params)
                request = urllib2.Request(url, datagen, headers)
                # or, alternatively, here
                content = urllib2.urlopen(request).read()
                # we assume it went through if no exception was thrown
                resp = {'status': '200'}
            except urllib2.HTTPError, ex:
                resp = {'status': str(ex.code)}
        else:
            raise Exception("Unknown request_type %s given to %s._perform_request(), must be 'standard' or 'multipart'" % (request_type, self.__class__.__name__))
        
        if resp['status'] != '200':
            raise BaseApi.HTTPException(self.__class__.__name__, resp['status'], body=content)

        return self._handle_response(content)
                
    def _handle_response(self, data):
        """
        Performs unified handling of the response to trap for error conditions, format according to the API defs, etc.
        This base version is a stub that simply returns the data as-is.
        
        Derived API classes should override this method to raise their own exceptions when API-level errors occur
        and otherwise format responses.
        """
        return data
                
    class HTTPException(Exception):
        def __init__(self, service, code, body=None):
            self.service = service
            self.code = code
            self.body = body
        
        def __str__(self):
            return "%s errored w/HTTP code %s" % (self.service, self.code)
            
        def __unicode__(self):
            return unicode(self.__str__())