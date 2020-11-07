from lsru import Espa

# Instantiate Espa class
espa = Espa()


for order in espa.orders:
    # Orders have their own class with attributes and methods
    print('%s: %s' % (order.orderid, order.status))

for order in espa.orders:
    if order.is_complete:
        order.download_all_complete('/home/rave/serdp/dangermond-sb/landsat-sr-et/', unpack=True)
