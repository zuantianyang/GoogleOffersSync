from tipprapi.tipprapi import TipprAPIClient

SHOW = True

client = TipprAPIClient()

def show(r):
    import json
    if SHOW:
        print json.dumps(r, sort_keys=True, indent=4)

def test_find_promotions():
    show(client.find_promotions(dict(status='approved')))
    show(client.find_promotions())

test_find_promotions()
