__author__ = 'txema'

import httplib2
import simplejson as json

from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
from googleoffers.retry import retry

#codeStatuses = ('CREATED', 'PURCHASED', 'REDEEMED', 'REFUNDED', 'CANCELLED')
#offerStatuses = ('CREATED', 'SCHEDULED', 'LIVE', 'EXPIRED', 'GOOGLE_CANCELLED', 'MERCHANT_CANCELLED')

class GoogleOffers(object):
    def __init__(self, partner_id, credentials_file, client_secrets_file='client_secrets.json'):
        self.client_secrets_file = client_secrets_file
        self.base_url = "https://www.googleapis.com/offers/v1/merchant/"  # The base URL without any method calls
        self.url = self.base_url + partner_id
        self.partner_id = partner_id
        
        self.httpHeaders = {
                'Content-Type' : 'application/json', 
                'charset'      :'UTF-8',
                'cache-control': 'no-cache'
                }
        
        self.httpHeadersNoContent = self.httpHeaders.copy()
        self.httpHeadersNoContent['Content-length'] = '0'
        self.http = self.getAuthHttp(httplib2.Http(), credentials_file)  # Our HTTP Object

    @retry(Exception, tries=4)
    def GetStatus(self):
        response, content = self.make_request(self.url, "GET")
        
        # Now capture the partner name from the returned object
        if content.has_key("error"):
            raise GoogleOffersError("Error code: " + str(content["error"]["code"]) + ".  " + content["error"]["message"])   
        elif content["merchant"].has_key("name"):
            partner_name = content["merchant"]["name"]
            return content["merchant"]
        else:
            raise GoogleOffersError('Fatal Error.  Partner name does not exist')
    
    @retry(Exception, tries=4)
    def GetOfferStatus(self, offer_id):
        httpHeaders = {'Content-Type': 'application/json', 'charset':'UTF-8', 'cache-control': 'no-cache'}   # HTTP headers
        httpHeadersNoContent = httpHeaders.copy()
        httpHeadersNoContent['Content-length'] = '0'        
        
        response, content = self.make_request(self.url + "/offer/" + offer_id, "GET", headers=httpHeadersNoContent)
        
        #Check if current offer exists
        if content.has_key("error"):
           return "-1"
        if content["offer"].has_key("status"): # Determine the current offer's status
            offerStatus = content["offer"]["status"]
            return content["offer"]["status"]
        else:
            raise GoogleOffersError("Offer " + offer_id + " does not exist")
           
    @retry(Exception, tries=4)
    def GetRedemptionCodesWithStatus(self, offer_id, status):
        lookup_url = self.url + "/offer/" + offer_id + "/lookupCodes?status=" + status
        
        httpHeaders = {'Content-Type': 'application/json', 'charset':'UTF-8', 'cache-control': 'no-cache'}   # HTTP headers
        httpHeadersNoContent = httpHeaders.copy()
        httpHeadersNoContent['Content-length'] = '0'
    
        response, content = self.make_request(lookup_url, "POST", headers=httpHeadersNoContent)
        return content
    
    @retry(Exception, tries=4)
    def SetRedemptionCodeStatus(self, offer_id, code):
        httpBody = '{"codes":[{"id":"' + code + ',"status":"REDEEMED"}]}' #Build our HTTP POST JSON object
        redemption_url = self.base_url  + "/offer/" + offer_id + "/redeemCodes"
        response, content = self.make_request(redemption_url, "POST", body=httpBody, headers=self.httpHeaders)
                
        if content.has_key("error"):
            if content["error"]["code"] == 500:
                msg = "You are trying to redeem a code for an offer that has not yet gone live, or has been cancelled."
            else:
                msg = "Error code: " + str(content["error"]["code"]) + ".  " + content["error"]["message"]
            raise GoogleOffersError(msg)
        else:
            return content
        
    @retry(Exception, tries=4)
    def StopOffer(self, offer_id):
        #query offer status
        status = self.GetOfferStatus(offer_id)
        if status in ['CREATED', 'SCHEDULED', 'LIVE']:
            raise GoogleOffersError('Offer ' + offer_id + ' cannot be stopped since it is in ' + status + ' status.')
        else:
            stop_url = self.base_url + "/offer/" + offer_id + "/stop"
            response, content = self.make_request(stop_url, "POST", headers=self.httpHeadersNoContent)
                            
            if content.has_key("error"):
                raise GoogleOffersError("Error code: " + str(content["error"]["code"]) + ".  " + content["error"]["message"])   
            elif content["offer"].has_key("status"): # Determine the current offer's status
                offerStatus = content["offer"]["status"]
                raise GoogleOffersError("Offer ID: " + offer_id + "  " + offerStatus)
            else:
                raise GoogleOffersError('Fatal Error:  Problem stopping offer')
    
    def getAuthHttp(self, http, storage):
        # STORAGE, name of a file for caching the access_token and refresh_tokens
        self.storage = storage
    
        # Read from the file
        flowData = json.load(open(self.client_secrets_file, 'r'))
        # Set up a Flow object to be used if we need to authenticate.
        FLOW = OAuth2WebServerFlow(flowData['client_id'], flowData['client_secret'],
                               flowData['scope'], flowData['user_agent'])

        storage = Storage(self.storage)
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            credentials = run(FLOW, storage)
    
        # Create an httplib2.Http object to handle our HTTP requests and authorize it
        # with our good Credentials.
        return credentials.authorize(http)
    
    def make_request(self, url, method, headers={}, body=""):
        try:
            response, content = self.http.request(url, method, body, headers)
            return (response, json.loads(content))
        except AccessTokenRefreshError:
            raise GoogleOffersError("The credentials have been revoked or expired, \
                    please re-run the application to re-authorize")

class CredentialsException(Exception):
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return repr(self.value)

class GoogleOffersError(Exception):
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return repr(self.value)
