from tipprapi.tipprapi import TipprAPIClient
from googleoffers.client import GoogleOffers

tippr_client = TipprAPIClient()

#g_client = GoogleOffers()

promotions = tippr_client.find_promotions()

for promotion in promotions:
    if promotion['status'] in ['approved', 'active', 'closed']:
        print promotion 
