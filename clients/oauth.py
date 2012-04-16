from base import BaseApi

import oauth2 as oauth
import urllib, cgi

class OAuthApi(BaseApi):
    """
    Implements OAuth authentication on top of regular HTTP requests.
    
    The main trickiness of using an OAuth provider is that you must first
    redirect the user to the provider's site to allow the user to authorize
    your requests for their account. This occurs in roughly the following
    order, assuming that all goes well and the user ok's the process:
    
    1) redirect the user to the provider's site to get their ok. this
       uses the key and secret that the provider made available to you,
       and maintains an oauth_token and oauth_token_secret for subsequent
       requests.
       
    2) accept the user returning from the provider's authorization page.
       here, you issue a request for a permanent access token using the
       oauth_token and oauth_token_secret from step 1 plus a verifier
       passed to you from provider via GET. the request results in a
       permanent access token (consisting of an oauth_token and
       oauth_token_secret) that are used to sign all subsequent requests.
       
    3) when you make a request, you must include the token and secret supplied
       in step 2. depending on the provider, you either include this data in the
       GET/POST, or in the headers. deriving classes should make this choice
       for you.
    """

    def __init__(self, server, api_key, api_secret, request_token_url, access_token_url, authenticate_url, app_prefix=''):
        super(OAuthApi, self).__init__(server, app_prefix)

        self.api_key = api_key
        self.api_secret = api_secret

        self.consumer = oauth.Consumer(api_key, api_secret)
        self.client = oauth.Client(self.consumer)
        self.client.set_signature_method(oauth.SignatureMethod_PLAINTEXT())

        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.authenticate_url = authenticate_url

    # ========================================================
    # === OAuth Handshake
    # ========================================================
    
    def get_auth_url(self, callback_url=None):
        """
        Produces a URL which the owner of the account should visit to authorize an app
        to access their information. The URL contains an intermediate token which is
        used to validate the request.
        
        Returns a tuple (rq_token, url) consisting of the request token that was used to
        sign the auth redirect plus the URL to which to redirect. The caller must
        hold on to the request token and pass it back when calling process_auth()
        in order to complete the authentication process.
        """
        
        # get temporary token
        resp, content = self.client.request(self.server + self.request_token_url, "GET")
        if resp['status'] != '200':
            raise OAuthApi.OAuthException()

        rq_token = dict(cgi.parse_qsl(content))
        
        # create and return the redirect url
        params = {'oauth_token': rq_token['oauth_token']}
        
        if callback_url:
            params['oauth_callback'] = callback_url
            
        return (rq_token, "%s?%s" % (self.server + self.authenticate_url, urllib.urlencode(params)))
        
    def process_auth_response(self, rq_token, verifier):
        """
        Processes an authentication request, using the request token passed back
        from get_auth_url() plus a verifier included in GET parameter 'oauth_verifier'
        of the callback hit that prompted this method to be called.
        """
        
        # use the request token in the session to build a new client.
        token = oauth.Token(rq_token['oauth_token'], rq_token['oauth_token_secret'])
        token.set_verifier(verifier)
        client = oauth.Client(self.consumer, token)
        
        # request the authorized access token
        resp, content = client.request(self.server + self.access_token_url, "POST")
        if resp['status'] != '200':
            raise OAuthApi.OAuthException("Received a non-200 response (%s) in process_auth_response()" % (resp['status']), content)

        access_token = dict(cgi.parse_qsl(content))
        
        return access_token
            
    # ========================================================
    # === Exceptions
    # ========================================================
            
    class OAuthException(Exception):
        def __init__(self, message, body=None):
            self.message = message
            self.body = body
            pass
        
        def __str__(self):
            return "%s" % (self.message)
            
        def __unicode__(self):
            return u"%s" % (self.message)