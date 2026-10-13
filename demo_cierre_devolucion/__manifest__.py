{
    "name": "DEMO - Cierre de venta al devolver (D3 + D2)",
    "version": "20.0.1.0.0",
    "summary": "Pregunta al validar la devolucion si cerrar la venta, y avisa al facturar si quedo sin cerrar",
    "depends": ["sale_stock", "purchase_stock", "stock_account", "demo_cancelar_remanente"],
    "data": [
        "security/ir.access.csv",
        "wizards/return_close_views.xml",
        "views/sale_order_views.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
}
