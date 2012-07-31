"""
A collection of classes and methods for interacting with the Ohmage server.

Most requests are handled through an instace of the OhmageApi class, which
takes care of authenticating each request. Some methods require or return other
supporting classes in this module.
"""

# the version of the Ohmage API that this module targets
# you should connect to a server >= this version for best results
__api_version__ = "2.10"

import simplejson, uuid
from datetime import datetime

# and finally the base API
from base import BaseApi

class OhmageApi(BaseApi):
    """
    A handle to the Ohmage server. Provides methods for the requests that
    can be made against the server and returns appropriate values for results.
    """
    
    def __init__(self, server, app_prefix='/app', client='ohmage-python-api'):
        super(OhmageApi, self).__init__(server, app_prefix)
        self.client = client
    
    # ========================================================
    # === User Authentication
    # ========================================================
    
    def user_auth(self, username, password):
        return self._perform_request('/user/auth', method="POST", params={
            'user': username,
            'password': password,
            'client': self.client
        })
        
    def user_auth_token(self, username, password):
        return self._perform_request('/user/auth_token', method="POST", params={
            'user': username,
            'password': password,
            'client': self.client
        })
        
    def login(self, username, password, doHashedLogin=True, doTokenLogin=True):
        """
        Performs a login and stores the resulting credentials in the handle
        (specifically, in self.auth_token and self.auth_hashedpass). All other
        methods in the API will preferentially use explicit credentials, but can
        fall back on these saved ones if the explicit credentials aren't given.
        
        If authentication fails, this method raises an OhmageApiException with code 0200.
        """
        
        if doHashedLogin:
            result = self.user_auth(username, password)
            self.auth_username = username
            self.auth_hashedpass = result['hashed_password']
            
        if doTokenLogin:
            result = self.user_auth_token(username, password)
            self.auth_token = result['token']
            
    def is_authenticated(self, forToken=False):
        """
        Returns true if credentials are stored in this api handle, whether or not
        they are still valid.

        For reference, token-based authentication times out after a while, whereas
        hashed passwords remain valid indefinitely.
        """
        return hasattr(self, 'auth_username') and (
                (forToken and hasattr(self, 'auth_token')) or
                (not forToken and hasattr(self, 'auth_hashedpass'))
            )
        
    def _add_login_to_params(self, params, useToken):
        # helper method that appends cached credentials to the request
        # if we have them and they're not already present
        if useToken and hasattr(self, 'auth_token'):
            if 'auth_token' not in params or not params['auth_token']:
                params['auth_token'] = self.auth_token
        elif hasattr(self, 'auth_username') and hasattr(self, 'auth_hashedpass'):
            if ('user' not in params or not params['user']) and ('password' not in params or not params['password']):
                params['user'] = self.auth_username
                params['password'] = self.auth_hashedpass
        
    # ========================================================
    # === Server Configuration
    # ========================================================
    
    def config_read(self, **kwargs):
        """
        Returns information about a particular ohmage install.
        """
        params={}
        params.update(kwargs)
        return self._perform_request('/config/read', method="GET", params=params)
            
    # ========================================================
    # === Campaign Manipulation
    # ========================================================
    
    def campaign_read(self, auth_token=None, output_format="short", **kwargs):
        """
        Returns a list of campaigns of the form output_format, filtered by the given parameters.
        
        (r) auth_token = A valid authentication token.
        (r) client = A short description of the client making the request.
        (r) output_format = short || long || xml
        (o) campaign_urn_list = urn:campaign:CS101,urn:campaign:CS102
        (o) start_date = 2011-11-01
        (o) end_date = 2011-11-11
        (o) privacy_state = shared || private
        (o) running_state = running || stopped
        (o) user_role = author (used as a filter on the logged-in user)
        (o) class_urn_list = urn:class:class1,urn:class:class2
        """
        
        # take the required arguments
        params = {
            'auth_token': auth_token,
            'output_format': output_format,
            'client': self.client
        }
        # and allow any other optional parameters they may wish to pass
        params.update(kwargs)
        
        # and supplement with the stored credentials, if present
        self._add_login_to_params(params, useToken=True)
        
        return self._perform_request('/campaign/read', method="POST", params=params)
        
    # ========================================================
    # === Survey Manipulation
    # ========================================================
    
    def survey_upload(self, user=None, hashedpass=None, campaign_urn=None, campaign_creation_timestamp=None, surveys=None):
        
        params = {
            'user': user,
            'password': hashedpass,
            'client': self.client,
            'campaign_urn': campaign_urn,
            'campaign_creation_timestamp': campaign_creation_timestamp,
            'surveys': simplejson.dumps(surveys)
        }
        
        # and supplement with the stored credentials, if present
        self._add_login_to_params(params, useToken=False)
        
        return self._perform_request('/survey/upload', method="POST", params=params, request_type='multipart')
        
    def survey_response_read(self,
        auth_token=None,
        campaign_urn=None,
        output_format="json-rows",
        column_list="urn:ohmage:special:all",
        user_list="urn:ohmage:special:all",
        **kwargs):
        """
        Allows reading of survey responses with a variety of output formats and many
        different ways of controlling the items present in the response.
        
        == token-based authentication takes this param:
        
            (r) auth_token = A valid authentication token from user/auth_token
            
        == OR explicitly authenticate with these params:
        
            (r) user = A username of the user attempting to login
            (r) password = A password for the above user.
        
        (r) campaign_urn = A valid campaign URN for the currently logged in user.
        (r) client = The name of the software client accessing the API.
        (r) column_list = One or more of the URNs in the table belown in a comma-separated list or urn:ohmage:special:all.
        (o) end_date = Must be present if start_date is present; allows querying against a date range
        (r) output_format = One of json-rows, json-columns, or csv.
        (o) pretty_print = A boolean that if true will indent JSON output.
        (o) prompt_id_list = Optional, but must be present if survey_id_list is not present. A comma separated list of prompt ids which must exist in the campaign being queried. urn:ohamge:special:all is also allowed.
        (o) privacy_state = If present, must be one of "private" or "shared". The output is dependent on the access-control rules governing the role of the logged-in user.
        (o) sort_order = Controls the SQL ORDER BY clause: a comma separated list containing user, timestamp, survey in any order.
        (o) start_date = Optional, but must be present if end_date is present: allows querying against a date range.
        (o) suppress_metadata = A boolean [true|false] to control whether the metadata section of the output will be returned.
        (o) survey_id_list = Optional, but must be present if prompt_id_list is not present. A comma separated list of survey ids which must exist in the campaign being queried. urn:ohamge:special:all is also allowed.
        (r) user_list = A comma separated list of usernames that must be valid for the campaign being queried. urn:ohmage:special:all is also allowed.
        (o) return_id = A boolean indicating whether to return the primary key of the survey for client update/delete purposes. This parameter is only available for json-rows output.
        (o) collapse = A boolean indicating whether to collapse duplicate results: this is most useful when asking the API to provide specific columns e.g., when you only want the a list of unique users to be returned.
        (o) num_to_skip = The number of survey responses to skip in reverse chronological order in which they were taken.
        (o) num_to_process = The number of survey responses to process after the skipping those to be skipped via 'num_survey_responses_to_skip'.
        (o) survey_response_id_list = A comma-separated list of survey response IDs. The results will only be of survey responses whose ID is in this list.
        """
        
        # take the required arguments
        params = {
            'campaign_urn': campaign_urn,
            'output_format': output_format,
            'column_list': column_list,
            'user_list': user_list,
            'client': self.client
        }
        # and allow any other optional parameters they may wish to pass
        params.update(kwargs)
        
        # and supplement with the stored credentials, if present
        self._add_login_to_params(params, useToken=True)
        
        return self._perform_request('/survey_response/read', method="POST", params=params)
    
    # ========================================================
    # === Mobility
    # ========================================================
    
    def mobility_read(self, auth_token=None, date=None, **kwargs):
        """
        Returns a list of mobility data points conforming to the given parameters.
        
        == token-based authentication takes this param:
        
            (r) auth_token = A valid authentication token from user/auth_token
            
        == OR explicitly authenticate with these params:
        
            (r) user = A username of the user attempting to login
            (r) password = A password for the above user.
            
        (r) client = A short description of the software client performing the upload.
        (r) date = An ISO8601-formatted date from which to retrieve mobility data points.
        (o) username = The username of the user whose data is desired. This is only applicable if the requesting user is an admin or if the server allows it (the "mobility_enabled" flag from config/read) and the requesting user is privileged in any class to which the desired user belongs.
        (o) with_sensor_data = true/false Indicates whether or not to return the sensor data with the regular data. The default is false.
        """
        
        # take the required arguments
        params = {
            'auth_token': auth_token,
            'date': date,
            'client': self.client
        }
        # and allow any other optional parameters they may wish to pass
        params.update(kwargs)
        
        # and supplement with the stored credentials, if present
        self._add_login_to_params(params, useToken=True)
        
        return self._perform_request('/mobility/read', method="POST", params=params)

    def mobility_dates_read(self, auth_token=None, start_date=None, end_date=None, username=None, **kwargs):
        """
        Returns a list of mobility data points conforming to the given parameters.

        == token-based authentication takes this param:

            (r) auth_token = A valid authentication token from user/auth_token

        == OR explicitly authenticate with these params:

            (r) user = A username of the user attempting to login
            (r) password = A password for the above user.

        (r) client = A short description of the software client performing the upload.
        (o) start_date = An ISO8601-formatted date which limits the results to only those dates on or after this one.
        (o) end_date = An ISO8601-formatted date which limits the results to only those dates on or before this one.
        (o) username = The username of the user whose data is desired. This is only applicable if the requesting user is an admin or if the server allows it and the requesting user is privileged in any class to which the desired user belongs.
        """

        # take the required arguments
        params = {
            'auth_token': auth_token,
            'client': self.client
        }
        # and allow any other optional parameters they may wish to pass
        params.update(kwargs)

        # and add the optional params
        if start_date: params['start_date'] = start_date
        if end_date: params['end_date'] = end_date
        if username: params['username'] = username

        # and supplement with the stored credentials, if present
        self._add_login_to_params(params, useToken=True)

        return self._perform_request('/mobility/dates/read', method="POST", params=params)
        
    # ========================================================
    # === support methods and classes
    # ========================================================
    
    def _perform_request(self, *args, **kwargs):
        """
        Overrides the base _perform_request() to get a chance to catch and reinterpet
        BaseApi.HTTPException in the case where the body contains more info about the error.
        """
        try:
            return super(OhmageApi, self)._perform_request(*args, **kwargs)
        except BaseApi.HTTPException, ex:
            # assume json and attempt to parse out result and errors keys
            # if it's not json or they're not present, re-raise the original exception
            try:
                parsed = simplejson.loads(ex.body)
                assert 'result' in parsed and 'errors' in parsed
                raise OhmageApi.OhmageApiException(result['errors'])
            except:
                raise ex
        
    def _handle_response(self, data):
        """
        Overrides the base _handle_response() method to trap for Ohmage-specific errors.
        """
        
        # in the rare case that the data is actually xml, return it as it is
        if data.startswith("""<?xml version="1.0" encoding="UTF-8"?>"""):
            return data
            
        result = simplejson.loads(data)
        
        if (result['result'] != 'success'):
            raise OhmageApi.OhmageApiException(result['errors'])
        
        return result
        
    class OhmageApiException(Exception):
        """
        Raised when an Ohmage API call produces a response where the result is not success.

        The possible errors and their associated codes are listed here, for reference:
        https://github.com/cens/ohmageServer/wiki/Error-Codes
        """
        def __init__(self, errors):
            self.errors = errors

        def errors(self):
            """
            Returns a list of dicts describing the errors that produced this exception.

            Each dict has a key 'code' which is the numeric code for the error, and
            'text' which is a plain-text description of the error. Note that multiple
            errors may map to the same code.
            """
            return self.errors
            
        def codes(self):
            """
            Returns a list of the error codes that caused this exception as integers.
            """
            return [int(x['code']) for x in self.errors]
            
        def __str__(self):
            return "Ohmage API Error: %s" % (",".join(["%s (code: %s)" % (x['text'], x['code']) for x in self.errors]))
            
        def __unicode__(self):
            return unicode(self.__str__())
 
class Survey(dict):
    """
    Represents a completed survey. 'responses' is a list of Response objects.
    """
    def __init__(self, survey_id, time, timezone, responses, uuid=None):
        """
        Constructs a new survey response with the specified values.

        'responses' should be a list of Response objects.
        Ommitting the 'uuid' paramter causes a unique uuid4 to be generated automatically.
        """
        self['survey_key'] = str(uuid) if uuid is not None else str(uuid.uuid4())
        self['time'] = time
        self['timezone'] = timezone
        self['location_status'] = "unavailable"
        self['survey_id'] = survey_id
        self['survey_launch_context'] = {'launch_time': time, 'launch_timezone': timezone, 'active_triggers': []}
        self['responses'] = responses

class Response(dict):
    """
    Represents a particular prompt within a survey. Passed as items of a list into Survey's constructor for 'responses'.
    """
    def __init__(self, prompt_id, value):
        self['prompt_id'] = prompt_id
        self['value'] = value