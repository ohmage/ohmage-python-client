from oauth import OAuthApi
import simplejson, functools
import oauth2 as oauth

# enables debugging output to the console
debug = True

class BodyMediaApi(OAuthApi):
    """
    A handle to the BodyMedia server. Provides methods for the requests that
    can be made against the server and returns appropriate values for results.
    """

    def __init__(self, server, api_key, api_secret, request_token_url, access_token_url, authenticate_url, app_prefix='/v2/json'):
        super(BodyMediaApi, self).__init__(
            server,
            api_key, api_secret,
            request_token_url, access_token_url, authenticate_url,
            app_prefix)

    # ============================================================================
    # === OVERRIDDEN BASE METHODS
    # ============================================================================

    def get_auth_url(self, callback_url=None, appendix_params=None):
        return super(BodyMediaApi, self).get_auth_url(callback_url, appendix_params={'api_key': self.api_key,'oauth_callback': callback_url})

    def process_auth_response(self, rq_token, verifier, appendix_params=None):
        return super(BodyMediaApi, self).process_auth_response(rq_token, verifier, appendix_params={'api_key': self.api_key})

    # ============================================================================
    # === BODYMEDIA API METHODS
    # ============================================================================

    def step_day(self, token, start='20120101', end='20120502'):
        # set up for an authed request
        token = oauth.Token(token['oauth_token'], token['oauth_secret'])
        client = oauth.Client(self.consumer, token)
        client.set_signature_method(oauth.SignatureMethod_PLAINTEXT())
        url = self.server + self.app_prefix + '/step/day/%s/%s?api_key=%s' % (start, end, self.api_key)

        if debug: print "Accessing URL: %s" % url

        # set the response to be json
        headers = {'Content-Type': 'application/json'}

        # and launch the request
        resp, content = client.request(url, "GET", headers=headers, force_auth_headers=True)
        if resp['status'] != '200':
            print content
            raise Exception("Invalid response from BodyMedia.")

        if debug: print "Returned (%s): %s" % (resp['status'], content)

        # return the interpreted data
        return simplejson.loads(content)