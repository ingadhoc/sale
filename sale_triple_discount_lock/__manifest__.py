{
    "name": "Sale Triple Discount Lock",
    "version": "19.0.1.1.0",
    "category": "Sales",
    "summary": "Lock Discount 1 for pricelist use only and preserve Discount 2/3 on recalculation",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "depends": [
        "sale_triple_discount",
    ],
    "data": [
        "views/sale_order_view.xml",
        "wizards/sale_order_discount_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
