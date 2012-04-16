from oauth import OAuthApi
import simplejson
import oauth2 as oauth

class FitBitApi(OAuthApi):
    """
    A handle to the FitBit server. Provides methods for the requests that
    can be made against the server and returns appropriate values for results.
    """

    def __init__(self, server, api_key, api_secret, request_token_url, access_token_url, authenticate_url, app_prefix='/1'):
        super(FitBitApi, self).__init__(server, api_key, api_secret, request_token_url, access_token_url, authenticate_url, app_prefix)
        
    def activities_steps(self, token, user='-', start='today', end='30d'):
        # set up for a fitbit authed request
        token = oauth.Token(token['oauth_token'], token['oauth_secret'])
        client = oauth.Client(self.consumer, token)
        client.set_signature_method(oauth.SignatureMethod_PLAINTEXT())
        url = self.server + self.app_prefix + '/user/%s/activities/steps/date/%s/%s.json' % (user, start, end)
        
        # and launch the request
        resp, content = client.request(url, "GET", force_auth_headers=True)
        if resp['status'] != '200':
            print content
            raise Exception("Invalid response from FitBit.")
        
        # return the interpreted data
        return simplejson.loads(content)